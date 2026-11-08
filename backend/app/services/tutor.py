"""Tutor conversation logic: triage → retrieve → reason → format (at most 2 model calls per turn)."""
from __future__ import annotations

import hashlib
import re
import typing as t

from app.ai import offline
from app.ai.router import ModelRouter
from app.compat import HTTPException, status
from app.db import Connection
from app.rag import index as rag_index
from app.services.gamification import record_event
from app.utils import LEARNING_STYLES, SUPPORTED_LANGUAGES, dumps, loads, new_id, now_iso, truncate

VALID_INTENTS = {"explain", "exercise_help", "answer_request", "quiz_request", "chit_chat", "other"}
_DOCUMENT_TASK_RE = re.compile(
    r"\b(summar(?:y|ize|ise|ized|ised)|explain|overview|main idea|key points|outline|what is this about)\b", re.I
)


def _is_document_task(content: str, has_document: bool) -> bool:
    return has_document and bool(_DOCUMENT_TASK_RE.search(content))


def serialize_conversation(row: dict, message_count: int | None = None) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "language": row["language"],
        "document_id": row.get("document_id"),
        "hint_level": int(row.get("hint_level") or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "message_count": message_count,
    }


def serialize_message(row: dict) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
        "meta": loads(row.get("meta_json"), {}),
    }


def get_owned_conversation(db: Connection, user_id: str, conversation_id: str) -> dict:
    row = db.fetchone("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return row


def create_conversation(db: Connection, user: dict, title: str | None, language: str | None, document_id: str | None) -> dict:
    if document_id and not db.fetchone("SELECT id FROM documents WHERE id = ? AND user_id = ?", (document_id, user["id"])):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    cid = new_id()
    now = now_iso()
    lang = language if language in SUPPORTED_LANGUAGES else user.get("preferred_language", "en")
    db.execute(
        "INSERT INTO conversations (id, user_id, title, language, document_id, hint_level, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
        (cid, user["id"], (title or "New conversation").strip()[:120], lang, document_id, now, now),
    )
    row = db.fetchone("SELECT * FROM conversations WHERE id = ?", (cid,))
    assert row
    return row


def _save_message(db: Connection, conversation_id: str, role: str, content: str, meta: dict | None = None) -> dict:
    mid = new_id()
    now = now_iso()
    db.execute(
        "INSERT INTO messages (id, conversation_id, role, content, meta_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (mid, conversation_id, role, content, dumps(meta or {}), now),
    )
    return {"id": mid, "role": role, "content": content, "created_at": now, "meta": meta or {}}


def _retrieve(db: Connection, user_id: str, conversation: dict, query: str, use_documents: bool) -> list[dict]:
    if not use_documents:
        return []
    if conversation.get("document_id"):
        if _is_document_task(query, True):
            return rag_index.sample_chunks(db, conversation["document_id"], limit=8)
        return rag_index.search(db, conversation["document_id"], query, k=4)
    docs = db.fetchall("SELECT id FROM documents WHERE user_id = ? AND status = 'ready' ORDER BY created_at DESC LIMIT 5", (user_id,))
    merged: list[dict] = []
    for d in docs:
        merged.extend(rag_index.search(db, d["id"], query, k=3))
    merged.sort(key=lambda s: -s["score"])
    return merged[:4]


def _normalise_triage(raw: dict | None, message: str, preferred_language: str) -> dict:
    fallback = offline.tutor_triage({"message": message, "preferred_language": preferred_language})
    raw = raw or {}
    language = raw.get("language") if raw.get("language") in SUPPORTED_LANGUAGES else fallback["language"]
    intent = raw.get("intent") if raw.get("intent") in VALID_INTENTS else fallback["intent"]
    confusion = raw.get("confusion") if raw.get("confusion") in ("none", "mild", "high") else fallback["confusion"]
    complexity = raw.get("complexity") if raw.get("complexity") in ("low", "high") else fallback["complexity"]
    topic = truncate(str(raw.get("topic") or fallback["topic"]), 60)
    return {"language": language, "intent": intent, "confusion": confusion, "complexity": complexity, "topic": topic}


def answer_turn(
    db: Connection,
    router: ModelRouter,
    user: dict,
    conversation: dict,
    content: str,
    *,
    mode: str = "guided",
    use_documents: bool = True,
    style_override: str | None = None,
    reveal: bool = False,
) -> dict:
    user_message = None if reveal else _save_message(db, conversation["id"], "user", content)

    history_rows = db.fetchall(
        "SELECT role, content, meta_json FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT 9", (conversation["id"],)
    )
    history_rows.reverse()
    history = [{"role": r["role"], "content": r["content"]} for r in history_rows if r["role"] in ("user", "assistant")]
    if not reveal and history and history[-1]["content"] == content and history[-1]["role"] == "user":
        history = history[:-1]
    previous_assistant = next((h["content"] for h in reversed(history) if h["role"] == "assistant"), "")

    # 1) triage (compact model, or heuristics offline)
    triage_out = router.run(
        "tutor_triage",
        {"message": content, "preferred_language": conversation["language"], "previous_assistant": previous_assistant},
        user_id=user["id"],
        db=db,
    )
    triage = _normalise_triage(triage_out.data if isinstance(triage_out.data, dict) else None, content, conversation["language"])
    language = triage["language"]

    # 2) retrieval (no model call)
    sources = _retrieve(db, user["id"], conversation, content, use_documents)
    document_task = _is_document_task(content, bool(conversation.get("document_id"))) and use_documents
    conversational = triage["intent"] == "chit_chat" and not sources
    response_mode = "direct" if document_task or conversational else mode

    # hint policy
    hint_level = int(conversation.get("hint_level") or 0)
    if reveal:
        hint_level = 2
    elif triage["intent"] not in ("exercise_help", "answer_request") or response_mode == "direct":
        hint_level = 0

    style = style_override if style_override in LEARNING_STYLES else (user.get("learning_style") or "step_by_step")
    history_digest = hashlib.sha256(dumps(history[-2:]).encode()).hexdigest()[:16]

    # 3) reasoning / answer (compact or large, decided by the routing table)
    answer_out = router.run(
        "tutor_answer",
        {
            "message": content,
            "language": language,
            "darija_script": user.get("darija_script", "arabic"),
            "learning_style": style,
            "level": user.get("level") or "beginner",
            "mode": response_mode,
            "hint_level": hint_level,
            "intent": triage["intent"],
            "complexity": triage["complexity"],
            "confusion": triage["confusion"],
            "topic": triage["topic"],
            "sources": sources,
            "source_ids": rag_index.source_ids(sources),
            "history": history,
            "history_digest": history_digest,
            "document_task": document_task,
            "conversational": conversational,
        },
        user_id=user["id"],
        db=db,
    )
    data = answer_out.data if isinstance(answer_out.data, dict) else {}
    answer_md = data.get("answer_md") or data.get("_raw") or data.get("text") or ""
    if not answer_md:
        answer_md = offline.tutor_answer(
            {
                "message": content,
                "language": language,
                "learning_style": style,
                "sources": sources,
                "mode": response_mode,
                "hint_level": hint_level,
                "topic": triage["topic"],
                "document_task": document_task,
                "conversational": conversational,
            }
        )["answer_md"]

    # 4) format & persist
    next_hint_level = min(hint_level + 1, 2) if (response_mode == "guided" and triage["intent"] in ("exercise_help", "answer_request") and not reveal) else (2 if reveal else 0)
    # confusion = strongest signal between the triage classifier and the answering model
    order = ["none", "mild", "high"]
    model_confusion = data.get("confusion_detected") if data.get("confusion_detected") in order else "none"
    confusion = order[max(order.index(model_confusion), order.index(triage["confusion"]))]
    meta = {
        "ai": {"triage": triage_out.ai, **answer_out.ai},
        "triage": triage,
        "hint_level": hint_level,
        "mode": response_mode,
        "sources": [{"chunk_id": s["chunk_id"], "document_id": s["document_id"], "page": s["page"], "excerpt": truncate(s["excerpt"], 300), "score": s["score"]} for s in sources],
        "next_step": None if document_task or conversational else data.get("next_step"),
        "guiding_question": None if document_task or conversational else data.get("guiding_question"),
        "confusion_detected": confusion,
        "learning_style": style,
    }
    assistant_message = _save_message(db, conversation["id"], "assistant", answer_md, meta)

    title = conversation["title"]
    if title in ("New conversation", "") and not reveal:
        title = truncate(content.strip().splitlines()[0], 60)
    db.execute(
        "UPDATE conversations SET title = ?, hint_level = ?, last_question = ?, updated_at = ? WHERE id = ?",
        (title, next_hint_level, content if not reveal else conversation.get("last_question"), now_iso(), conversation["id"]),
    )

    rewards: dict[str, t.Any] = {"xp_gained": 0, "badges_unlocked": []}
    if reveal:
        rewards = record_event(db, user["id"], "answer_revealed", {"conversation_id": conversation["id"]})
    else:
        rewards = record_event(db, user["id"], "question_asked", {"conversation_id": conversation["id"], "topic": triage["topic"], "language": language, "complexity": triage["complexity"]})
    if meta["confusion_detected"] in ("mild", "high"):
        record_event(db, user["id"], "confusion_detected", {"conversation_id": conversation["id"], "topic": triage["topic"], "level": meta["confusion_detected"]}, xp=0)

    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
        "stages": ["triage", "retrieve", "reason", "format"],
        **rewards,
    }
