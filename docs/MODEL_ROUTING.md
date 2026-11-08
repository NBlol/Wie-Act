# GenAI module — model routing, prompts and resilience

This document is the technical explanation of EdNova's GenAI module required by the challenge
(*"how your application combines the two model categories, and how it behaves when usage is limited"*).

## 1. Principle

> Give the compact model everything it can handle correctly; reserve the large model for steps that
> genuinely need it; never call a model for something code can compute; never regenerate what was
> already obtained.

The decision is encoded once, in `backend/app/ai/tasks.py`, and applied by `ModelRouter.run(task, inputs)`.
It is served at `GET /api/system/routing` so that the choice is visible and auditable.

## 2. Routing table

| Task | Category | Max tokens | Rationale |
|---|---|---|---|
| `tutor_triage` | compact | 160 | Classification (language ∈ {en, fr, ar, tn}, intent, confusion, complexity, topic). ~1 s. Its `complexity` output decides whether the answer step needs the large model. |
| `tutor_answer` | **dynamic** | 900 | `complexity == high` → large; `hint_level == 2` (full worked solution) → large; direct-mode exercise help → large; ≥ 3 retrieved passages → large; otherwise compact. |
| `diagnostic_summary` | compact | 300 | Style/level are computed in code; the model writes 3 sentences + 3 tips. |
| `quiz_generate` | large | 2 200 | N distinct, correct questions with misconception-based distractors and explanations. |
| `quiz_grade_short` | compact | 600 | **One batched call** for all free-text answers of a submission; MCQs are graded in code. |
| `quiz_feedback` | compact | 260 | 3 encouraging sentences from computed results. |
| `room_nudge` | compact | 200 | Participation stats are computed in code; the model writes the warm invitation. |
| `room_guiding_question` | compact | 160 | One Socratic question from the last messages. |
| `room_check_explanation` | large | 700 | Verifying a peer explanation is exactly where wrong explanations get accepted — needs reasoning. |
| `room_summary` | large | 900 | Multi-source synthesis into revision notes. |
| `rag_answer` | **dynamic** | 700 | 1 high-scoring passage (score ≥ 0.75) + short question (< 120 chars) → compact; otherwise large. |
| `roadmap_generate` | large | 2 000 | Multi-week planning with checkpoints. |
| `notes_generate` | large | 2 000 | Synthesis + polished writing + flashcards. |

Steps with **no model call**: language detection fallback (script + lexicon), BM25 retrieval, MCQ grading,
participation balance (normalised entropy of message counts), diagnostic scoring, next-step rules, cache.

### Budget per user action

| Action | Model calls | Notes |
|---|---|---|
| Tutor turn | ≤ 2 (triage + answer) | retrieval is local; cache can bring it to 0 |
| Quiz generation | 1 (large) | cached for equivalent topic/document/difficulty/language/count |
| Quiz submission | ≤ 2 (batched grading + feedback) | 1 if there is no short-answer question |
| Room message | 0, or 1 compact nudge every ≥ N unbalanced messages, or 1 answer for `@ednova` |
| Moderator action | 1 | compact or large per table |
| Roadmap / notes / document question | 1 | cached |

## 3. Prompt design (`backend/app/ai/prompts.py`)

All prompts ask for **compact JSON** so the application can post-process reliably (`extract_json`
tolerates code fences and prose; non-JSON answers are kept as raw text rather than discarded).

* **Tutor system prompt** = role (patient peer tutor, guide the process, never replace the teacher) +
  inclusivity rule + *learning-style instruction* (6 variants) + *level instruction* + *hint rule*
  (guided level 1/2/3 or direct) + *confusion rule* + *language instruction* (incl. Tunisian Darija in Arabic
  or Latin script, Latin digits) + grounding/citation rule + output schema
  `{answer_md, guiding_question, next_step, confusion_detected}`.
* **Hint-first policy**: in guided mode, intents `exercise_help`/`answer_request` start at hint level 1
  (method only), then level 2 (first worked step), and the learner can *reveal* level 3 (full solution,
  routed to the large model). A new question resets the level.
* **Room prompts** receive computed participation statistics and the last messages; the nudge prompt
  explicitly asks to invite quiet members *by name*, thank active ones and never blame.
* **RAG prompts** number the passages and require `[n]` citations and an explicit "not in the passages" statement.

## 4. Resilience when capacity is limited

Implemented in `ModelRouter` (`backend/app/ai/router.py`) and verified by `tests/test_router.py`:

| Situation | Behaviour | What the learner sees |
|---|---|---|
| Equivalent request already answered | served from cache (memory LRU + `ai_cache` table, 24 h TTL) | tier pill "cached" |
| Transient 429/5xx/timeout | retry with exponential back-off (0.8 s, 2 s …), `Retry-After` honoured (≤ 10 s) | staged progress continues |
| Large model fails after retries | fallback to the compact model | notice: "large model temporarily unavailable — compact model answered" (localised) |
| 429 on the large model | fallback to compact, `fallback_reason = rate_limited` | notice: "usage limit reached, retry later for more detail" |
| ≥ `AI_BREAKER_FAILURES` large failures in the window | breaker opens for `AI_BREAKER_OPEN_S`; requests go straight to compact | banner "Large model temporarily unavailable" (from `/api/system/status`) |
| Too many concurrent large calls | bounded queue; wait ≤ `AI_LARGE_QUEUE_WAIT_S`, else compact | banner shows queue depth; notice "many learners are using the large model" |
| Both categories down | labelled **offline generators** (rules / extractive answers from retrieved passages) | notice "AI service not reachable — offline mode" |
| No credentials configured | offline mode from start | persistent banner "Offline demo mode" |

Every response carries:

```json
"ai": {"tier": "compact|large|none", "model": "...", "provider": "live|offline", "cached": false,
       "fallback": false, "fallback_reason": null, "intended_tier": "large", "latency_ms": 1234, "notice": null}
```

The UI never freezes: `StagedProgress` advances through *triage → retrieve → reason → format* using typical
durations (`GET /api/tutor/stages`), and `/api/system/status` is polled every 20 s for the banner.

## 5. Telemetry

Each call is logged in `ai_calls` (task, tier, model, cached, fallback, latency, ok). The Analytics page
shows the compact/large split, cache-hit ratio and fallbacks per learner, and `/api/system/status`
exposes process-level counters — useful to prove efficient use of the shared service during the demo.
