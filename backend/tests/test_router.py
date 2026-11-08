"""Unit tests for the two-tier ModelRouter: tier selection, cache, retry, fallback, breaker, queue, offline."""
from __future__ import annotations

import threading

from app.ai import router as router_module
from app.ai.tasks import COMPACT, LARGE, TASKS
from app.utils import detect_language, extract_json


def _router():
    return router_module.router


def test_routing_table_tier_selection():
    assert TASKS["tutor_triage"].resolve_tier({}) == COMPACT
    assert TASKS["quiz_generate"].resolve_tier({}) == LARGE
    # dynamic tutor routing
    assert TASKS["tutor_answer"].resolve_tier({"complexity": "low", "hint_level": 0, "sources": []}) == COMPACT
    assert TASKS["tutor_answer"].resolve_tier({"complexity": "high", "hint_level": 0, "sources": []}) == LARGE
    assert TASKS["tutor_answer"].resolve_tier({"complexity": "low", "hint_level": 2, "sources": []}) == LARGE
    assert TASKS["tutor_answer"].resolve_tier({"complexity": "low", "hint_level": 0, "sources": [{}, {}, {}]}) == LARGE
    # dynamic RAG routing
    assert TASKS["rag_answer"].resolve_tier({"question": "What is X?", "sources": [{"score": 1.0}]}) == COMPACT
    assert TASKS["rag_answer"].resolve_tier({"question": "Compare A and B across the chapters", "sources": [{"score": 1.0}, {"score": 0.8}, {"score": 0.7}]}) == LARGE


def test_live_call_uses_expected_model_and_parses_json(fake_provider):
    out = _router().run("tutor_triage", {"message": "I don't understand this exercise", "preferred_language": "en"})
    assert out.ai["provider"] == "live" and out.ai["tier"] == COMPACT and out.ai["cached"] is False
    assert fake_provider.calls[-1]["model"] == _router().compact_model
    assert out.data["intent"] == "exercise_help" and out.data["confusion"] == "mild"

    out = _router().run("quiz_generate", {"topic": "Cells", "num_questions": 4, "difficulty": "beginner", "language": "en", "question_types": ["mcq"], "sources": [], "source_ids": ""})
    assert out.ai["tier"] == LARGE and fake_provider.calls[-1]["model"] == _router().large_model
    assert len(out.data["questions"]) == 4


def test_cache_prevents_regenerating_equivalent_requests(fake_provider):
    inputs = {"topic": "Photosynthesis", "num_questions": 3, "difficulty": "beginner", "language": "en", "question_types": ["mcq"], "sources": [], "source_ids": ""}
    first = _router().run("quiz_generate", inputs)
    n_calls = len(fake_provider.calls)
    # same request with different whitespace / case must hit the cache
    second = _router().run("quiz_generate", {**inputs, "topic": "  photosynthesis "})
    assert second.ai["cached"] is True
    assert len(fake_provider.calls) == n_calls
    assert second.data == first.data


def test_retry_then_success_on_transient_error(fake_provider):
    fake_provider.fail_once.add(_router().compact_model)
    out = _router().run("tutor_triage", {"message": "hello there", "preferred_language": "en"})
    assert out.ai["provider"] == "live" and out.ai["fallback"] is False
    assert len(fake_provider.calls) == 2  # one failure + one retry


def test_large_unavailable_falls_back_to_compact_with_notice(fake_provider):
    fake_provider.fail_models[_router().large_model] = 503
    out = _router().run("notes_generate", {"source": "topic", "topic": "Vectors", "material": "Vectors have magnitude and direction.", "format": "both", "language": "fr", "material_digest": "x"})
    assert out.ai["tier"] == COMPACT and out.ai["fallback"] is True
    assert out.ai["fallback_reason"] in ("large_unavailable", "rate_limited")
    assert out.ai["intended_tier"] == LARGE
    assert "modèle compact" in out.ai["notice"]  # notice in the learner's language
    assert out.data["content_md"]


def test_rate_limit_reason_is_reported(fake_provider):
    fake_provider.fail_models[_router().large_model] = 429
    out = _router().run("roadmap_generate", {"goal": "Pass algebra", "weeks": 2, "hours_per_week": 3, "language": "en", "learning_style": "visual", "level": "beginner", "sources": [], "source_ids": "", "material_digest": "r"})
    assert out.ai["fallback_reason"] == "rate_limited" and out.ai["tier"] == COMPACT


def test_circuit_breaker_opens_after_repeated_large_failures(fake_provider):
    r = _router()
    fake_provider.fail_models[r.large_model] = 503
    r.run("room_summary", {"messages": [], "messages_digest": "a", "topic": "T", "language": "en"})
    r.run("room_summary", {"messages": [], "messages_digest": "b", "topic": "T", "language": "en"})
    assert r.breaker_large.is_open is True
    status = r.status()
    assert status["large_available"] is False and status["large_breaker_open_until"]
    calls_before = len(fake_provider.calls)
    out = r.run("room_summary", {"messages": [], "messages_digest": "c", "topic": "T", "language": "en"})
    # breaker open → straight to compact without even trying the large model
    assert out.ai["tier"] == COMPACT and out.ai["fallback_reason"] == "large_unavailable"
    assert all(c["model"] == r.compact_model for c in fake_provider.calls[calls_before:])


def test_queue_full_falls_back_instead_of_blocking(fake_provider):
    r = _router()
    fake_provider.delay = 0.6  # longer than AI_LARGE_QUEUE_WAIT_S (0.2 s in tests)
    results: list = []

    def worker(i: int) -> None:
        results.append(r.run("quiz_generate", {"topic": f"Topic {i}", "num_questions": 3, "difficulty": "beginner", "language": "en", "question_types": ["mcq"], "sources": [], "source_ids": ""}))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(r.queue_large.capacity + 2)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    tiers = [o.ai["tier"] for o in results]
    assert tiers.count(LARGE) == r.queue_large.capacity
    assert tiers.count(COMPACT) == 2
    assert all(o.ai["fallback_reason"] == "queue_full" for o in results if o.ai["tier"] == COMPACT)


def test_all_tiers_down_degrades_to_offline_generators(fake_provider):
    r = _router()
    fake_provider.fail_models[r.large_model] = 503
    fake_provider.fail_models[r.compact_model] = 503
    out = r.run("rag_answer", {"question": "What is osmosis?", "language": "en", "sources": [{"chunk_id": "c1", "page": 1, "score": 1.0, "excerpt": "Osmosis is the movement of water across a membrane. It matters for cells."}], "source_ids": "c1"})
    assert out.ai["provider"] == "offline" and out.ai["fallback"] is True
    assert "not reachable" in out.ai["notice"]
    assert "Osmosis" in out.data["answer_md"]
    assert r.stats.errors >= 1


def test_offline_mode_without_api_key(offline_router):
    out = _router().run("tutor_triage", {"message": "شنوّة هي المشتقة؟ ما فهمتش", "preferred_language": "en"})
    assert out.ai["provider"] == "offline" and out.ai["fallback_reason"] == "no_api_key"
    assert out.data["language"] == "tn" and out.data["confusion"] in ("mild", "high")


def test_unparseable_model_output_is_kept_as_raw(fake_provider):
    fake_provider.raw_override = "Sorry, here is prose instead of JSON."
    out = _router().run("tutor_triage", {"message": "hi", "preferred_language": "en"})
    assert out.data == {"_raw": "Sorry, here is prose instead of JSON."}


def test_helpers_language_detection_and_json_extraction():
    assert detect_language("Bonjour, je ne comprends pas cet exercice") == "fr"
    assert detect_language("ما هي الخلية؟") == "ar"
    assert detect_language("kifech na7seb el moyenne? barcha s3iba") == "tn"
    assert detect_language("What is a derivative?") == "en"
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Here you go: {"a": [1, 2]} thanks') == {"a": [1, 2]}
    assert extract_json("no json") is None
