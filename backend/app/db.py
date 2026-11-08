"""
Database access layer.

A deliberately thin DB-API wrapper that runs the same SQL on

* **PostgreSQL** (production, via `psycopg` 3) – `DATABASE_URL=postgresql://...`
* **SQLite** (local development & the automated test-suite) – `DATABASE_URL=sqlite:///./ednova.db`

Portability rules used throughout the schema and queries:
  - primary keys are UUID strings (TEXT), timestamps are ISO-8601 TEXT,
    JSON payloads are TEXT, booleans are INTEGER 0/1;
  - queries use `?` placeholders which are rewritten to `%s` for psycopg;
  - rows are returned as plain dicts.
"""
from __future__ import annotations

import sqlite3
import threading
import typing as t
from pathlib import Path

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'learner',
    preferred_language TEXT NOT NULL DEFAULT 'en',
    darija_script TEXT NOT NULL DEFAULT 'arabic',
    learning_style TEXT,
    secondary_style TEXT,
    level TEXT,
    style_scores_json TEXT,
    goal TEXT,
    diagnostic_completed INTEGER NOT NULL DEFAULT 0,
    xp INTEGER NOT NULL DEFAULT 0,
    streak_days INTEGER NOT NULL DEFAULT 0,
    last_active_date TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    language TEXT NOT NULL,
    document_id TEXT,
    hint_level INTEGER NOT NULL DEFAULT 0,
    last_question TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_conversations_user ON conversations(user_id);
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    meta_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_messages_conversation ON messages(conversation_id, created_at);
CREATE TABLE IF NOT EXISTS quizzes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    room_id TEXT,
    topic TEXT NOT NULL,
    language TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    source TEXT NOT NULL,
    document_id TEXT,
    questions_json TEXT NOT NULL,
    ai_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_quizzes_user ON quizzes(user_id);
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id TEXT PRIMARY KEY,
    quiz_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    results_json TEXT NOT NULL,
    score REAL NOT NULL,
    total INTEGER NOT NULL,
    percent REAL NOT NULL,
    time_spent_s INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX IF NOT EXISTS ix_attempts_user ON quiz_attempts(user_id);
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    topic TEXT NOT NULL,
    language TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    quiz_id TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    last_moderated_at_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS room_members (
    room_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    PRIMARY KEY (room_id, user_id)
);
CREATE TABLE IF NOT EXISTS room_messages (
    id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL,
    user_id TEXT,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    meta_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_room_messages ON room_messages(room_id, created_at);
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime TEXT NOT NULL,
    pages INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    chars INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'en',
    status TEXT NOT NULL DEFAULT 'ready',
    error TEXT,
    preview TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_documents_user ON documents(user_id);
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    page INTEGER NOT NULL DEFAULT 1,
    text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_chunks_document ON chunks(document_id, idx);
CREATE TABLE IF NOT EXISTS roadmaps (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    weeks INTEGER NOT NULL,
    hours_per_week INTEGER NOT NULL DEFAULT 5,
    language TEXT NOT NULL,
    document_id TEXT,
    milestones_json TEXT NOT NULL,
    ai_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    source_id TEXT,
    language TEXT NOT NULL,
    content_md TEXT NOT NULL,
    flashcards_json TEXT,
    ai_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_events_user ON events(user_id, created_at);
CREATE TABLE IF NOT EXISTS badges (
    user_id TEXT NOT NULL,
    badge_id TEXT NOT NULL,
    unlocked_at TEXT NOT NULL,
    PRIMARY KEY (user_id, badge_id)
);
CREATE TABLE IF NOT EXISTS ai_cache (
    cache_key TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    tier TEXT NOT NULL,
    response_json TEXT NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_calls (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    task TEXT NOT NULL,
    tier TEXT NOT NULL,
    model TEXT NOT NULL,
    cached INTEGER NOT NULL DEFAULT 0,
    fallback INTEGER NOT NULL DEFAULT 0,
    fallback_reason TEXT,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    ok INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ai_calls_user ON ai_calls(user_id, created_at);
CREATE TABLE IF NOT EXISTS classes (
    id TEXT PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    teacher_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS class_members (
    class_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    PRIMARY KEY (class_id, user_id)
);
"""


class Connection:
    """Dialect-agnostic connection wrapper returning dict rows."""

    def __init__(self, raw: t.Any, dialect: str):
        self.raw = raw
        self.dialect = dialect

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.dialect == "postgresql" else sql

    def execute(self, sql: str, params: t.Sequence[t.Any] = ()) -> t.Any:
        cur = self.raw.cursor()
        cur.execute(self._sql(sql), tuple(params))
        return cur

    def fetchone(self, sql: str, params: t.Sequence[t.Any] = ()) -> dict | None:
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self, sql: str, params: t.Sequence[t.Any] = ()) -> list[dict]:
        cur = self.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def scalar(self, sql: str, params: t.Sequence[t.Any] = ()) -> t.Any:
        row = self.fetchone(sql, params)
        if not row:
            return None
        return next(iter(row.values()))

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()


class Database:
    def __init__(self, url: str | None = None):
        self.url = url or settings.database_url
        self.dialect = "postgresql" if self.url.startswith(("postgres://", "postgresql://")) else "sqlite"
        self._lock = threading.Lock()
        self._schema_ready = False

    # ------------------------------------------------------------------ connect
    def connect(self) -> Connection:
        if self.dialect == "sqlite":
            path = self.url.replace("sqlite:///", "", 1)
            if path not in (":memory:", ""):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            raw = sqlite3.connect(path or ":memory:", check_same_thread=False, timeout=30, isolation_level="DEFERRED")
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA journal_mode=WAL")
            raw.execute("PRAGMA foreign_keys=ON")
            raw.execute("PRAGMA busy_timeout=30000")
            return Connection(raw, "sqlite")
        import psycopg  # imported lazily: only needed for PostgreSQL deployments
        from psycopg.rows import dict_row

        raw = psycopg.connect(self.url, row_factory=dict_row)
        return Connection(raw, "postgresql")

    def init_schema(self) -> None:
        with self._lock:
            if self._schema_ready:
                return
            conn = self.connect()
            try:
                for statement in [s.strip() for s in SCHEMA.split(";") if s.strip()]:
                    conn.execute(statement)
                conn.commit()
            finally:
                conn.close()
            self._schema_ready = True

    def reset_for_tests(self) -> None:
        """Drop everything (used by the test-suite on throw-away SQLite files)."""
        conn = self.connect()
        try:
            tables = [
                "users", "conversations", "messages", "quizzes", "quiz_attempts", "rooms", "room_members",
                "room_messages", "documents", "chunks", "roadmaps", "notes", "events", "badges", "ai_cache",
                "ai_calls", "classes", "class_members",
            ]
            for table in tables:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()
        finally:
            conn.close()
        self._schema_ready = False
        self.init_schema()


database = Database()


def get_db() -> t.Iterator[Connection]:
    """Request-scoped connection (FastAPI dependency with `yield`)."""
    database.init_schema()
    conn = database.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
