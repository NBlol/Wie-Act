"""Collaborative learning rooms with an AI moderator that encourages equal participation."""
from __future__ import annotations

import math
import typing as t

from app.ai.router import ModelRouter
from app.compat import HTTPException, status
from app.config import settings
from app.db import Connection
from app.services.gamification import record_event
from app.utils import SUPPORTED_LANGUAGES, dumps, loads, new_id, now_iso, room_code, truncate

MODERATOR_NAME = "EdNova moderator"


def _members(db: Connection, room_id: str) -> list[dict]:
    return db.fetchall(
        "SELECT m.user_id, u.display_name, m.joined_at, "
        "(SELECT COUNT(*) FROM room_messages rm WHERE rm.room_id = m.room_id AND rm.user_id = m.user_id) AS message_count "
        "FROM room_members m JOIN users u ON u.id = m.user_id WHERE m.room_id = ? ORDER BY m.joined_at",
        (room_id,),
    )


def participation(members: list[dict]) -> dict:
    counts = [int(m.get("message_count") or 0) for m in members]
    total = sum(counts)
    n = len(members)
    if n <= 1 or total == 0:
        return {"balance_score": 1.0, "dominant_member": None, "quiet_members": [], "total_messages": total, "per_member": [{"display_name": m["display_name"], "count": c} for m, c in zip(members, counts)]}
    probs = [c / total for c in counts if c > 0]
    entropy = -sum(p * math.log(p) for p in probs)
    balance = round(entropy / math.log(n), 3) if n > 1 else 1.0
    avg = total / n
    dominant = None
    quiet: list[str] = []
    if total >= 4:
        for m, c in zip(members, counts):
            if c / total > 0.5:
                dominant = m["display_name"]
            if c < 0.25 * avg:
                quiet.append(m["display_name"])
    return {
        "balance_score": balance,
        "dominant_member": dominant,
        "quiet_members": quiet,
        "total_messages": total,
        "per_member": [{"display_name": m["display_name"], "count": c} for m, c in zip(members, counts)],
    }


def serialize_message(row: dict) -> dict:
    return {
        "id": row["id"],
        "room_id": row["room_id"],
        "user_id": row.get("user_id"),
        "display_name": row["display_name"],
        "role": row["role"],
        "content": row["content"],
        "created_at": row["created_at"],
        "meta": loads(row.get("meta_json"), {}),
    }


def serialize_room(db: Connection, row: dict, user_id: str | None = None) -> dict:
    members = _members(db, row["id"])
    return {
        "id": row["id"],
        "code": row["code"],
        "name": row["name"],
        "topic": row["topic"],
        "language": row["language"],
        "owner_id": row["owner_id"],
        "created_at": row["created_at"],
        "quiz_id": row.get("quiz_id"),
        "member_count": len(members),
        "is_owner": user_id == row["owner_id"] if user_id else None,
        "members": [{"user_id": m["user_id"], "display_name": m["display_name"], "joined_at": m["joined_at"], "message_count": int(m.get("message_count") or 0)} for m in members],
        "participation": participation(members),
    }


def get_member_room(db: Connection, user_id: str, room_id: str) -> dict:
    row = db.fetchone("SELECT * FROM rooms WHERE id = ?", (room_id,))
    if not row or not db.fetchone("SELECT 1 FROM room_members WHERE room_id = ? AND user_id = ?", (room_id, user_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    return row


def create_room(db: Connection, user: dict, name: str, topic: str, language: str | None) -> dict:
    lang = language if language in SUPPORTED_LANGUAGES else user.get("preferred_language", "en")
    rid = new_id()
    code = room_code()
    while db.fetchone("SELECT 1 FROM rooms WHERE code = ?", (code,)):
        code = room_code()
    now = now_iso()
    db.execute(
        "INSERT INTO rooms (id, code, name, topic, language, owner_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rid, code, name.strip(), topic.strip(), lang, user["id"], now),
    )
    db.execute("INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?, ?, ?)", (rid, user["id"], now))
    welcome = {
        "en": f"Welcome to **{name}**! Topic: {topic}. I'm the EdNova moderator: I keep the discussion balanced, ask guiding questions and can check explanations or summarise the session. Mention @ednova to ask me something.",
        "fr": f"Bienvenue dans **{name}** ! Sujet : {topic}. Je suis le modérateur EdNova : je veille à l'équilibre des échanges, pose des questions guides et peux vérifier une explication ou résumer la séance. Mentionnez @ednova pour me solliciter.",
        "ar": f"مرحباً بكم في **{name}**! الموضوع: {topic}. أنا مشرف EdNova: أحافظ على توازن النقاش، أطرح أسئلة موجهة، ويمكنني التحقق من شرح أو تلخيص الجلسة. اذكروا @ednova لسؤالي.",
        "tn": f"مرحبا بيكم في **{name}**! الموضوع: {topic}. أنا موديراتور EdNova: نخلّي النقاش متوازن، نسأل أسئلة موجّهة، ونجم نتثبّت من شرح ولا نلخّص الحصّة. اكتبو @ednova باش تسألوني.",
    }
    _post_moderator(db, rid, welcome.get(lang, welcome["en"]), {"kind": "welcome"})
    record_event(db, user["id"], "room_created", {"room_id": rid})
    row = db.fetchone("SELECT * FROM rooms WHERE id = ?", (rid,))
    assert row
    return row


def join_room(db: Connection, user: dict, code: str) -> dict:
    row = db.fetchone("SELECT * FROM rooms WHERE code = ?", (code.strip().upper(),))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No room with this code")
    if not db.fetchone("SELECT 1 FROM room_members WHERE room_id = ? AND user_id = ?", (row["id"], user["id"])):
        db.execute("INSERT INTO room_members (room_id, user_id, joined_at) VALUES (?, ?, ?)", (row["id"], user["id"], now_iso()))
    return row


def _post_moderator(db: Connection, room_id: str, content: str, meta: dict | None = None) -> dict:
    mid = new_id()
    now = now_iso()
    db.execute(
        "INSERT INTO room_messages (id, room_id, user_id, display_name, role, content, meta_json, created_at) VALUES (?, ?, NULL, ?, 'moderator', ?, ?, ?)",
        (mid, room_id, MODERATOR_NAME, content, dumps(meta or {}), now),
    )
    return {"id": mid, "room_id": room_id, "user_id": None, "display_name": MODERATOR_NAME, "role": "moderator", "content": content, "created_at": now, "meta": meta or {}}


def _recent(db: Connection, room_id: str, limit: int = 12) -> list[dict]:
    rows = db.fetchall("SELECT display_name, role, content FROM room_messages WHERE room_id = ? ORDER BY created_at DESC LIMIT ?", (room_id, limit))
    rows.reverse()
    return [{"display_name": r["display_name"], "role": r["role"], "content": truncate(r["content"], 400)} for r in rows]


def post_message(db: Connection, router: ModelRouter, user: dict, room: dict, content: str) -> dict:
    mid = new_id()
    now = now_iso()
    db.execute(
        "INSERT INTO room_messages (id, room_id, user_id, display_name, role, content, meta_json, created_at) VALUES (?, ?, ?, ?, 'member', ?, '{}', ?)",
        (mid, room["id"], user["id"], user["display_name"], content, now),
    )
    db.execute("UPDATE rooms SET message_count = message_count + 1 WHERE id = ?", (room["id"],))
    record_event(db, user["id"], "room_message", {"room_id": room["id"]})
    message = {"id": mid, "room_id": room["id"], "user_id": user["id"], "display_name": user["display_name"], "role": "member", "content": content, "created_at": now, "meta": {}}

    moderator_message = None
    lowered = content.lower()
    if "@ednova" in lowered:
        moderator_message = _answer_group_question(db, router, user, room, content.replace("@ednova", "").replace("@EdNova", "").strip() or content)
    else:
        fresh = db.fetchone("SELECT message_count, last_moderated_at_count FROM rooms WHERE id = ?", (room["id"],)) or {}
        count = int(fresh.get("message_count") or 0)
        since = count - int(fresh.get("last_moderated_at_count") or 0)
        members = _members(db, room["id"])
        stats = participation(members)
        if since >= settings.room_moderator_every_n_messages and (stats["balance_score"] < 0.75 or stats["quiet_members"]):
            moderator_message = moderate(db, router, user, room, "nudge", None)["moderator_message"]
    return {"message": message, "moderator_message": moderator_message}


def _answer_group_question(db: Connection, router: ModelRouter, user: dict, room: dict, question: str) -> dict:
    recent = _recent(db, room["id"])
    out = router.run(
        "tutor_answer",
        {
            "message": question,
            "language": room["language"],
            "darija_script": user.get("darija_script", "arabic"),
            "learning_style": "examples",
            "level": "intermediate",
            "mode": "direct",
            "hint_level": 0,
            "intent": "explain",
            "complexity": "high" if len(question) > 160 else "low",
            "confusion": "none",
            "topic": room["topic"],
            "sources": [],
            "source_ids": "",
            "history": [{"role": "user", "content": f"{m['display_name']}: {m['content']}"} for m in recent[-6:]],
            "history_digest": "",
        },
        user_id=user["id"],
        db=db,
    )
    data = out.data if isinstance(out.data, dict) else {}
    text = data.get("answer_md") or data.get("_raw") or ""
    if data.get("guiding_question"):
        text += f"\n\n❓ {data['guiding_question']}"
    db.execute("UPDATE rooms SET last_moderated_at_count = message_count WHERE id = ?", (room["id"],))
    return _post_moderator(db, room["id"], text, {"kind": "answer", "ai": out.ai})


def moderate(db: Connection, router: ModelRouter, user: dict, room: dict, action: str, message_id: str | None) -> dict:
    members = _members(db, room["id"])
    stats = participation(members)
    recent = _recent(db, room["id"])
    common = {"topic": room["topic"], "language": room["language"], "darija_script": user.get("darija_script", "arabic"), "recent_messages": recent}
    if action == "nudge":
        out = router.run("room_nudge", {**common, "participation": {k: v for k, v in stats.items() if k != "per_member"}}, user_id=user["id"], db=db)
        text = (out.data or {}).get("message") or (out.data or {}).get("_raw") or ""
        kind = "nudge"
    elif action == "guiding_question":
        out = router.run("room_guiding_question", common, user_id=user["id"], db=db)
        text = (out.data or {}).get("message") or (out.data or {}).get("_raw") or ""
        kind = "guiding_question"
    elif action == "check_explanation":
        target = db.fetchone("SELECT * FROM room_messages WHERE id = ? AND room_id = ?", (message_id, room["id"])) if message_id else None
        if not target:
            target = db.fetchone("SELECT * FROM room_messages WHERE room_id = ? AND role = 'member' ORDER BY created_at DESC LIMIT 1", (room["id"],))
        if not target:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No explanation to check yet")
        out = router.run("room_check_explanation", {**common, "author": target["display_name"], "explanation": target["content"]}, user_id=user["id"], db=db)
        data = out.data or {}
        verdict = data.get("verdict") if data.get("verdict") in ("correct", "partially_correct", "incorrect", "unclear") else "unclear"
        text = data.get("message") or data.get("_raw") or ""
        text = f"**{verdict.replace('_', ' ').title()}** — {target['display_name']}: {text}"
        kind = "check_explanation"
    elif action == "summarize":
        rows = db.fetchall("SELECT display_name, role, content FROM room_messages WHERE room_id = ? AND role = 'member' ORDER BY created_at ASC LIMIT 80", (room["id"],))
        msgs = [{"display_name": r["display_name"], "content": truncate(r["content"], 500)} for r in rows]
        import hashlib

        digest = hashlib.sha256(dumps(msgs).encode()).hexdigest()[:16]
        out = router.run("room_summary", {**common, "messages": msgs, "messages_digest": digest}, user_id=user["id"], db=db)
        text = (out.data or {}).get("message") or (out.data or {}).get("_raw") or ""
        kind = "summary"
    else:  # pragma: no cover - validated by the schema
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown action")
    if not text:
        text = "…"
    db.execute("UPDATE rooms SET last_moderated_at_count = message_count WHERE id = ?", (room["id"],))
    moderator_message = _post_moderator(db, room["id"], text, {"kind": kind, "ai": out.ai, "participation": {k: v for k, v in stats.items() if k != "per_member"}})
    return {"moderator_message": moderator_message, "ai": out.ai}


def leaderboard(db: Connection, room: dict) -> list[dict]:
    if not room.get("quiz_id"):
        return []
    rows = db.fetchall(
        "SELECT u.display_name, MAX(a.percent) AS percent, MAX(a.created_at) AS submitted_at FROM quiz_attempts a JOIN users u ON u.id = a.user_id "
        "WHERE a.quiz_id = ? GROUP BY u.display_name ORDER BY percent DESC, submitted_at ASC",
        (room["quiz_id"],),
    )
    return [{"display_name": r["display_name"], "percent": r["percent"], "submitted_at": r["submitted_at"]} for r in rows]
