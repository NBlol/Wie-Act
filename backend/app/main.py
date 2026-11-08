"""EdNova AI – application entry point."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from app.api import analytics, auth, classes, diagnostic, documents, notes, quizzes, roadmaps, rooms, system, tutor
from app.compat import USING_FASTAPI, CORSMiddleware, FastAPI, StaticFiles
from app.config import settings
from app.db import database

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
for noisy in ("httpx", "httpx2", "httpcore", "httpcore2"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
log = logging.getLogger("ednova")


@asynccontextmanager
async def lifespan(app):  # type: ignore[no-untyped-def]
    database.init_schema()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    log.info(
        "EdNova AI %s starting (framework=%s, db=%s, ai=%s, compact=%s, large=%s)",
        settings.version,
        "fastapi" if USING_FASTAPI else "starlette-compat",
        settings.db_dialect,
        "live" if settings.ai_live else "OFFLINE (no AI_API_KEY)",
        settings.ai_compact_model,
        settings.ai_large_model,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (system.router, auth.router, diagnostic.router, tutor.router, quizzes.router, rooms.router, documents.router, roadmaps.router, notes.router, analytics.router, classes.router):
        app.include_router(r, prefix="/api")

    # Optionally serve the built frontend from the same process (single-container deployments)
    frontend_dir = settings.serve_frontend_dir
    if frontend_dir and os.path.isdir(frontend_dir):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    return app


app = create_app()
