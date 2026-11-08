from __future__ import annotations

from tests.conftest import register


def test_room_lifecycle_participation_and_moderation(client, fake_provider):
    h_owner, owner = register(client, name="Amal")
    h_lina, lina = register(client, name="Lina")
    h_sami, sami = register(client, name="Sami")

    r = client.post("/api/rooms", headers=h_owner, json={"name": "Calculus crew", "topic": "Derivatives", "language": "en"})
    assert r.status_code == 201, r.text
    room = r.json()
    assert room["member_count"] == 1 and room["is_owner"] is True and len(room["code"]) == 6

    for h in (h_lina, h_sami):
        r = client.post("/api/rooms/join", headers=h, json={"code": room["code"].lower()})
        assert r.status_code == 200 and r.json()["member_count"] >= 2
    assert client.post("/api/rooms/join", headers=h_lina, json={"code": "ZZZZZZ"}).status_code == 404

    # welcome message from the moderator exists
    msgs = client.get(f"/api/rooms/{room['id']}/messages", headers=h_lina).json()
    assert msgs["messages"][0]["role"] == "moderator"

    # Amal dominates the discussion → after N messages the moderator nudges quiet members
    moderator_seen = None
    for i in range(7):
        r = client.post(f"/api/rooms/{room['id']}/messages", headers=h_owner, json={"content": f"The derivative measures the rate of change, point {i}."})
        assert r.status_code == 200
        if r.json()["moderator_message"]:
            moderator_seen = r.json()["moderator_message"]
    assert moderator_seen is not None and moderator_seen["meta"]["kind"] == "nudge"
    assert moderator_seen["meta"]["ai"]["tier"] == "compact"
    assert "Lina" in moderator_seen["meta"]["participation"]["quiet_members"]

    detail = client.get(f"/api/rooms/{room['id']}", headers=h_sami).json()
    assert detail["participation"]["dominant_member"] == "Amal"
    assert detail["participation"]["balance_score"] < 0.5
    assert set(detail["participation"]["quiet_members"]) == {"Lina", "Sami"}

    # incremental polling with the `after` cursor
    all_msgs = client.get(f"/api/rooms/{room['id']}/messages", headers=h_sami).json()["messages"]
    r = client.post(f"/api/rooms/{room['id']}/messages", headers=h_lina, json={"content": "I think the derivative of x^2 is x."})
    lina_msg = r.json()["message"]
    newer = client.get(f"/api/rooms/{room['id']}/messages?after={all_msgs[-1]['id']}", headers=h_sami).json()["messages"]
    assert [m["id"] for m in newer] == [lina_msg["id"]]

    # checking a peer explanation goes to the LARGE model
    r = client.post(f"/api/rooms/{room['id']}/moderate", headers=h_sami, json={"action": "check_explanation", "message_id": lina_msg["id"]})
    assert r.status_code == 200
    assert r.json()["ai"]["tier"] == "large" and r.json()["moderator_message"]["content"].startswith("**Partially Correct**")

    r = client.post(f"/api/rooms/{room['id']}/moderate", headers=h_sami, json={"action": "guiding_question"})
    assert r.json()["ai"]["tier"] == "compact"
    r = client.post(f"/api/rooms/{room['id']}/moderate", headers=h_sami, json={"action": "summarize"})
    assert r.json()["ai"]["tier"] == "large" and r.json()["moderator_message"]["content"].startswith("## Fake summary")

    # @ednova mention → the moderator answers the group's question
    r = client.post(f"/api/rooms/{room['id']}/messages", headers=h_sami, json={"content": "@ednova what is the chain rule?"})
    assert r.json()["moderator_message"]["meta"]["kind"] == "answer"

    # collaborative quiz + leaderboard
    r = client.post(f"/api/rooms/{room['id']}/quiz", headers=h_owner, json={"num_questions": 3})
    assert r.status_code == 201
    quiz = r.json()
    assert client.get(f"/api/rooms/{room['id']}", headers=h_owner).json()["quiz_id"] == quiz["id"]
    for h, pick in ((h_owner, "a"), (h_lina, "b")):
        answers = [{"question_id": q["id"], "option_id": pick} for q in quiz["questions"]]
        r = client.post(f"/api/quizzes/{quiz['id']}/submit", headers=h, json={"answers": answers, "time_spent_s": 30})
        assert r.status_code == 200
    board = client.get(f"/api/rooms/{room['id']}/leaderboard", headers=h_sami).json()
    assert board[0]["display_name"] == "Amal" and board[0]["percent"] == 100
    assert board[1]["display_name"] == "Lina" and board[1]["percent"] == 0

    # non-members cannot see the room
    h_other, _ = register(client)
    assert client.get(f"/api/rooms/{room['id']}", headers=h_other).status_code == 404
    rooms = client.get("/api/rooms", headers=h_lina).json()
    assert any(x["id"] == room["id"] for x in rooms)


def test_roadmap_create_and_progress(client, auth, fake_provider):
    headers, _ = auth
    r = client.post("/api/roadmaps", headers=headers, json={"goal": "Pass my linear algebra exam", "weeks": 3, "hours_per_week": 4, "language": "en"})
    assert r.status_code == 201, r.text
    rm = r.json()
    assert rm["ai"]["tier"] == "large" and len(rm["milestones"]) == 3 and rm["progress_percent"] == 0
    assert "roadmap_starter" in rm["badges_unlocked"]
    act = rm["milestones"][0]["activities"][0]
    r = client.patch(f"/api/roadmaps/{rm['id']}/activities/{act['id']}", headers=headers, json={"done": True})
    assert r.status_code == 200
    assert r.json()["progress_percent"] > 0 and r.json()["xp_gained"] == 8
    r = client.patch(f"/api/roadmaps/{rm['id']}/activities/{act['id']}", headers=headers, json={"done": True})
    assert r.json()["xp_gained"] == 0  # no double XP
    assert client.get("/api/roadmaps", headers=headers).json()[0]["id"] == rm["id"]
    assert client.patch(f"/api/roadmaps/{rm['id']}/activities/nope", headers=headers, json={"done": True}).status_code == 404


def test_roadmap_offline_fallback(client, auth, offline_router):
    headers, _ = auth
    r = client.post("/api/roadmaps", headers=headers, json={"goal": "Learn Python basics", "weeks": 2, "language": "ar"})
    assert r.status_code == 201
    assert r.json()["ai"]["provider"] == "offline" and len(r.json()["milestones"]) == 2
    assert r.json()["milestones"][0]["title"].startswith("الأسبوع 1")


def test_notes_from_document_conversation_and_topic(client, auth, fake_provider):
    headers, _ = auth
    text = ("Osmosis is the movement of water across a semi-permeable membrane. Diffusion is the net movement of particles. " * 15).encode()
    doc = client.post("/api/documents", headers=headers, files={"file": ("cells.txt", text, "text/plain")}).json()
    r = client.post("/api/notes/generate", headers=headers, json={"source": "document", "source_id": doc["id"], "format": "both"})
    assert r.status_code == 201, r.text
    note = r.json()
    assert note["ai"]["tier"] == "large" and note["title"] == "Fake notes" and note["flashcards"] == [{"q": "Q?", "a": "A."}]
    assert "note_taker" in note["badges_unlocked"]

    cid = client.post("/api/tutor/conversations", headers=headers, json={}).json()["id"]
    client.post(f"/api/tutor/conversations/{cid}/messages", headers=headers, json={"content": "Explain osmosis simply"})
    r = client.post("/api/notes/generate", headers=headers, json={"source": "conversation", "source_id": cid, "format": "summary"})
    assert r.status_code == 201 and r.json()["flashcards"] == []

    assert client.post("/api/notes/generate", headers=headers, json={"source": "topic", "format": "both"}).status_code == 422
    notes = client.get("/api/notes", headers=headers).json()
    assert len(notes) == 2
    assert client.delete(f"/api/notes/{note['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/notes/{note['id']}", headers=headers).status_code == 404


def test_notes_offline_extractive(client, auth, offline_router):
    headers, _ = auth
    text = ("A prime number is a natural number greater than 1 with no divisors other than 1 and itself. Seven is prime. " * 10).encode()
    doc = client.post("/api/documents", headers=headers, files={"file": ("primes.txt", text, "text/plain")}).json()
    r = client.post("/api/notes/generate", headers=headers, json={"source": "document", "source_id": doc["id"], "format": "both", "language": "fr"})
    assert r.status_code == 201
    assert r.json()["ai"]["provider"] == "offline" and "prime" in r.json()["content_md"].lower()
    assert r.json()["flashcards"]  # definition sentences became flashcards


def test_teacher_classes_dashboard(client, fake_provider):
    h_teacher, teacher = register(client, role="teacher", name="Prof")
    h_learner, learner = register(client, name="Student1")
    assert client.post("/api/classes", headers=h_learner, json={"name": "Nope"}).status_code == 403
    r = client.post("/api/classes", headers=h_teacher, json={"name": "Bio 101"})
    assert r.status_code == 201
    klass = r.json()
    r = client.post("/api/classes/join", headers=h_learner, json={"code": klass["code"]})
    assert r.status_code == 200 and r.json()["joined"] is True
    # learner activity
    quiz = client.post("/api/quizzes/generate", headers=h_learner, json={"topic": "Cells", "num_questions": 3}).json()
    client.post(f"/api/quizzes/{quiz['id']}/submit", headers=h_learner, json={"answers": [{"question_id": q["id"], "option_id": "a"} for q in quiz["questions"]], "time_spent_s": 20})
    r = client.get(f"/api/classes/{klass['id']}/dashboard", headers=h_teacher)
    assert r.status_code == 200
    dash = r.json()
    assert dash["members"] == 1 and dash["quizzes_taken"] == 1 and dash["avg_score_percent"] == 100
    assert dash["active_last_7_days"] == 1
    assert client.get(f"/api/classes/{klass['id']}/dashboard", headers=h_learner).status_code == 403
    assert client.get("/api/classes", headers=h_learner).json()[0]["code"] == klass["code"]


def test_analytics_overview_shape_and_next_step(client, auth):
    headers, _ = auth
    ov = client.get("/api/analytics/overview", headers=headers).json()
    for key in ("xp", "level_number", "streak_days", "totals", "skills", "activity_last_14_days", "badges", "next_step", "ai_efficiency"):
        assert key in ov
    assert len(ov["activity_last_14_days"]) == 14
    assert ov["next_step"]["action"] == "onboarding"  # diagnostic not done yet
    assert len(ov["badges"]) == 12 and not any(b["unlocked"] for b in ov["badges"])
