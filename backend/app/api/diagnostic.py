from __future__ import annotations

from app.ai.router import get_router
from app.compat import APIRouter, Depends
from app.db import Connection
from app.deps import get_current_user, get_db
from app.schemas import DiagnosticSubmit
from app.services import diagnostic
from app.services.gamification import record_event
from app.services.users import serialize_user
from app.utils import dumps

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.get("/questions")
def get_questions(language: str = "en") -> dict:
    return {"questions": diagnostic.questions(language)}


@router.post("/submit")
def submit(body: DiagnosticSubmit, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    profile = diagnostic.score([a.model_dump() for a in body.answers], body.self_reported_level)
    language = body.language or user.get("preferred_language", "en")
    db.execute(
        "UPDATE users SET learning_style = ?, secondary_style = ?, level = ?, style_scores_json = ?, goal = COALESCE(?, goal), diagnostic_completed = 1 WHERE id = ?",
        (profile["learning_style"], profile["secondary_style"], profile["level"], dumps(profile["style_scores"]), body.goal, user["id"]),
    )
    first_time = not bool(user.get("diagnostic_completed"))
    rewards = record_event(db, user["id"], "diagnostic_completed", {"profile": profile}) if first_time else {"xp_gained": 0, "badges_unlocked": []}
    out = get_router().run(
        "diagnostic_summary",
        {**profile, "goal": body.goal, "language": language, "darija_script": user.get("darija_script", "arabic")},
        user_id=user["id"],
        db=db,
    )
    data = out.data if isinstance(out.data, dict) else {}
    fresh = db.fetchone("SELECT * FROM users WHERE id = ?", (user["id"],))
    assert fresh
    return {
        "profile": profile,
        "explanation": data.get("explanation") or data.get("_raw") or "",
        "recommendations": data.get("recommendations") or [],
        "ai": out.ai,
        "user": serialize_user(fresh),
        **rewards,
    }
