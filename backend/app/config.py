"""Application settings, loaded from environment variables (see `.env.example`)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:  # python-dotenv is optional
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:  # pragma: no cover
    pass


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass
class Settings:
    app_name: str = "EdNova AI"
    version: str = "1.0.0"
    environment: str = os.getenv("APP_ENV", "development")
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production-this-is-not-a-secret")
    access_token_minutes: int = _int("ACCESS_TOKEN_MINUTES", 60 * 24)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./ednova.db")
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
    )
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_upload_mb: int = _int("MAX_UPLOAD_MB", 15)
    serve_frontend_dir: str = os.getenv("SERVE_FRONTEND_DIR", "")

    # --- AI inference platform (two model categories) -----------------------
    ai_base_url: str = os.getenv("AI_BASE_URL", "")  # e.g. https://<platform>/v1
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_api_style: str = os.getenv("AI_API_STYLE", "openai")  # openai | anthropic
    ai_compact_model: str = os.getenv("AI_COMPACT_MODEL", "compact-model")
    ai_large_model: str = os.getenv("AI_LARGE_MODEL", "large-model")
    ai_timeout_s: float = _float("AI_TIMEOUT_S", 90.0)
    ai_max_retries: int = _int("AI_MAX_RETRIES", 2)
    ai_large_concurrency: int = _int("AI_LARGE_CONCURRENCY", 2)
    ai_large_queue_wait_s: float = _float("AI_LARGE_QUEUE_WAIT_S", 20.0)
    ai_breaker_failures: int = _int("AI_BREAKER_FAILURES", 3)
    ai_breaker_window_s: int = _int("AI_BREAKER_WINDOW_S", 120)
    ai_breaker_open_s: int = _int("AI_BREAKER_OPEN_S", 90)
    ai_cache_ttl_s: int = _int("AI_CACHE_TTL_S", 24 * 3600)
    ai_json_mode: bool = _bool("AI_JSON_MODE", False)
    ai_force_offline: bool = _bool("AI_FORCE_OFFLINE", False)
    ai_log_prompts: bool = _bool("AI_LOG_PROMPTS", False)

    # --- Collaborative rooms --------------------------------------------------
    room_moderator_every_n_messages: int = _int("ROOM_MODERATOR_EVERY_N", 6)

    @property
    def ai_live(self) -> bool:
        return bool(self.ai_base_url and self.ai_api_key) and not self.ai_force_offline

    @property
    def db_dialect(self) -> str:
        return "postgresql" if self.database_url.startswith(("postgres://", "postgresql://")) else "sqlite"


settings = Settings()
