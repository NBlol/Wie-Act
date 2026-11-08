"""Events, XP and badges (gamified learning progress)."""
from __future__ import annotations

import typing as t

from app.db import Connection
from app.utils import dumps, new_id, now_iso

XP_RULES: dict[str, int] = {
    "diagnostic_completed": 30,
    "question_asked": 5,
    "answer_revealed": 2,
    "quiz_completed": 10,  # + score bonus
    "room_message": 2,
    "room_created": 10,
    "document_uploaded": 15,
    "roadmap_created": 15,
    "roadmap_step_done": 8,
    "note_generated": 10,
}

BADGES: list[dict[str, t.Any]] = [
    {"id": "diagnostic_done", "name_key": "badge.diagnostic_done", "rule": "complete the learning-style diagnostic"},
    {"id": "first_question", "name_key": "badge.first_question", "rule": "ask your first question to the tutor"},
    {"id": "curious_mind", "name_key": "badge.curious_mind", "rule": "ask 10 questions"},
    {"id": "first_quiz", "name_key": "badge.first_quiz", "rule": "complete your first quiz"},
    {"id": "quiz_master", "name_key": "badge.quiz_master", "rule": "complete 5 quizzes"},
    {"id": "perfect_score", "name_key": "badge.perfect_score", "rule": "score 100 % on a quiz"},
    {"id": "collaborator", "name_key": "badge.collaborator", "rule": "post 5 messages in study rooms"},
    {"id": "document_explorer", "name_key": "badge.document_explorer", "rule": "upload a document"},
    {"id": "roadmap_starter", "name_key": "badge.roadmap_starter", "rule": "create a roadmap"},
    {"id": "note_taker", "name_key": "badge.note_taker", "rule": "generate revision notes"},
    {"id": "streak_3", "name_key": "badge.streak_3", "rule": "study 3 days in a row"},
    {"id": "streak_7", "name_key": "badge.streak_7", "rule": "study 7 days in a row"},
]


def record_event(db: Connection, user_id: str, event_type: str, payload: dict | None = None, xp: int | None = None) -> dict:
    """Store an analytics event, award XP and evaluate badge rules. Returns {"xp_gained", "badges_unlocked"}."""
    db.execute(
        "INSERT INTO events (id, user_id, type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (new_id(), user_id, event_type, dumps(payload or {}), now_iso()),
    )
    gained = XP_RULES.get(event_type, 0) if xp is None else xp
    if gained:
        db.execute("UPDATE users SET xp = xp + ? WHERE id = ?", (gained, user_id))
    unlocked = evaluate_badges(db, user_id, event_type, payload or {})
    return {"xp_gained": gained, "badges_unlocked": unlocked}


def _count(db: Connection, user_id: str, event_type: str) -> int:
    return int(db.scalar("SELECT COUNT(*) FROM events WHERE user_id = ? AND type = ?", (user_id, event_type)) or 0)


def _has_badge(db: Connection, user_id: str, badge_id: str) -> bool:
    return db.fetchone("SELECT 1 FROM badges WHERE user_id = ? AND badge_id = ?", (user_id, badge_id)) is not None


def _unlock(db: Connection, user_id: str, badge_id: str, unlocked: list[str]) -> None:
    if _has_badge(db, user_id, badge_id):
        return
    db.execute("INSERT INTO badges (user_id, badge_id, unlocked_at) VALUES (?, ?, ?)", (user_id, badge_id, now_iso()))
    db.execute(
        "INSERT INTO events (id, user_id, type, payload_json, created_at) VALUES (?, ?, 'badge_unlocked', ?, ?)",
        (new_id(), user_id, dumps({"badge_id": badge_id}), now_iso()),
    )
    unlocked.append(badge_id)


def evaluate_badges(db: Connection, user_id: str, event_type: str, payload: dict) -> list[str]:
    unlocked: list[str] = []
    if event_type == "diagnostic_completed":
        _unlock(db, user_id, "diagnostic_done", unlocked)
    if event_type == "question_asked":
        n = _count(db, user_id, "question_asked")
        if n >= 1:
            _unlock(db, user_id, "first_question", unlocked)
        if n >= 10:
            _unlock(db, user_id, "curious_mind", unlocked)
    if event_type == "quiz_completed":
        _unlock(db, user_id, "first_quiz", unlocked)
        if _count(db, user_id, "quiz_completed") >= 5:
            _unlock(db, user_id, "quiz_master", unlocked)
        if float(payload.get("percent", 0)) >= 100:
            _unlock(db, user_id, "perfect_score", unlocked)
    if event_type == "room_message" and _count(db, user_id, "room_message") >= 5:
        _unlock(db, user_id, "collaborator", unlocked)
    if event_type == "document_uploaded":
        _unlock(db, user_id, "document_explorer", unlocked)
    if event_type == "roadmap_created":
        _unlock(db, user_id, "roadmap_starter", unlocked)
    if event_type == "note_generated":
        _unlock(db, user_id, "note_taker", unlocked)
    user = db.fetchone("SELECT streak_days FROM users WHERE id = ?", (user_id,))
    streak = int(user.get("streak_days") or 0) if user else 0
    if streak >= 3:
        _unlock(db, user_id, "streak_3", unlocked)
    if streak >= 7:
        _unlock(db, user_id, "streak_7", unlocked)
    return unlocked


def list_badges(db: Connection, user_id: str) -> list[dict]:
    rows = {r["badge_id"]: r["unlocked_at"] for r in db.fetchall("SELECT badge_id, unlocked_at FROM badges WHERE user_id = ?", (user_id,))}
    return [
        {**badge, "unlocked_at": rows.get(badge["id"]), "unlocked": badge["id"] in rows}
        for badge in BADGES
    ]
