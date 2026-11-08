from __future__ import annotations

import typing as t

from app.ai import offline
from app.ai.router import get_router
from app.compat import APIRouter, Depends, HTTPException, status
from app.db import Connection
from app.deps import get_current_user, get_db
from app.rag import index as rag_index
from app.schemas import ActivityUpdate, RoadmapCreate
from app.services.gamification import record_event
from app.utils import SUPPORTED_LANGUAGES, dumps, loads, new_id, now_iso, truncate

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

_KINDS = ("read", "practice", "quiz", "discuss", "watch", "recall")


def _clean_milestones(raw: t.Any, weeks: int) -> list[dict]:
    items = raw.get("milestones") if isinstance(raw, dict) else None
    out: list[dict] = []
    if not isinstance(items, list):
        return out
    for i, m in enumerate(items[:weeks], 1):
        if not isinstance(m, dict):
            continue
        activities = []
        for a in (m.get("activities") or [])[:6]:
            if isinstance(a, dict) and a.get("text"):
                activities.append({"id": new_id(), "text": truncate(str(a["text"]), 200), "kind": a.get("kind") if a.get("kind") in _KINDS else "practice", "done": False})
            elif isinstance(a, str) and a.strip():
                activities.append({"id": new_id(), "text": truncate(a, 200), "kind": "practice", "done": False})
        if not activities:
            continue
        out.append(
            {
                "id": new_id(),
                "week": int(m.get("week") or i),
                "title": truncate(str(m.get("title") or f"Week {i}"), 120),
                "objective": truncate(str(m.get("objective") or ""), 300),
                "activities": activities,
                "checkpoint": truncate(str(m.get("checkpoint") or ""), 300),
            }
        )
    return out


def serialize(row: dict, ai: dict | None = None) -> dict:
    milestones = loads(row["milestones_json"], [])
    total = sum(len(m["activities"]) for m in milestones)
    done = sum(1 for m in milestones for a in m["activities"] if a.get("done"))
    return {
        "id": row["id"], "goal": row["goal"], "weeks": int(row["weeks"]), "hours_per_week": int(row.get("hours_per_week") or 5), "language": row["language"],
        "document_id": row.get("document_id"), "created_at": row["created_at"],
        "progress_percent": round(100 * done / total) if total else 0, "milestones": milestones,
        "ai": ai if ai is not None else loads(row.get("ai_json"), None),
    }


def _owned(db: Connection, user_id: str, roadmap_id: str) -> dict:
    row = db.fetchone("SELECT * FROM roadmaps WHERE id = ? AND user_id = ?", (roadmap_id, user_id))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Roadmap not found")
    return row


@router.post("", status_code=201)
def create_roadmap(body: RoadmapCreate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    language = body.language if body.language in SUPPORTED_LANGUAGES else user.get("preferred_language", "en")
    sources: list[dict] = []
    if body.document_id:
        if not db.fetchone("SELECT id FROM documents WHERE id = ? AND user_id = ?", (body.document_id, user["id"])):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
        sources = rag_index.sample_chunks(db, body.document_id, limit=6, excerpt_chars=700)
    inputs = {
        "goal": body.goal, "weeks": body.weeks, "hours_per_week": body.hours_per_week, "language": language,
        "darija_script": user.get("darija_script", "arabic"), "learning_style": user.get("learning_style") or "step_by_step",
        "level": user.get("level") or "beginner", "sources": sources, "source_ids": rag_index.source_ids(sources),
    }
    out = get_router().run("roadmap_generate", inputs, user_id=user["id"], db=db)
    milestones = _clean_milestones(out.data, body.weeks)
    if not milestones:
        milestones = _clean_milestones(offline.roadmap_generate(inputs), body.weeks)
        out.ai = {**out.ai, "fallback": True, "fallback_reason": out.ai.get("fallback_reason") or "unparseable_output", "notice": out.ai.get("notice") or offline.NOTICE.get(language, offline.NOTICE["en"])}
    rid = new_id()
    db.execute(
        "INSERT INTO roadmaps (id, user_id, goal, weeks, hours_per_week, language, document_id, milestones_json, ai_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (rid, user["id"], body.goal.strip(), body.weeks, body.hours_per_week, language, body.document_id, dumps(milestones), dumps(out.ai), now_iso()),
    )
    rewards = record_event(db, user["id"], "roadmap_created", {"roadmap_id": rid, "goal": body.goal})
    row = db.fetchone("SELECT * FROM roadmaps WHERE id = ?", (rid,))
    assert row
    return {**serialize(row, out.ai), **rewards}


@router.get("")
def list_roadmaps(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    rows = db.fetchall("SELECT * FROM roadmaps WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))
    return [serialize(r) for r in rows]


@router.get("/{roadmap_id}")
def get_roadmap(roadmap_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    return serialize(_owned(db, user["id"], roadmap_id))


@router.patch("/{roadmap_id}/activities/{activity_id}")
def update_activity(roadmap_id: str, activity_id: str, body: ActivityUpdate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = _owned(db, user["id"], roadmap_id)
    milestones = loads(row["milestones_json"], [])
    found = False
    changed_to_done = False
    for m in milestones:
        for a in m["activities"]:
            if a["id"] == activity_id:
                changed_to_done = body.done and not a.get("done")
                a["done"] = body.done
                found = True
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activity not found")
    db.execute("UPDATE roadmaps SET milestones_json = ? WHERE id = ?", (dumps(milestones), roadmap_id))
    rewards = {"xp_gained": 0, "badges_unlocked": []}
    if changed_to_done:
        rewards = record_event(db, user["id"], "roadmap_step_done", {"roadmap_id": roadmap_id, "activity_id": activity_id})
    fresh = db.fetchone("SELECT * FROM roadmaps WHERE id = ?", (roadmap_id,))
    assert fresh
    return {**serialize(fresh), **rewards}
