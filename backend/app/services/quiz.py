"""Quiz generation (large model) and correction (local for MCQ, one batched compact call for short answers)."""
from __future__ import annotations

import hashlib
import typing as t

from app.ai import offline
from app.ai.router import ModelRouter
from app.compat import HTTPException, status
from app.db import Connection
from app.rag import index as rag_index
from app.services.gamification import record_event
from app.utils import SUPPORTED_LANGUAGES, dumps, loads, new_id, now_iso, truncate

_OPTION_IDS = ["a", "b", "c", "d", "e", "f"]


def _clean_questions(raw: t.Any, allowed_types: list[str], n: int) -> list[dict]:
    items = raw.get("questions") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    cleaned: list[dict] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        qtype = item.get("type") if item.get("type") in ("mcq", "short") else "mcq"
        if qtype not in allowed_types:
            qtype = allowed_types[0]
        q: dict[str, t.Any] = {
            "id": new_id(),
            "type": qtype,
            "text": str(item["text"]).strip(),
            "skill": truncate(str(item.get("skill") or "General"), 40),
            "explanation": truncate(str(item.get("explanation") or ""), 600),
        }
        if qtype == "mcq":
            options = item.get("options") or []
            norm: list[dict] = []
            for i, opt in enumerate(options[:6]):
                if isinstance(opt, dict):
                    norm.append({"id": str(opt.get("id") or _OPTION_IDS[i]).lower()[:1], "text": str(opt.get("text", "")).strip()})
                else:
                    norm.append({"id": _OPTION_IDS[i], "text": str(opt).strip()})
            # re-letter options a..f and remap the correct id
            correct_raw = str(item.get("correct_option_id") or "").lower()[:1]
            correct_idx = next((i for i, o in enumerate(norm) if o["id"] == correct_raw), 0)
            for i, o in enumerate(norm):
                o["id"] = _OPTION_IDS[i]
            if len(norm) < 2 or not all(o["text"] for o in norm):
                continue
            q["options"] = norm
            q["correct_option_id"] = _OPTION_IDS[correct_idx]
        else:
            q["expected_answer"] = str(item.get("expected_answer") or item.get("answer") or "").strip()
            if not q["expected_answer"]:
                continue
        cleaned.append(q)
        if len(cleaned) >= n:
            break
    return cleaned


def public_question(q: dict) -> dict:
    out = {"id": q["id"], "type": q["type"], "text": q["text"], "skill": q.get("skill")}
    if q["type"] == "mcq":
        out["options"] = q["options"]
    return out


def serialize_quiz(row: dict, include_answers: bool = False, ai: dict | None = None) -> dict:
    questions = loads(row["questions_json"], [])
    return {
        "id": row["id"],
        "topic": row["topic"],
        "language": row["language"],
        "difficulty": row["difficulty"],
        "source": row["source"],
        "document_id": row.get("document_id"),
        "room_id": row.get("room_id"),
        "created_at": row["created_at"],
        "questions": questions if include_answers else [public_question(q) for q in questions],
        "ai": ai if ai is not None else loads(row.get("ai_json"), None),
    }


def generate_quiz(
    db: Connection,
    router: ModelRouter,
    user: dict,
    *,
    topic: str | None,
    document_id: str | None,
    num_questions: int,
    difficulty: str,
    language: str | None,
    question_types: list[str],
    room_id: str | None = None,
) -> dict:
    if not topic and not document_id:
        raise HTTPException(422, "Provide a topic or a document_id")
    lang = language if language in SUPPORTED_LANGUAGES else user.get("preferred_language", "en")
    if difficulty == "auto":
        difficulty = user.get("level") or "intermediate"
    sources: list[dict] = []
    doc = None
    if document_id:
        doc = db.fetchone("SELECT * FROM documents WHERE id = ? AND user_id = ?", (document_id, user["id"]))
        if not doc and room_id:
            doc = db.fetchone("SELECT * FROM documents WHERE id = ?", (document_id,))
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        sources = rag_index.search(db, document_id, topic, k=6) if topic else []
        if len(sources) < 3:
            sources = rag_index.sample_chunks(db, document_id, limit=6)
        topic = topic or doc["title"]
    inputs = {
        "topic": topic,
        "num_questions": num_questions,
        "difficulty": difficulty,
        "language": lang,
        "darija_script": user.get("darija_script", "arabic"),
        "question_types": sorted(question_types),
        "sources": sources,
        "source_ids": rag_index.source_ids(sources),
    }
    out = router.run("quiz_generate", inputs, user_id=user["id"], db=db)
    questions = _clean_questions(out.data, sorted(question_types) or ["mcq"], num_questions)
    if len(questions) < 3:
        # the model output was unusable → deterministic fallback, clearly labelled in `ai`
        questions = _clean_questions(offline.quiz_generate(inputs), sorted(question_types) or ["mcq"], num_questions)
        out.ai = {**out.ai, "fallback": True, "fallback_reason": out.ai.get("fallback_reason") or "unparseable_output", "notice": out.ai.get("notice") or offline.NOTICE.get(lang, offline.NOTICE["en"])}
    qid = new_id()
    db.execute(
        "INSERT INTO quizzes (id, user_id, room_id, topic, language, difficulty, source, document_id, questions_json, ai_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (qid, user["id"], room_id, topic, lang, difficulty, "document" if document_id else "topic", document_id, dumps(questions), dumps(out.ai), now_iso()),
    )
    row = db.fetchone("SELECT * FROM quizzes WHERE id = ?", (qid,))
    assert row
    return serialize_quiz(row, ai=out.ai)


def get_accessible_quiz(db: Connection, user_id: str, quiz_id: str) -> dict:
    row = db.fetchone("SELECT * FROM quizzes WHERE id = ?", (quiz_id,))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    if row["user_id"] != user_id:
        if not row.get("room_id") or not db.fetchone("SELECT 1 FROM room_members WHERE room_id = ? AND user_id = ?", (row["room_id"], user_id)):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz not found")
    return row


def submit_quiz(db: Connection, router: ModelRouter, user: dict, quiz_row: dict, answers: list[dict], time_spent_s: int) -> dict:
    questions: list[dict] = loads(quiz_row["questions_json"], [])
    by_id = {q["id"]: q for q in questions}
    given = {a["question_id"]: a for a in answers}
    language = quiz_row["language"]
    results: list[dict] = []
    short_items: list[tuple[dict, dict]] = []
    for q in questions:
        ans = given.get(q["id"], {})
        if q["type"] == "mcq":
            chosen = ans.get("option_id")
            correct = chosen == q["correct_option_id"]
            correct_text = next((o["text"] for o in q["options"] if o["id"] == q["correct_option_id"]), q["correct_option_id"])
            your = next((o["text"] for o in q["options"] if o["id"] == chosen), chosen or "")
            results.append({"question_id": q["id"], "correct": correct, "score": 1.0 if correct else 0.0, "your_answer": your, "correct_answer": correct_text, "explanation": q.get("explanation", ""), "skill": q.get("skill"), "feedback": None})
        else:
            text = (ans.get("text") or "").strip()
            results.append({"question_id": q["id"], "correct": False, "score": 0.0, "your_answer": text, "correct_answer": q["expected_answer"], "explanation": q.get("explanation", ""), "skill": q.get("skill"), "feedback": None})
            if text:
                short_items.append((q, results[-1]))
    # ONE batched compact call for all short answers
    grade_ai: dict | None = None
    if short_items:
        payload = {
            "items": [{"question": q["text"], "expected_answer": q["expected_answer"], "learner_answer": r["your_answer"]} for q, r in short_items],
            "language": language,
            "darija_script": user.get("darija_script", "arabic"),
        }
        out = router.run("quiz_grade_short", payload, user_id=user["id"], db=db)
        grade_ai = out.ai
        grades = out.data.get("grades") if isinstance(out.data, dict) else None
        for i, (q, r) in enumerate(short_items):
            g = grades[i] if isinstance(grades, list) and i < len(grades) and isinstance(grades[i], dict) else None
            heuristic = offline.grade_short_heuristic(q["expected_answer"], r["your_answer"])
            if g is not None:
                try:
                    s = float(g.get("score", heuristic))
                except (TypeError, ValueError):
                    s = heuristic
                s = 1.0 if s >= 0.75 else 0.5 if s >= 0.25 else 0.0
                r["feedback"] = truncate(str(g.get("feedback") or ""), 400) or None
            else:
                s = heuristic
            r["score"] = s
            r["correct"] = s >= 1.0
    score = round(sum(r["score"] for r in results), 2)
    total = len(questions)
    percent = round(100 * score / total) if total else 0
    results_digest = hashlib.sha256(dumps([(r["skill"], r["score"]) for r in results]).encode()).hexdigest()[:16]
    fb_out = router.run(
        "quiz_feedback",
        {
            "topic": quiz_row["topic"], "percent": percent, "results": [{"skill": r["skill"], "correct": r["correct"]} for r in results],
            "results_digest": results_digest, "language": language, "darija_script": user.get("darija_script", "arabic"),
            "learning_style": user.get("learning_style") or "step_by_step",
        },
        user_id=user["id"],
        db=db,
    )
    feedback = fb_out.data.get("feedback") if isinstance(fb_out.data, dict) else None
    feedback = feedback or offline.quiz_feedback({"percent": percent, "results": results, "language": language, "learning_style": user.get("learning_style")})["feedback"]
    attempt_id = new_id()
    db.execute(
        "INSERT INTO quiz_attempts (id, quiz_id, user_id, answers_json, results_json, score, total, percent, time_spent_s, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (attempt_id, quiz_row["id"], user["id"], dumps(answers), dumps(results), score, total, percent, time_spent_s, now_iso()),
    )
    bonus = int(percent // 10)
    rewards = record_event(
        db, user["id"], "quiz_completed",
        {"quiz_id": quiz_row["id"], "topic": quiz_row["topic"], "percent": percent, "skills": [{"skill": r["skill"], "score": r["score"]} for r in results], "time_spent_s": time_spent_s, "room_id": quiz_row.get("room_id")},
        xp=10 + bonus,
    )
    return {
        "attempt_id": attempt_id,
        "score": score,
        "total": total,
        "percent": percent,
        "results": results,
        "feedback": feedback,
        "ai": {**fb_out.ai, "grading": grade_ai},
        **rewards,
    }


def quiz_summaries(db: Connection, user_id: str) -> list[dict]:
    rows = db.fetchall(
        "SELECT q.id, q.topic, q.language, q.difficulty, q.source, q.room_id, q.created_at, q.questions_json, "
        "(SELECT MAX(percent) FROM quiz_attempts a WHERE a.quiz_id = q.id AND a.user_id = ?) AS best_score, "
        "(SELECT COUNT(*) FROM quiz_attempts a WHERE a.quiz_id = q.id AND a.user_id = ?) AS attempts "
        "FROM quizzes q WHERE q.user_id = ? OR q.room_id IN (SELECT room_id FROM room_members WHERE user_id = ?) ORDER BY q.created_at DESC LIMIT 100",
        (user_id, user_id, user_id, user_id),
    )
    return [
        {
            "id": r["id"], "topic": r["topic"], "language": r["language"], "difficulty": r["difficulty"], "source": r["source"], "room_id": r.get("room_id"),
            "num_questions": len(loads(r["questions_json"], [])), "created_at": r["created_at"],
            "best_score": r.get("best_score"), "attempts": int(r.get("attempts") or 0),
        }
        for r in rows
    ]
