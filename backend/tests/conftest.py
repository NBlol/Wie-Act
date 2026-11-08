"""Shared fixtures: isolated SQLite database per test session, API client, fake inference provider."""
from __future__ import annotations

import json
import os
import re
import tempfile
import typing as t
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="ednova-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["AI_LARGE_QUEUE_WAIT_S"] = "0.2"
os.environ["AI_MAX_RETRIES"] = "1"
os.environ["AI_BREAKER_FAILURES"] = "2"
os.environ["AI_BREAKER_WINDOW_S"] = "60"
os.environ["AI_BREAKER_OPEN_S"] = "60"
os.environ.pop("AI_API_KEY", None)
os.environ.pop("AI_BASE_URL", None)

from starlette.testclient import TestClient  # noqa: E402

from app.ai import router as router_module  # noqa: E402
from app.ai.provider import LLMResult, ProviderError  # noqa: E402
from app.db import database  # noqa: E402
from app.main import app  # noqa: E402


class FakeProvider:
    """Deterministic stand-in for the inference platform.

    * answers each prompt with well-formed JSON for the task recognised from the system prompt;
    * `fail_models` makes a model raise `ProviderError` (retryable, optional status) – used to
      exercise retries, fallback and the circuit breaker;
    * `fail_once` makes the first call of a model fail, then succeed (retry path);
    * `delay` sleeps to exercise the concurrency queue.
    """

    name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.fail_models: dict[str, int | None] = {}
        self.fail_once: set[str] = set()
        self.delay: float = 0.0
        self.raw_override: str | None = None

    def complete(self, *, model: str, messages: list[dict[str, str]], max_tokens: int, temperature: float, json_mode: bool) -> LLMResult:
        self.calls.append({"model": model, "messages": messages, "max_tokens": max_tokens})
        if model in self.fail_once:
            self.fail_once.discard(model)
            raise ProviderError("transient", status=503, retryable=True)
        if model in self.fail_models:
            raise ProviderError("unavailable", status=self.fail_models[model], retryable=True)
        if self.delay:
            import time

            time.sleep(self.delay)
        text = self.raw_override if self.raw_override is not None else fake_text_for(messages)
        return LLMResult(text=text, model=model, latency_ms=12)


def fake_text_for(messages: list[dict[str, str]]) -> str:
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    user = " ".join(m["content"] for m in messages if m["role"] == "user")
    if "fast classifier" in system:
        lang = "fr" if re.search(r"[éèàç]|comprends|pourquoi", user) else "en"
        return json.dumps({"language": lang, "intent": "exercise_help" if "exercice" in user.lower() or "exercise" in user.lower() else "explain", "confusion": "mild" if "comprends pas" in user.lower() or "understand" in user.lower() else "none", "complexity": "high" if "prove" in user.lower() or "démontr" in user.lower() else "low", "topic": "test topic"})
    if "peer-learning tutor" in system:
        return json.dumps({"answer_md": "**Fake tutor answer** based on your question. [1]", "guiding_question": "What would you try first?", "next_step": "Take a 3-question quiz.", "confusion_detected": "none"})
    if "writing a" in system and "quiz" in system:
        m = re.search(r"exactly (\d+) questions", system)
        n = int(m.group(1)) if m else 5
        qs = []
        for i in range(n):
            if "short" in system and i % 3 == 2:
                qs.append({"type": "short", "text": f"Short question {i + 1}?", "expected_answer": "chlorophyll absorbs light energy", "explanation": "Because.", "skill": f"Skill {i % 2}"})
            else:
                qs.append({"type": "mcq", "text": f"Question {i + 1}?", "options": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong 1"}, {"id": "c", "text": "Wrong 2"}, {"id": "d", "text": "Wrong 3"}], "correct_option_id": "a", "explanation": "A is right.", "skill": f"Skill {i % 2}"})
        return json.dumps({"questions": qs})
    if "grade learners" in system:
        items = json.loads(user).get("items", [])
        return json.dumps({"grades": [{"score": 1 if "chlorophyll" in it["learner_answer"].lower() else 0, "feedback": "Fake grading feedback."} for it in items]})
    if "feedback after a quiz" in system:
        return json.dumps({"feedback": "Fake personalised feedback."})
    if "EQUAL participation" in system:
        return json.dumps({"message": "Fake nudge: Lina, what do you think?"})
    if "ONE guiding question" in system:
        return json.dumps({"message": "Fake guiding question?"})
    if "verify the explanation" in system:
        return json.dumps({"verdict": "partially_correct", "message": "Fake verification."})
    if "session summary" in system:
        return json.dumps({"message": "## Fake summary"})
    if "ONLY the numbered document passages" in system:
        return json.dumps({"answer_md": "Fake RAG answer [1].", "used_sources": [1]})
    if "learning coach" in system:
        m = re.search(r"(\d+)-week", system)
        weeks = int(m.group(1)) if m else 4
        return json.dumps({"milestones": [{"week": w, "title": f"Week {w}", "objective": "Obj", "activities": [{"text": "Read", "kind": "read"}, {"text": "Practice", "kind": "practice"}], "checkpoint": "Can you explain it?"} for w in range(1, weeks + 1)]})
    if "revision notes" in system:
        return json.dumps({"title": "Fake notes", "content_md": "# Fake notes\n- point", "flashcards": [{"q": "Q?", "a": "A."}]})
    if "learning-profile summary" in system:
        return json.dumps({"explanation": "Fake explanation.", "recommendations": ["Tip 1", "Tip 2", "Tip 3"]})
    return json.dumps({"text": "fake"})


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    database.reset_for_tests()


@pytest.fixture()
def client() -> t.Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


_counter = {"n": 0}


def register(client: TestClient, role: str = "learner", language: str = "en", name: str | None = None) -> tuple[dict, dict]:
    _counter["n"] += 1
    email = f"user{_counter['n']}@example.test"
    r = client.post("/api/auth/register", json={"email": email, "password": "Passw0rd!xyz", "display_name": name or f"Learner{_counter['n']}", "preferred_language": language, "role": role})
    assert r.status_code == 201, r.text
    data = r.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]


@pytest.fixture()
def auth(client: TestClient) -> tuple[dict, dict]:
    return register(client)


@pytest.fixture()
def fake_provider() -> t.Iterator[FakeProvider]:
    """Switch the global router to LIVE mode with the fake provider for the duration of a test."""
    r = router_module.router
    original = r.provider
    fake = FakeProvider()
    r.provider = fake
    r.clear_cache()
    r.breaker_large.record_success()
    r.breaker_compact.record_success()
    try:
        yield fake
    finally:
        r.provider = original
        r.clear_cache()
        r.breaker_large.record_success()
        r.breaker_compact.record_success()


@pytest.fixture()
def offline_router() -> t.Iterator[None]:
    r = router_module.router
    original = r.provider
    r.provider = None
    try:
        yield
    finally:
        r.provider = original
