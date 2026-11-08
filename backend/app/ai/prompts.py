"""
Prompt design for every AI task.

All "intelligence" comes from prompt design + supplied context + model-tier
choice (no fine-tuning is available on the challenge platform).  Every prompt
asks for compact JSON so that the application can post-process reliably.
"""
from __future__ import annotations

import json
import typing as t

from app.utils import LANGUAGE_NAMES, truncate

STYLE_INSTRUCTIONS: dict[str, str] = {
    "visual": "The learner is a VISUAL learner: describe what a diagram or sketch would show, use tables, spatial metaphors, arrows (→) and clear structure. Offer an ASCII sketch when useful.",
    "analogy": "The learner learns best through ANALOGIES: open with one vivid everyday analogy, then map each part of the analogy precisely onto the concept and say where the analogy breaks.",
    "step_by_step": "The learner needs STEP-BY-STEP reasoning: numbered steps, one operation per step, state why each step is taken, and add a quick check after the key step.",
    "examples": "The learner learns through CONCRETE EXAMPLES: start with 2 worked examples from daily life or practice, then state the general rule, then one counter-example.",
    "repetition": "The learner benefits from REPETITION: state the key idea, re-express it in different words, give a 2-line recap, and finish with one quick recall question.",
    "problem_solving": "The learner prefers DIRECT PROBLEM-SOLVING: pose a small problem first, invite the learner to try, then debrief the method. Keep theory minimal and actionable.",
}

LEVEL_INSTRUCTIONS: dict[str, str] = {
    "beginner": "Beginner level: plain words, define every technical term the first time, avoid jargon, short sentences.",
    "intermediate": "Intermediate level: assume the basics, focus on the connections between ideas and common mistakes.",
    "advanced": "Advanced level: be precise and rigorous, mention edge cases and formal definitions when relevant.",
}


def language_instruction(language: str, darija_script: str = "arabic") -> str:
    name = LANGUAGE_NAMES.get(language, "English")
    if language == "tn":
        script = "Arabic script" if darija_script == "arabic" else "Latin script ('Arabizi', e.g. 'chnowa', '3lech')"
        return (
            f"Respond ONLY in {name}, written in {script}. Use natural Tunisian phrasing (e.g. 'باهي', 'كيفاش', 'برشا', 'نجمو'), "
            "not Modern Standard Arabic and not Moroccan/Egyptian dialect. Keep technical terms in their usual French/English form when Tunisians do so. "
            "Use Latin digits (1 2 3), never Arabic-Indic digits."
        )
    if language == "ar":
        return f"Respond ONLY in {name} (فصحى واضحة ومبسطة). Use Latin digits (1 2 3), never Arabic-Indic digits."
    if language == "fr":
        return "Réponds UNIQUEMENT en français clair et bienveillant."
    return "Respond ONLY in clear, friendly English."


def _messages(system: str, user: str) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ----------------------------------------------------------------------------- tutor

def tutor_triage(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You are a fast classifier for a learning assistant. Read the learner's message and the short context. "
        "Return ONLY a JSON object with keys: "
        '"language" (one of en, fr, ar, tn — tn = Tunisian Darija in Arabic or Latin script), '
        '"intent" (explain | exercise_help | answer_request | quiz_request | chit_chat | other), '
        '"confusion" (none | mild | high — high when the learner says they do not understand, repeats a question, or expresses frustration), '
        '"complexity" (low for definitions, simple facts, short clarifications; high for multi-step reasoning, proofs, derivations, debugging, open analysis or when several document passages must be combined), '
        '"topic" (2-5 words).'
    )
    user = (
        f"Conversation language preference: {inputs.get('preferred_language', 'en')}\n"
        f"Previous assistant message (truncated): {truncate(inputs.get('previous_assistant', '') or '-', 400)}\n"
        f"Learner message: {inputs['message']}"
    )
    return _messages(system, user)


def tutor_answer(inputs: dict) -> list[dict[str, str]]:
    style = inputs.get("learning_style") or "step_by_step"
    level = inputs.get("level") or "beginner"
    language = inputs.get("language", "en")
    hint_level = int(inputs.get("hint_level", 0))
    mode = inputs.get("mode", "guided")
    sources: list[dict] = inputs.get("sources") or []
    confusion = inputs.get("confusion", "none")
    document_task = bool(inputs.get("document_task"))
    conversational = bool(inputs.get("conversational"))

    hint_rules = {
        "direct": "Mode DIRECT: give the complete explanation or solution, still clearly structured.",
        0: "Mode GUIDED, hint level 1: do NOT give the final answer to an exercise. Give the key idea or method to start, and ask the learner to attempt the first step.",
        1: "Mode GUIDED, hint level 2: do NOT give the final answer yet. Show the first worked step and a stronger hint for the next one.",
        2: "Mode GUIDED, hint level 3 (reveal): the learner asked for the full answer. Give the complete worked solution and explain each step.",
    }
    hint_rule = hint_rules["direct"] if mode == "direct" else hint_rules[min(hint_level, 2)]

    system = "\n".join(
        [
            "You are EdNova, a warm, natural conversational peer-learning tutor. Answer what the learner actually asked.",
            "Never judge a question as too simple. Be inclusive and neutral regarding gender, region, language level or background.",
            STYLE_INSTRUCTIONS.get(style, STYLE_INSTRUCTIONS["step_by_step"]),
            LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS["beginner"]),
            hint_rule,
            "This is casual conversation. Reply naturally and briefly, without analysis, study advice, a guiding question, or a quiz suggestion." if conversational else "",
            "The learner is asking about the attached document. Explain or summarize the supplied passages directly, preserve the important facts, and cite claims with [1], [2]. Do not give hints, a guiding question, a study tip, or a next-step suggestion." if document_task else "",
            "The learner currently seems CONFUSED: slow down, use simpler words, one idea at a time, and check understanding." if confusion in ("mild", "high") else "",
            language_instruction(language, inputs.get("darija_script", "arabic")),
            "If document passages are provided, ground your answer in them and cite them inline as [1], [2]; if the passages do not contain the answer, say so explicitly before using general knowledge.",
            "Keep the answer focused (max ~500 words for document explanations, otherwise ~250 words unless a full solution is requested). Use Markdown.",
            'Return ONLY a JSON object: {"answer_md": "...", "guiding_question": null, "next_step": null, "confusion_detected": "none|mild|high"}',
        ]
    ).strip()

    parts: list[str] = []
    if sources:
        parts.append("Document passages:")
        for i, src in enumerate(sources, 1):
            parts.append(f"[{i}] (page {src.get('page', '?')}) {truncate(src.get('excerpt', ''), 900)}")
        parts.append("")
    history: list[dict] = inputs.get("history") or []
    if history:
        parts.append("Recent conversation:")
        for msg in history[-8:]:
            role = "Learner" if msg.get("role") == "user" else "Tutor"
            parts.append(f"{role}: {truncate(msg.get('content', ''), 600)}")
        parts.append("")
    parts.append(f"Learner message: {inputs['message']}")
    return _messages(system, "\n".join(parts))


# ----------------------------------------------------------------------------- diagnostic

def diagnostic_summary(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You write a short, warm learning-profile summary for a learner who just completed a learning-style diagnostic. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"explanation": "2-3 sentences describing how this learner learns best and how the tutor will adapt", "recommendations": ["3 short, concrete study tips"]}'
    )
    user = json.dumps(
        {
            "learning_style": inputs.get("learning_style"),
            "secondary_style": inputs.get("secondary_style"),
            "level": inputs.get("level"),
            "style_scores": inputs.get("style_scores"),
            "goal": inputs.get("goal"),
        },
        ensure_ascii=False,
    )
    return _messages(system, user)


# ----------------------------------------------------------------------------- quizzes

def quiz_generate(inputs: dict) -> list[dict[str, str]]:
    n = int(inputs.get("num_questions", 5))
    types = inputs.get("question_types") or ["mcq"]
    language = inputs.get("language", "en")
    difficulty = inputs.get("difficulty", "intermediate")
    system = "\n".join(
        [
            f"You are an expert teacher writing a {difficulty}-level quiz of exactly {n} questions about the given topic or document passages.",
            f"Question types allowed: {', '.join(types)}. Prefer 'mcq' (4 options, exactly one correct, plausible distractors that target common misconceptions); use 'short' for questions needing a 1-sentence free answer.",
            "Each question must test a distinct skill; tag it with a short 'skill' label (2-4 words).",
            "If document passages are given, every question must be answerable from them.",
            language_instruction(language, inputs.get("darija_script", "arabic")),
            "Return ONLY JSON: {\"questions\": [{\"type\": \"mcq\", \"text\": \"...\", \"options\": [{\"id\": \"a\", \"text\": \"...\"}, {\"id\": \"b\", ...}, {\"id\": \"c\", ...}, {\"id\": \"d\", ...}], \"correct_option_id\": \"a\", \"explanation\": \"why, in 1-2 sentences\", \"skill\": \"...\"}, {\"type\": \"short\", \"text\": \"...\", \"expected_answer\": \"...\", \"explanation\": \"...\", \"skill\": \"...\"}]}",
        ]
    )
    parts = [f"Topic: {inputs.get('topic') or 'the document'}"]
    for i, src in enumerate(inputs.get("sources") or [], 1):
        parts.append(f"[{i}] (page {src.get('page', '?')}) {truncate(src.get('excerpt', ''), 1200)}")
    return _messages(system, "\n".join(parts))


def quiz_grade_short(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You grade learners' short free-text answers against the expected answers (one batch, several items). Be fair: accept equivalent formulations, give partial credit for incomplete but correct ideas. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON, one grade per item in the same order: {"grades": [{"score": 0 | 0.5 | 1, "feedback": "one encouraging sentence saying what was right and what was missing"}]}'
    )
    user = json.dumps({"items": inputs["items"]}, ensure_ascii=False)
    return _messages(system, user)


def quiz_feedback(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You write personalised, encouraging feedback after a quiz. Name the weakest skill and give ONE concrete tip adapted to the learner's learning style. 3 sentences maximum. "
        + STYLE_INSTRUCTIONS.get(inputs.get("learning_style") or "step_by_step", "")
        + " "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"feedback": "..."}'
    )
    user = json.dumps(
        {"topic": inputs.get("topic"), "percent": inputs.get("percent"), "results": inputs.get("results")},
        ensure_ascii=False,
    )
    return _messages(system, user)


# ----------------------------------------------------------------------------- rooms

def room_nudge(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You are the AI moderator of a peer-learning study room. Your job: keep the discussion balanced and focused, encourage EQUAL participation, and make it safe to ask simple questions. "
        "Write ONE short moderator message (max 60 words): warmly invite the quiet members BY NAME with an easy, specific question about the topic, gently thank the active members, never blame anyone. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"message": "..."}'
    )
    user = json.dumps(
        {
            "topic": inputs.get("topic"),
            "participation": inputs.get("participation"),
            "recent_messages": inputs.get("recent_messages"),
        },
        ensure_ascii=False,
    )
    return _messages(system, user)


def room_guiding_question(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You are the AI moderator of a peer-learning study room. Based on the recent discussion, ask ONE guiding question that pushes the group one step deeper (Socratic style), "
        "or redirects them to the topic if they drifted. Max 40 words. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"message": "..."}'
    )
    user = json.dumps({"topic": inputs.get("topic"), "recent_messages": inputs.get("recent_messages")}, ensure_ascii=False)
    return _messages(system, user)


def room_check_explanation(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You are the AI moderator of a peer-learning study room. A member explained a concept to the group. Carefully verify the explanation. "
        "Be kind and constructive: start by naming what is right, then correct any error or imprecision with a clear corrected version, then ask one follow-up question to the group. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"verdict": "correct|partially_correct|incorrect|unclear", "message": "markdown, max 180 words"}'
    )
    user = json.dumps(
        {"topic": inputs.get("topic"), "explanation_by": inputs.get("author"), "explanation": inputs.get("explanation"), "recent_messages": inputs.get("recent_messages")},
        ensure_ascii=False,
    )
    return _messages(system, user)


def room_summary(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You are the AI moderator of a peer-learning study room. Write the session summary as revision notes: key takeaways (bullets), misconceptions that were clarified, open questions, and 3 next steps for the group. Max 250 words, Markdown. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"message": "markdown"}'
    )
    user = json.dumps({"topic": inputs.get("topic"), "messages": inputs.get("messages")}, ensure_ascii=False)
    return _messages(system, user)


# ----------------------------------------------------------------------------- RAG

def rag_answer(inputs: dict) -> list[dict[str, str]]:
    system = (
        "You answer a learner's question using ONLY the numbered document passages provided. Cite passages inline as [1], [2]. "
        "If the passages do not contain the answer, say so clearly and suggest what to look for. Be concise and pedagogical. "
        + language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic"))
        + ' Return ONLY JSON: {"answer_md": "...", "used_sources": [1, 2]}'
    )
    parts = []
    for i, src in enumerate(inputs.get("sources") or [], 1):
        parts.append(f"[{i}] (page {src.get('page', '?')}) {truncate(src.get('excerpt', ''), 1200)}")
    parts.append("")
    parts.append(f"Question: {inputs['question']}")
    return _messages(system, "\n".join(parts))


# ----------------------------------------------------------------------------- roadmap / notes

def roadmap_generate(inputs: dict) -> list[dict[str, str]]:
    weeks = int(inputs.get("weeks", 4))
    system = "\n".join(
        [
            f"You are a learning coach. Design a realistic {weeks}-week learning roadmap for the learner's goal, {inputs.get('hours_per_week', 5)} hours per week.",
            "One milestone per week with: a title, a one-sentence objective, 3-5 activities (kinds: read, practice, quiz, discuss, watch, recall) adapted to the learner's style and level, and a checkpoint (how to self-assess).",
            STYLE_INSTRUCTIONS.get(inputs.get("learning_style") or "step_by_step", ""),
            LEVEL_INSTRUCTIONS.get(inputs.get("level") or "beginner", ""),
            language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic")),
            'Return ONLY JSON: {"milestones": [{"week": 1, "title": "...", "objective": "...", "activities": [{"text": "...", "kind": "read"}], "checkpoint": "..."}]}',
        ]
    )
    parts = [f"Goal: {inputs['goal']}"]
    for i, src in enumerate(inputs.get("sources") or [], 1):
        parts.append(f"[{i}] {truncate(src.get('excerpt', ''), 800)}")
    return _messages(system, "\n".join(parts))


def notes_generate(inputs: dict) -> list[dict[str, str]]:
    fmt = inputs.get("format", "both")
    system = "\n".join(
        [
            "You turn learning material into excellent revision notes: a clear title, Markdown notes with headings, key definitions in bold, a short worked example when relevant, and a 'Common mistakes' section.",
            "Also produce flashcards (question/answer pairs) that test recall of the key points." if fmt in ("both", "flashcards") else "Do not produce flashcards (return an empty list).",
            STYLE_INSTRUCTIONS.get(inputs.get("learning_style") or "step_by_step", ""),
            language_instruction(inputs.get("language", "en"), inputs.get("darija_script", "arabic")),
            'Return ONLY JSON: {"title": "...", "content_md": "...", "flashcards": [{"q": "...", "a": "..."}]}',
        ]
    )
    parts = [f"Source type: {inputs.get('source')}", f"Topic: {inputs.get('topic') or '-'}", "Material:"]
    parts.append(truncate(inputs.get("material", ""), 9000))
    return _messages(system, "\n".join(parts))


PROMPT_BUILDERS: dict[str, t.Callable[[dict], list[dict[str, str]]]] = {
    "tutor_triage": tutor_triage,
    "tutor_answer": tutor_answer,
    "diagnostic_summary": diagnostic_summary,
    "quiz_generate": quiz_generate,
    "quiz_grade_short": quiz_grade_short,
    "quiz_feedback": quiz_feedback,
    "room_nudge": room_nudge,
    "room_guiding_question": room_guiding_question,
    "room_check_explanation": room_check_explanation,
    "room_summary": room_summary,
    "rag_answer": rag_answer,
    "roadmap_generate": roadmap_generate,
    "notes_generate": notes_generate,
}
