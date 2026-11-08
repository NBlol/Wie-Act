from tests.conftest import register


def test_register_login_me_update_delete(client):
    headers, user = register(client, language="fr", name="Nour")
    assert user["display_name"] == "Nour"
    assert user["preferred_language"] == "fr"
    assert user["diagnostic_completed"] is False

    r = client.post("/api/auth/login", json={"email": user["email"], "password": "Passw0rd!xyz"})
    assert r.status_code == 200 and r.json()["access_token"]

    r = client.post("/api/auth/login", json={"email": user["email"], "password": "wrong-password"})
    assert r.status_code == 401

    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200 and r.json()["id"] == user["id"]

    r = client.patch("/api/auth/me", headers=headers, json={"preferred_language": "tn", "darija_script": "latin", "learning_style": "analogy"})
    assert r.status_code == 200
    assert r.json()["preferred_language"] == "tn" and r.json()["darija_script"] == "latin" and r.json()["learning_style"] == "analogy"

    r = client.patch("/api/auth/me", headers=headers, json={"learning_style": "telepathy"})
    assert r.status_code == 422

    r = client.delete("/api/auth/me", headers=headers)
    assert r.status_code == 204
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 401


def test_duplicate_email_and_validation(client):
    headers, user = register(client)
    r = client.post("/api/auth/register", json={"email": user["email"], "password": "Passw0rd!xyz", "display_name": "Dup"})
    assert r.status_code == 409
    r = client.post("/api/auth/register", json={"email": "bad", "password": "short", "display_name": "x"})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], list)


def test_protected_routes_require_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    assert client.get("/api/analytics/overview").status_code == 401


def test_health_and_public_system_endpoints(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    r = client.get("/api/system/status")
    assert r.status_code == 200 and r.json()["provider_mode"] in ("live", "offline")
    r = client.get("/api/system/routing")
    tasks = {t["task"]: t["tier"] for t in r.json()["tasks"]}
    assert tasks["tutor_triage"] == "compact"
    assert tasks["quiz_generate"] == "large"
    assert tasks["room_check_explanation"] == "large"
    assert tasks["tutor_answer"] == "dynamic"
    r = client.get("/api/tutor/stages")
    assert [s["key"] for s in r.json()["stages"]] == ["triage", "retrieve", "reason", "format"]
