from __future__ import annotations

from app.compat import APIRouter, Depends
from app.db import Connection
from app.deps import get_current_user, get_db
from app.services import analytics
from app.utils import loads

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def get_overview(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    fresh = db.fetchone("SELECT * FROM users WHERE id = ?", (user["id"],)) or user
    return analytics.overview(db, fresh)


@router.get("/events")
def get_events(limit: int = 50, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    limit = max(1, min(limit, 500))
    rows = db.fetchall("SELECT id, type, payload_json, created_at FROM events WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user["id"], limit))
    return [{"id": r["id"], "type": r["type"], "created_at": r["created_at"], "payload": loads(r["payload_json"], {})} for r in rows]
