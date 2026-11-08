#!/usr/bin/env python3
"""
Seed a running EdNova AI backend with SYNTHETIC demo data (no real personal data).

    python scripts/seed_demo.py --base http://127.0.0.1:8000

Creates: 3 learners (Amal, Lina, Sami) + 1 teacher, a study room with an unbalanced
discussion (to showcase the moderator), a sample course document, a quiz attempt,
a roadmap and revision notes. All accounts use the password `Demo-Pass-2026`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

PASSWORD = "Demo-Pass-2026"
DOC = Path(__file__).with_name("sample_docs") / "photosynthesis_course.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    s = requests.Session()

    def auth(email: str, name: str, lang: str, role: str = "learner") -> dict:
        r = s.post(f"{base}/api/auth/register", json={"email": email, "password": PASSWORD, "display_name": name, "preferred_language": lang, "role": role})
        if r.status_code == 409:
            r = s.post(f"{base}/api/auth/login", json={"email": email, "password": PASSWORD})
        r.raise_for_status()
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    amal = auth("amal@demo.ednova", "Amal", "fr")
    lina = auth("lina@demo.ednova", "Lina", "tn")
    sami = auth("sami@demo.ednova", "Sami", "en")
    prof = auth("prof@demo.ednova", "Prof. Demo", "fr", role="teacher")
    print("✓ accounts ready (password: %s)" % PASSWORD)

    # diagnostic for Amal (visual learner)
    answers = [{"question_id": f"p{i}", "option_id": "a"} for i in range(1, 7)] + [{"question_id": "e1", "option_id": "b"}, {"question_id": "e2", "option_id": "b"}, {"question_id": "e3", "option_id": "a"}]
    s.post(f"{base}/api/diagnostic/submit", headers=amal, json={"answers": answers, "self_reported_level": "intermediate", "goal": "Réussir mon examen de biologie"}).raise_for_status()
    print("✓ diagnostic completed for Amal")

    # document
    with DOC.open("rb") as fh:
        r = s.post(f"{base}/api/documents", headers=amal, files={"file": (DOC.name, fh, "text/markdown")}, data={"title": "Photosynthesis — course notes"})
    r.raise_for_status()
    doc_id = r.json()["id"]
    print("✓ document uploaded:", r.json()["chunk_count"], "chunks")

    # tutor conversation grounded on the document
    r = s.post(f"{base}/api/tutor/conversations", headers=amal, json={"language": "fr", "document_id": doc_id})
    cid = r.json()["id"]
    s.post(f"{base}/api/tutor/conversations/{cid}/messages", headers=amal, json={"content": "Je ne comprends pas le rôle de la chlorophylle dans la photosynthèse", "mode": "guided"}).raise_for_status()
    print("✓ tutor conversation")

    # quiz
    r = s.post(f"{base}/api/quizzes/generate", headers=amal, json={"document_id": doc_id, "num_questions": 5, "difficulty": "auto", "language": "fr"})
    r.raise_for_status()
    quiz = r.json()
    ans = [{"question_id": q["id"], "option_id": "a"} if q["type"] == "mcq" else {"question_id": q["id"], "text": "La chlorophylle absorbe la lumière"} for q in quiz["questions"]]
    s.post(f"{base}/api/quizzes/{quiz['id']}/submit", headers=amal, json={"answers": ans, "time_spent_s": 95}).raise_for_status()
    print("✓ quiz generated and attempted")

    # room with unbalanced participation
    r = s.post(f"{base}/api/rooms", headers=amal, json={"name": "Bio study crew", "topic": "Photosynthèse", "language": "fr"})
    room = r.json()
    for h in (lina, sami):
        s.post(f"{base}/api/rooms/join", headers=h, json={"code": room["code"]}).raise_for_status()
    lines = [
        "La photosynthèse transforme l'énergie lumineuse en énergie chimique.",
        "La chlorophylle absorbe surtout le bleu et le rouge.",
        "Les réactions dépendantes de la lumière ont lieu dans les thylakoïdes.",
        "Le cycle de Calvin fixe le CO2 en sucres.",
        "Les stomates régulent les échanges gazeux.",
        "Je pense que la photosynthèse produit du CO2, non ?",
    ]
    for line in lines:
        s.post(f"{base}/api/rooms/{room['id']}/messages", headers=amal, json={"content": line}).raise_for_status()
    s.post(f"{base}/api/rooms/{room['id']}/messages", headers=lina, json={"content": "موش متأكدة... الـ CO2 يدخل ولا يخرج؟"}).raise_for_status()
    print("✓ room", room["code"], "with 3 members and an unbalanced discussion")

    # roadmap + notes
    s.post(f"{base}/api/roadmaps", headers=amal, json={"goal": "Maîtriser la photosynthèse et la respiration cellulaire", "weeks": 4, "hours_per_week": 4, "language": "fr", "document_id": doc_id}).raise_for_status()
    s.post(f"{base}/api/notes/generate", headers=amal, json={"source": "document", "source_id": doc_id, "format": "both", "language": "fr"}).raise_for_status()
    print("✓ roadmap and revision notes")

    # teacher class
    r = s.post(f"{base}/api/classes", headers=prof, json={"name": "Biologie 1A"})
    code = r.json()["code"]
    for h in (amal, lina, sami):
        s.post(f"{base}/api/classes/join", headers=h, json={"code": code}).raise_for_status()
    print("✓ class", code, "with 3 learners")
    print("\nLogin as amal@demo.ednova / lina@demo.ednova / sami@demo.ednova / prof@demo.ednova — password:", PASSWORD)
    return 0


if __name__ == "__main__":
    sys.exit(main())
