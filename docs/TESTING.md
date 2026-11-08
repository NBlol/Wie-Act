# Testing strategy and results

*All figures below were measured on 5 November 2026 in the build sandbox. Nothing here is estimated.*

## 1. Strategy

| Level | What | How |
|---|---|---|
| Unit | `ModelRouter` (two-tier routing, cache, retries, fallback, breaker, queue, offline), BM25 tokenizer/ranking, chunking, extraction, language detection, JSON extraction | pytest with a **fake inference provider** (`tests/conftest.py::FakeProvider`) that returns well-formed JSON per task and can be told to fail (429/503), fail once (retry path) or sleep (queue path) |
| API / integration | Every feature end-to-end through the HTTP layer with the Starlette `TestClient` on a throw-away SQLite database: auth & erasure, diagnostic, tutor hint-first flow, dynamic routing of complex questions, quizzes (generation, batched grading, XP/badges, cache), rooms (participation balance, automatic nudge, explanation check, polling cursor, collaborative quiz, leaderboard, access control), documents (upload, search, cited answers, deletion), roadmaps, notes, analytics, teacher dashboard | pytest, same suite |
| Frontend static | TypeScript strict type-check (typed i18n keys guarantee FR/AR/TN dictionaries are complete), production build | `tsc -p tsconfig.json`, `node scripts/build.mjs` |
| End-to-end (browser) | Real backend (offline AI mode) + dev server + headless Chromium driving the real UI: register → diagnostic → dashboard → upload & ask a document → tutor (hint, reveal) → quiz (generate, answer, submit) → room (create, chat, moderator actions) → roadmap → notes → analytics → Arabic/Darija RTL → teacher dashboard → seeded unbalanced room → mobile viewport | `frontend/scripts/e2e.mjs` (Playwright), screenshots in `docs/screenshots/real-*.png`, summary in `docs/e2e-results.json` |
| Demo data | Synthetic accounts and material, seeded through the public API | `backend/scripts/seed_demo.py` |

## 2. Executed results

| Suite | Result |
|---|---|
| Backend pytest | **36 passed, 0 failed** in 7.1 s (Python 3.13, Starlette 1.7 compatibility layer, SQLite) |
| Frontend type-check | **0 errors** (TypeScript strict, 33 files, 7 812 lines) |
| Frontend build | OK — `main.js` 482.5 kB, `styles.css` 57 kB, build time ≈ 0.2 s |
| Browser end-to-end | **15 / 15 flows passed**, 0 page errors, 0 console errors |
| Backend size | 5 272 lines of Python, 50 HTTP endpoints, 18 tables |

### Router behaviours proven by `tests/test_router.py`

| Test | Verified behaviour |
|---|---|
| `test_routing_table_tier_selection` | compact/large/dynamic selection incl. complexity, hint level 3 and ≥ 3 passages → large |
| `test_live_call_uses_expected_model_and_parses_json` | the right model name is sent per category; JSON parsed |
| `test_cache_prevents_regenerating_equivalent_requests` | second equivalent request (different case/whitespace) → 0 provider calls, `cached: true` |
| `test_retry_then_success_on_transient_error` | one 503 then success → 2 calls, no fallback |
| `test_large_unavailable_falls_back_to_compact_with_notice` | large 503 → compact answer, `fallback_reason=large_unavailable`, notice in French |
| `test_rate_limit_reason_is_reported` | large 429 → `fallback_reason=rate_limited` |
| `test_circuit_breaker_opens_after_repeated_large_failures` | after N failures the breaker opens; later requests go straight to compact; status exposes `large_breaker_open_until` |
| `test_queue_full_falls_back_instead_of_blocking` | capacity + 2 concurrent large requests → capacity served by large, 2 by compact with `queue_full` |
| `test_all_tiers_down_degrades_to_offline_generators` | both categories failing → labelled offline extractive answer, `errors` counter incremented |
| `test_offline_mode_without_api_key` | no credentials → `provider: offline`, `fallback_reason: no_api_key`, Darija detected |
| `test_unparseable_model_output_is_kept_as_raw` | prose instead of JSON is kept, not discarded |

### Call-budget assertions in the API tests

* A quiz submission with 6 questions (4 MCQ + 2 short) performs **exactly 2** provider calls (one batched grading, one feedback).
* A guided tutor turn with low complexity and no passages uses the **compact** model; the "reveal" turn uses the **large** model.
* Checking a peer explanation uses the **large** model; nudges and guiding questions use the **compact** model.

## 3. End-to-end run (browser)

| # | Flow | Result | Screenshot |
|---|---|---|---|
| 1 | Landing page renders | ✓ | `real-landing.png` |
| 2 | Register through the UI | ✓ | — |
| 3 | Onboarding diagnostic (9 questions, level, goal) → profile | ✓ | `real-onboarding*.png` |
| 4 | Dashboard (XP, style card, next step, AI-efficiency) | ✓ | `real-dashboard.png` |
| 5 | Upload Markdown course → cited answer ("RuBisCO") | ✓ | `real-document-ask.png` |
| 6 | Tutor: guided hint with guiding question/next step → reveal | ✓ | `real-tutor.png` |
| 7 | Quiz: generate, answer MCQ + short, submit → results, XP, badge | ✓ | `real-quiz-results.png` |
| 8 | Room: create, chat, nudge, moderator messages | ✓ | `real-room.png` |
| 9 | Roadmap: generate, tick activity → progress | ✓ | `real-roadmap.png` |
| 10 | Notes from a document (summary + flashcards) | ✓ | `real-notes.png` |
| 11 | Analytics page | ✓ | `real-analytics.png` |
| 12 | Language switch to Arabic (dir=rtl) and Darija | ✓ | `real-dashboard-ar.png`, `real-tutor-tn.png` |
| 13 | Teacher dashboard (class aggregates) | ✓ | `real-teacher.png` |
| 14 | Seeded room with unbalanced participation (balance 37 %, quiet member named by the moderator) | ✓ | `real-room-seeded.png` |
| 15 | Mobile viewport 390 × 844 | ✓ | `real-mobile-tutor.png` |

## 4. What has NOT been tested (to be done with platform credentials)

* **The real FastAPI package, PostgreSQL via psycopg and the Docker images** could not be executed in the sandbox (PyPI/npm unreachable). The code paths exist and are standard; run `pip install -r requirements.txt && pytest`, `npm install && npm run check` and `docker compose up --build` on a connected machine before submission.
* **Real inference calls**: no credentials were available. Latency, JSON compliance and pedagogical quality of the compact/large models must be measured with the team's key (fill the measured numbers into the report). The provider adapters were written against the OpenAI-compatible and Anthropic wire formats but were only exercised with the fake provider.
* **Load**: the queue and breaker were tested with threads in-process, not under multi-worker load.
* **Real user testing** (bonus): not yet performed; the seeder and anonymised accounts make a 5–10 learner session easy to run.

## 5. How to re-run

```bash
cd backend && python -m pytest                      # unit + API tests
cd frontend && npm run typecheck && npm run build   # static checks
# end-to-end (two terminals): uvicorn app.main:app --port 8000 ; node scripts/dev.mjs
cd backend && python scripts/seed_demo.py           # synthetic data (teacher/room flows depend on it)
cd frontend && node scripts/e2e.mjs --shots ../docs/screenshots
```
