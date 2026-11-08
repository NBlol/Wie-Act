"""
The documented, deliberate model-routing table.

Each AI step is assigned to the COMPACT (fast) or LARGE (capable) model
category. The compact model handles everything it can do correctly
(classification, extraction, formatting, short summaries, templated
facilitation); the large model is reserved for steps that genuinely need
multi-step reasoning, multi-source synthesis, planning or polished writing.
Some tasks are routed dynamically from the request itself (`tier` callable).

This table is served on `GET /api/system/routing` and reproduced in the
technical report.
"""
from __future__ import annotations

import typing as t
from dataclasses import dataclass, field

COMPACT = "compact"
LARGE = "large"


@dataclass
class TaskSpec:
    name: str
    tier: str | t.Callable[[dict], str]
    rationale: str
    max_tokens: int = 600
    temperature: float = 0.3
    json_output: bool = True
    cacheable: bool = True
    # keys of the input dict that define request equivalence for caching
    cache_keys: tuple[str, ...] = field(default_factory=tuple)

    def resolve_tier(self, inputs: dict) -> str:
        return self.tier if isinstance(self.tier, str) else self.tier(inputs)

    def tier_label(self) -> str:
        return self.tier if isinstance(self.tier, str) else "dynamic"


def _tutor_answer_tier(inputs: dict) -> str:
    """Compact for low-complexity Q&A with ≤2 passages; large for reasoning, full solutions or synthesis."""
    if inputs.get("complexity") == "high":
        return LARGE
    if int(inputs.get("hint_level", 0)) >= 2 or inputs.get("mode") == "direct" and inputs.get("intent") in ("exercise_help", "answer_request"):
        return LARGE
    if len(inputs.get("sources") or []) >= 3:
        return LARGE
    return COMPACT


def _rag_tier(inputs: dict) -> str:
    """Single high-confidence passage + short question → compact; otherwise multi-source synthesis → large."""
    sources = inputs.get("sources") or []
    if len(sources) <= 2 and len(inputs.get("question", "")) < 120 and sources and float(sources[0].get("score", 0)) >= 0.75:
        return COMPACT
    return LARGE


TASKS: dict[str, TaskSpec] = {
    "tutor_triage": TaskSpec(
        "tutor_triage", COMPACT,
        "Pure classification (language, intent, confusion, complexity): the compact model does this correctly in ~1 s and its output decides whether the large model is needed at all.",
        max_tokens=160, temperature=0.0, cache_keys=("message", "preferred_language"),
    ),
    "tutor_answer": TaskSpec(
        "tutor_answer", _tutor_answer_tier,
        "Dynamic: definitions, simple clarifications and single-passage answers go to the compact model; multi-step reasoning, full worked solutions (hint level 3) and ≥3-passage synthesis go to the large model.",
        max_tokens=900, temperature=0.4,
        cache_keys=("message", "language", "learning_style", "level", "mode", "hint_level", "source_ids", "history_digest"),
    ),
    "diagnostic_summary": TaskSpec(
        "diagnostic_summary", COMPACT,
        "Scores are computed locally; the model only writes a 3-sentence personalised summary from structured input — a short-writing task.",
        max_tokens=300, temperature=0.5, cache_keys=("learning_style", "secondary_style", "level", "language", "goal"),
    ),
    "quiz_generate": TaskSpec(
        "quiz_generate", LARGE,
        "Writing N distinct, correct questions with plausible misconception-based distractors and explanations requires reasoning about the content; quality here drives the whole assessment loop.",
        max_tokens=2200, temperature=0.6, cache_keys=("topic", "num_questions", "difficulty", "language", "question_types", "source_ids"),
    ),
    "quiz_grade_short": TaskSpec(
        "quiz_grade_short", COMPACT,
        "Comparing 1-sentence answers against expected answers is a bounded judgement task, batched in ONE call per submission; MCQs are graded locally with no model call at all.",
        max_tokens=600, temperature=0.0, cache_keys=("items", "language"),
    ),
    "quiz_feedback": TaskSpec(
        "quiz_feedback", COMPACT,
        "The per-question results are already computed; the model turns structured results into 3 encouraging sentences.",
        max_tokens=260, temperature=0.5, cache_keys=("topic", "percent", "results_digest", "language", "learning_style"),
    ),
    "room_nudge": TaskSpec(
        "room_nudge", COMPACT,
        "Participation statistics are computed in code; the model writes a short, warm invitation to the quiet members — formatting + tone, not reasoning.",
        max_tokens=200, temperature=0.7, cacheable=False,
    ),
    "room_guiding_question": TaskSpec(
        "room_guiding_question", COMPACT,
        "One Socratic question from the last few messages: short, local context, low stakes.",
        max_tokens=160, temperature=0.7, cacheable=False,
    ),
    "room_check_explanation": TaskSpec(
        "room_check_explanation", LARGE,
        "Verifying whether a peer's explanation is correct is exactly where unclear or wrong explanations get accepted — it needs the capable model's reasoning.",
        max_tokens=700, temperature=0.2, cache_keys=("explanation", "topic", "language"),
    ),
    "room_summary": TaskSpec(
        "room_summary", LARGE,
        "Synthesising a whole discussion into revision notes is multi-source synthesis and polished writing.",
        max_tokens=900, temperature=0.3, cache_keys=("messages_digest", "topic", "language"),
    ),
    "rag_answer": TaskSpec(
        "rag_answer", _rag_tier,
        "Dynamic: a short question answered by one high-scoring passage is handled by the compact model; combining several passages is synthesis and goes to the large model.",
        max_tokens=700, temperature=0.2, cache_keys=("question", "language", "source_ids"),
    ),
    "roadmap_generate": TaskSpec(
        "roadmap_generate", LARGE,
        "Planning a multi-week programme with dependencies and self-assessment checkpoints is a planning task.",
        max_tokens=2000, temperature=0.5, cache_keys=("goal", "weeks", "hours_per_week", "language", "learning_style", "level", "source_ids"),
    ),
    "notes_generate": TaskSpec(
        "notes_generate", LARGE,
        "Revision notes and flashcards from long material = multi-source synthesis + final polished writing.",
        max_tokens=2000, temperature=0.4, cache_keys=("material_digest", "language", "format", "topic"),
    ),
}

NO_MODEL_STEPS: list[dict[str, str]] = [
    {"task": "language_detection (fallback)", "tier": "none", "rationale": "Script + lexical heuristics; folded into the compact triage call when live."},
    {"task": "document_retrieval (RAG)", "tier": "none", "rationale": "BM25 ranking over local chunks narrows the context before any model call (fewer tokens, better relevance)."},
    {"task": "mcq_grading", "tier": "none", "rationale": "Multiple-choice answers are graded in code."},
    {"task": "participation_balance", "tier": "none", "rationale": "Room participation statistics are computed in code and only summarised by the compact model."},
    {"task": "diagnostic_scoring", "tier": "none", "rationale": "Learning-style scores and level are computed deterministically from the questionnaire."},
    {"task": "next_step_suggestion", "tier": "none", "rationale": "Rule-based from analytics (weak skills, inactivity, pending roadmap steps)."},
    {"task": "response_cache", "tier": "none", "rationale": "Equivalent requests (same task, tier and normalised inputs) are served from the cache instead of being regenerated."},
]


def routing_table() -> list[dict[str, str]]:
    rows = [{"task": s.name, "tier": s.tier_label(), "rationale": s.rationale} for s in TASKS.values()]
    return rows + NO_MODEL_STEPS
