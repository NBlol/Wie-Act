"""User serialisation, XP/levels and daily streak maintenance."""
from __future__ import annotations

from datetime import date, timedelta

from app.db import Connection
from app.utils import loads, today_str

XP_PER_LEVEL = 100


def level_from_xp(xp: int) -> tuple[int, int]:
    """Return (level_number, progress_percent) for a simple linear curve."""
    level = xp // XP_PER_LEVEL + 1
    progress = int((xp % XP_PER_LEVEL) / XP_PER_LEVEL * 100)
    return level, progress


def serialize_user(user: dict) -> dict:
    level, progress = level_from_xp(int(user.get("xp") or 0))
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "role": user.get("role", "learner"),
        "preferred_language": user.get("preferred_language", "en"),
        "darija_script": user.get("darija_script", "arabic"),
        "learning_style": user.get("learning_style"),
        "secondary_style": user.get("secondary_style"),
        "level": user.get("level"),
        "goal": user.get("goal"),
        "style_scores": loads(user.get("style_scores_json"), {}),
        "diagnostic_completed": bool(user.get("diagnostic_completed")),
        "xp": int(user.get("xp") or 0),
        "level_number": level,
        "level_progress_percent": progress,
        "streak_days": int(user.get("streak_days") or 0),
        "created_at": user.get("created_at"),
    }


def touch_activity(db: Connection, user: dict) -> None:
    """Maintain the daily streak counter on any authenticated request."""
    today = today_str()
    last = user.get("last_active_date")
    if last == today:
        return
    streak = int(user.get("streak_days") or 0)
    if last:
        try:
            yesterday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
            streak = streak + 1 if last == yesterday else 1
        except ValueError:
            streak = 1
    else:
        streak = 1
    db.execute("UPDATE users SET last_active_date = ?, streak_days = ? WHERE id = ?", (today, streak, user["id"]))
    user["last_active_date"] = today
    user["streak_days"] = streak
