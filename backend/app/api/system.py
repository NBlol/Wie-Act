from __future__ import annotations

from app.ai.router import get_router
from app.ai.tasks import routing_table
from app.compat import USING_FASTAPI, APIRouter
from app.config import settings

router = APIRouter(tags=["system"])

TUTOR_STAGES = [
    {"key": "triage", "label_key": "stage.triage", "typical_ms": 1500, "tier": "compact"},
    {"key": "retrieve", "label_key": "stage.retrieve", "typical_ms": 400, "tier": "none"},
    {"key": "reason", "label_key": "stage.reason", "typical_ms": 7000, "tier": "compact|large"},
    {"key": "format", "label_key": "stage.format", "typical_ms": 500, "tier": "none"},
]


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": settings.version,
        "db": settings.db_dialect,
        "framework": "fastapi" if USING_FASTAPI else "starlette-compat",
        "ai_mode": "live" if get_router().live else "offline",
    }


@router.get("/system/status")
def system_status() -> dict:
    return get_router().status()


@router.get("/system/routing")
def system_routing() -> dict:
    return {"tasks": routing_table()}


@router.get("/tutor/stages")
def tutor_stages() -> dict:
    return {"stages": TUTOR_STAGES}
