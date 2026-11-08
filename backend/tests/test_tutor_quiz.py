from __future__ import annotations


def _conversation(client, headers, language="en"):
    r = client.post("/api/tutor/conversations", headers=headers, json={"language": language})
    assert r.status_code == 201
    return r.json()["id"]


def test_diagnostic_questions_and_profile(client, auth, fake_provider):
    headers, _ = auth
    for lang in ("en", "fr", "ar", "tn"):
        r = client.get(f"/api/diagnostic/questions?language={lang}")
        assert r.status_code == 200 and len(r.json()["questions"]) == 9
    answers = [{"question_id": f"p{i}", "option_id": "d"} for i in range(1, 7)]  # all "examples"
    answers += [{"question_id": "e1", "option_id": "b"}, {"question_id": "e2", "option_id": "b"}, {"question_id": "e3", "option_id": "c"}]
    r = client.post("/api/diagnostic/submit", headers=headers, json={"answers": answers, "self_reported_level": "intermediate", "goal": "Pass biology"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["profile"]["learning_style"] == "examples" and body["profile"]["exercise_score"] == 3
    assert body["profile"]["level"] == "advanced"
    assert body["user"]["diagnostic_completed"] is True and body["xp_gained"] > 0
    assert "diagnostic_done" in body["badges_unlocked"]
    assert body["explanation"] == "Fake explanation." and body["ai"]["tier"] == "compact"


def test_tutor_hint_first_flow_and_reveal(client, auth, fake_provider):
    headers, _ = auth
    cid = _conversation(client, headers, "fr")
    r = client.post(f"/api/tutor/conversations/{cid}/messages", headers=headers, json={"content": "Je ne comprends pas cet exercice : résoudre 2x + 3 = 11", "mode": "guided"})
    assert r.status_code == 200, r.text
    body = r.json()
    msg = body["assistant_message"]
    assert msg["meta"]["hint_level"] == 0 and msg["meta"]["triage"]["intent"] == "exercise_help"
    assert msg["meta"]["triage"]["language"] == "fr" and msg["meta"]["confusion_detected"] == "mild"
    assert msg["meta"]["guiding_question"] and msg["meta"]["next_step"]
    assert body["stages"] == ["triage", "retrieve", "reason", "format"]
    assert body["xp_gained"] == 5
    # low complexity + no sources → compact model answered
    assert msg["meta"]["ai"]["tier"] == "compact"
    models = [c["model"] for c in fake_provider.calls]
    assert models.count("large-model") == 0 if fake_provider.calls else True

    # second attempt on the same exercise → hint level 1
    r = client.post(f"/api/tutor/conversations/{cid}/messages", headers=headers, json={"content": "Toujours pas, aide moi encore sur l'exercice", "mode": "guided"})
    assert r.json()["assistant_message"]["meta"]["hint_level"] == 1

    # reveal → full solution with the large model
    r = client.post(f"/api/tutor/conversations/{cid}/reveal", headers=headers, json={})
    assert r.status_code == 200
    assert r.json()["assistant_message"]["meta"]["hint_level"] == 2
    assert r.json()["assistant_message"]["meta"]["ai"]["tier"] == "large"

    r = client.get(f"/api/tutor/conversations/{cid}", headers=headers)
    assert r.status_code == 200
    roles = [m["role"] for m in r.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant", "assistant"]
    assert r.json()["conversation"]["title"].startswith("Je ne comprends pas")

    # confusion was recorded as an analytics event
    events = client.get("/api/analytics/events", headers=headers).json()
    assert any(e["type"] == "confusion_detected" for e in events)


def test_tutor_complex_question_uses_large_model(client, auth, fake_provider):
    headers, _ = auth
    cid = _conversation(client, headers)
    r = client.post(f"/api/tutor/conversations/{cid}/messages", headers=headers, json={"content": "Can you prove that the derivative of sin is cos from first principles?", "mode": "direct"})
    assert r.status_code == 200
    assert r.json()["assistant_message"]["meta"]["ai"]["tier"] == "large"


def test_tutor_offline_mode_is_labelled(client, auth, offline_router):
    headers, _ = auth
    cid = _conversation(client, headers, "tn")
    r = client.post(f"/api/tutor/conversations/{cid}/messages", headers=headers, json={"content": "شنوّة هي المشتقة؟", "mode": "guided"})
    assert r.status_code == 200
    meta = r.json()["assistant_message"]["meta"]
    assert meta["ai"]["provider"] == "offline" and meta["ai"]["notice"]
    assert meta["triage"]["language"] == "tn"


def test_quiz_generate_submit_and_grading(client, auth, fake_provider):
    headers, _ = auth
    r = client.post("/api/quizzes/generate", headers=headers, json={"topic": "Photosynthesis", "num_questions": 6, "difficulty": "beginner", "question_types": ["mcq", "short"]})
    assert r.status_code == 201, r.text
    quiz = r.json()
    assert quiz["ai"]["tier"] == "large" and len(quiz["questions"]) == 6
    assert all("correct_option_id" not in q and "expected_answer" not in q for q in quiz["questions"])
    types = [q["type"] for q in quiz["questions"]]
    assert "mcq" in types and "short" in types

    answers = []
    for i, q in enumerate(quiz["questions"]):
        if q["type"] == "mcq":
            answers.append({"question_id": q["id"], "option_id": "a" if i % 2 == 0 else "b"})
        else:
            answers.append({"question_id": q["id"], "text": "Chlorophyll absorbs the light energy"})
    calls_before = len(fake_provider.calls)
    r = client.post(f"/api/quizzes/{quiz['id']}/submit", headers=headers, json={"answers": answers, "time_spent_s": 90})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["total"] == 6 and 0 < res["percent"] < 100
    short_results = [x for x in res["results"] if x["your_answer"].startswith("Chlorophyll")]
    assert short_results and all(x["correct"] for x in short_results)
    assert res["feedback"] == "Fake personalised feedback."
    assert "first_quiz" in res["badges_unlocked"] and res["xp_gained"] >= 10
    # exactly ONE batched grading call + ONE feedback call, no call per MCQ
    assert len(fake_provider.calls) - calls_before == 2

    r = client.get("/api/quizzes", headers=headers)
    summary = next(s for s in r.json() if s["id"] == quiz["id"])
    assert summary["attempts"] == 1 and summary["best_score"] == res["percent"]

    r = client.get(f"/api/quizzes/{quiz['id']}", headers=headers)
    assert r.status_code == 200 and len(r.json()["attempts"]) == 1

    # analytics now reflects the skills
    ov = client.get("/api/analytics/overview", headers=headers).json()
    assert ov["totals"]["quizzes_taken"] == 1 and ov["skills"]
    assert ov["ai_efficiency"]["calls_large"] >= 1 and ov["ai_efficiency"]["calls_compact"] >= 2


def test_quiz_from_document_and_cache(client, auth, fake_provider):
    headers, _ = auth
    text = ("Newton's first law states that an object stays at rest or in uniform motion unless acted upon by a force. " * 20).encode()
    doc = client.post("/api/documents", headers=headers, files={"file": ("physics.txt", text, "text/plain")}).json()
    body = {"document_id": doc["id"], "num_questions": 3, "difficulty": "auto"}
    r1 = client.post("/api/quizzes/generate", headers=headers, json=body)
    r2 = client.post("/api/quizzes/generate", headers=headers, json=body)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["source"] == "document" and r1.json()["topic"] == doc["title"]
    assert r2.json()["ai"]["cached"] is True  # equivalent request served from cache


def test_quiz_requires_topic_or_document(client, auth, fake_provider):
    headers, _ = auth
    r = client.post("/api/quizzes/generate", headers=headers, json={"num_questions": 3})
    assert r.status_code == 422
