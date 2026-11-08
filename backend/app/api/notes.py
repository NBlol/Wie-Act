from __future__ import annotations

import hashlib

from app.ai import offline
from app.ai.router import get_router
from app.compat import APIRouter, Depends, HTTPException, Response, status
from app.db import Connection
from app.deps import get_current_user, get_db
from app.rag import index as rag_index
from app.schemas import NoteGenerate
from app.services.gamification import record_event
from app.utils import SUPPORTED_LANGUAGES, dumps, loads, new_id, now_iso, truncate

router = APIRouter(prefix="/notes", tags=["notes"])


def serialize(row: dict, ai: dict | None = None) -> dict:
    return {
        "id": row["id"], "title": row["title"], "source": row["source"], "source_id": row.get("source_id"), "language": row["language"],
        "content_md": row["content_md"], "flashcards": loads(row.get("flashcards_json"), []), "created_at": row["created_at"],
        "ai": ai if ai is not None else loads(row.get("ai_json"), None),
    }


def _material(db: Connection, user: dict, body: NoteGenerate) -> tuple[str, str]:
    """Collect the source material (text) and a default title."""
    if body.source == "conversation":
        conv = db.fetchone("SELECT * FROM conversations WHERE id = ? AND user_id = ?", (body.source_id, user["id"]))
        if not conv:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        msgs = db.fetchall("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT 60", (conv["id"],))
        text = "\n".join(f"{'Learner' if m['role'] == 'user' else 'Tutor'}: {truncate(m['content'], 1200)}" for m in msgs)
        return text, conv["title"]
    if body.source == "document":
        doc = db.fetchone("SELECT * FROM documents WHERE id = ? AND user_id = ?", (body.source_id, user["id"]))
        if not doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        chunks = rag_index.search(db, doc["id"], body.topic, k=8) if body.topic else rag_index.sample_chunks(db, doc["id"], limit=8)
        return "\n\n".join(f"(page {c['page']}) {c['excerpt']}" for c in chunks), body.topic or doc["title"]
    if body.source == "room":
        room = db.fetchone("SELECT * FROM rooms WHERE id = ?", (body.source_id,))
        if not room or not db.fetchone("SELECT 1 FROM room_members WHERE room_id = ? AND user_id = ?", (room["id"], user["id"])):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
        msgs = db.fetchall("SELECT display_name, content FROM room_messages WHERE room_id = ? AND role = 'member' ORDER BY created_at ASC LIMIT 80", (room["id"],))
        return "\n".join(f"{m['display_name']}: {truncate(m['content'], 600)}" for m in msgs), f"{room['name']} — {room['topic']}"
    if not body.topic:
        raise HTTPException(422, "A topic is required for topic notes")
    return f"Topic: {body.topic}", body.topic


@router.post("/generate", status_code=201)
def generate(body: NoteGenerate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    language = body.language if body.language in SUPPORTED_LANGUAGES else user.get("preferred_language", "en")
    material, default_title = _material(db, user, body)
    inputs = {
        "source": body.source, "topic": body.topic or default_title, "material": material, "format": body.format, "language": language,
        "darija_script": user.get("darija_script", "arabic"), "learning_style": user.get("learning_style") or "step_by_step",
        "material_digest": hashlib.sha256(material.encode()).hexdigest()[:24],
    }
    out = get_router().run("notes_generate", inputs, user_id=user["id"], db=db)
    data = out.data if isinstance(out.data, dict) else {}
    content = data.get("content_md") or data.get("_raw")
    if not content:
        data = offline.notes_generate(inputs)
        content = data["content_md"]
        out.ai = {**out.ai, "fallback": True, "fallback_reason": out.ai.get("fallback_reason") or "unparseable_output", "notice": out.ai.get("notice") or offline.NOTICE.get(language, offline.NOTICE["en"])}
    flashcards = [
        {"q": truncate(str(c.get("q", "")), 300), "a": truncate(str(c.get("a", "")), 500)}
        for c in (data.get("flashcards") or []) if isinstance(c, dict) and c.get("q") and c.get("a")
    ][:20]
    if body.format == "summary":
        flashcards = []
    nid = new_id()
    title = truncate(str(data.get("title") or default_title), 120)
    db.execute(
        "INSERT INTO notes (id, user_id, title, source, source_id, language, content_md, flashcards_json, ai_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (nid, user["id"], title, body.source, body.source_id, language, content, dumps(flashcards), dumps(out.ai), now_iso()),
    )
    rewards = record_event(db, user["id"], "note_generated", {"note_id": nid, "source": body.source})
    row = db.fetchone("SELECT * FROM notes WHERE id = ?", (nid,))
    assert row
    return {**serialize(row, out.ai), **rewards}


@router.get("")
def list_notes(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    rows = db.fetchall("SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))
    return [serialize(r) for r in rows]


@router.get("/{note_id}")
def get_note(note_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = db.fetchone("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user["id"]))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return serialize(row)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> Response:
    if not db.fetchone("SELECT 1 FROM notes WHERE id = ? AND user_id = ?", (note_id, user["id"])):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))
    return Response(status_code=204)
