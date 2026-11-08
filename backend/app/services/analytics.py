"""Learning analytics computed from the events log (no model call)."""
from __future__ import annotations

import typing as t
from collections import defaultdict
from datetime import date, timedelta

from app.db import Connection
from app.services.gamification import list_badges
from app.services.users import level_from_xp
from app.utils import loads, today_str


def _skills(events: list[dict]) -> list[dict]:
    history: dict[str, list[float]] = defaultdict(list)
    for e in events:
        if e["type"] != "quiz_completed":
            continue
        for s in (e["payload"].get("skills") or []):
            if s.get("skill"):
                history[s["skill"]].append(float(s.get("score") or 0))
    out = []
    for skill, scores in history.items():
        recent = scores[-3:]
        mastery = round(100 * sum(recent) / len(recent))
        trend = "flat"
        if len(scores) >= 2:
            trend = "up" if scores[-1] > scores[-2] else "down" if scores[-1] < scores[-2] else "flat"
        out.append({"skill": skill, "mastery_percent": mastery, "attempts": len(scores), "trend": trend})
    out.sort(key=lambda s: (s["mastery_percent"], -s["attempts"]))
    return out[:12]


def _activity(events: list[dict]) -> list[dict]:
    today = date.fromisoformat(today_str())
    days = [(today - timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    buckets = {d: {"date": d, "questions": 0, "quiz_points": 0, "minutes": 0} for d in days}
    for e in events:
        d = e["created_at"][:10]
        if d not in buckets:
            continue
        if e["type"] == "question_asked":
            buckets[d]["questions"] += 1
            buckets[d]["minutes"] += 3
        elif e["type"] == "quiz_completed":
            buckets[d]["quiz_points"] += int(float(e["payload"].get("percent") or 0) // 20)
            buckets[d]["minutes"] += max(2, int(e["payload"].get("time_spent_s") or 0) // 60)
        elif e["type"] in ("room_message", "roadmap_step_done", "note_generated", "document_uploaded"):
            buckets[d]["minutes"] += 2
    return [buckets[d] for d in days]


_NEXT_TEXT = {
    "next.diagnostic": {
        "en": "Complete the 3-minute learning-style diagnostic so EdNova can adapt to you.",
        "fr": "Faites le diagnostic de 3 minutes pour qu'EdNova s'adapte à votre façon d'apprendre.",
        "ar": "أكمل تشخيص أسلوب التعلم (3 دقائق) ليتكيف EdNova معك.",
        "tn": "كمّل تشخيص أسلوب التعلّم (3 دقايق) باش EdNova يتأقلم معاك.",
    },
    "next.weak_skill": {
        "en": "Your weakest skill is '{skill}' ({pct}%). Ask the tutor for a hint-first explanation, then retake a quiz.",
        "fr": "Votre compétence la plus fragile est « {skill} » ({pct} %). Demandez au tuteur une explication guidée, puis refaites un quiz.",
        "ar": "أضعف مهارة لديك هي '{skill}' ({pct}%). اطلب من المعلّم شرحاً بالتلميحات ثم أعد اختباراً.",
        "tn": "أضعف مهارة عندك هي '{skill}' ({pct}%). اطلب من المعلّم شرح بالتلميحات وبعد عاود كويز.",
    },
    "next.roadmap": {
        "en": "Continue your roadmap: {goal}", "fr": "Continuez votre feuille de route : {goal}", "ar": "تابع خارطة طريقك: {goal}", "tn": "كمّل خارطة طريقك: {goal}",
    },
    "next.document": {
        "en": "Upload a course document so the tutor and quizzes can use your own material.",
        "fr": "Téléversez un document de cours pour que le tuteur et les quiz utilisent votre propre matériel.",
        "ar": "ارفع وثيقة الدرس ليستخدم المعلّم والاختبارات مادتك الخاصة.",
        "tn": "حمّل وثيقة الدرس باش المعلّم والكويزات يستعملو المادة متاعك.",
    },
    "next.quiz": {
        "en": "Take your first quiz to start tracking skill mastery.", "fr": "Faites votre premier quiz pour commencer à suivre vos compétences.",
        "ar": "أجرِ اختبارك الأول لبدء تتبع إتقان المهارات.", "tn": "دير أوّل كويز باش تبدا تتبّع مهاراتك.",
    },
    "next.room": {
        "en": "Create a study room and invite a peer: explaining to others is the fastest way to learn.",
        "fr": "Créez une salle d'étude et invitez un pair : expliquer aux autres est le moyen le plus rapide d'apprendre.",
        "ar": "أنشئ غرفة دراسة وادعُ زميلاً: الشرح للآخرين أسرع طريقة للتعلم.",
        "tn": "اعمل غرفة دراسة وعيّط لصاحبك: كي تفسّر للناس تتعلّم أسرع.",
    },
    "next.roadmap_new": {
        "en": "Set a new goal and let EdNova build a roadmap for it.", "fr": "Fixez un nouvel objectif et laissez EdNova construire la feuille de route.",
        "ar": "حدد هدفاً جديداً ودع EdNova يبني خارطة طريق له.", "tn": "حطّ هدف جديد وخلّي EdNova يبنيلك خارطة طريق.",
    },
}


def _next_step(skills: list[dict], totals: dict, user: dict, db: Connection) -> dict:
    lang = user.get("preferred_language") if user.get("preferred_language") in ("en", "fr", "ar", "tn") else "en"

    def txt(key: str, **kw: t.Any) -> str:
        return _NEXT_TEXT[key][lang].format(**kw)

    if not user.get("diagnostic_completed"):
        return {"text_key": "next.diagnostic", "text": txt("next.diagnostic"), "action": "onboarding", "target_id": None}
    weak = [s for s in skills if s["mastery_percent"] < 60]
    if weak:
        return {"text_key": "next.weak_skill", "text": txt("next.weak_skill", skill=weak[0]["skill"], pct=weak[0]["mastery_percent"]), "action": "tutor", "target_id": None, "skill": weak[0]["skill"]}
    pending = db.fetchone("SELECT id, goal FROM roadmaps WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user["id"],))
    if pending:
        return {"text_key": "next.roadmap", "text": txt("next.roadmap", goal=pending["goal"]), "action": "roadmap", "target_id": pending["id"]}
    if totals["documents"] == 0:
        return {"text_key": "next.document", "text": txt("next.document"), "action": "document", "target_id": None}
    if totals["quizzes_taken"] == 0:
        return {"text_key": "next.quiz", "text": txt("next.quiz"), "action": "quiz", "target_id": None}
    if totals["rooms"] == 0:
        return {"text_key": "next.room", "text": txt("next.room"), "action": "room", "target_id": None}
    return {"text_key": "next.roadmap_new", "text": txt("next.roadmap_new"), "action": "roadmap", "target_id": None}


def overview(db: Connection, user: dict) -> dict:
    rows = db.fetchall("SELECT type, payload_json, created_at FROM events WHERE user_id = ? ORDER BY created_at ASC", (user["id"],))
    events = [{"type": r["type"], "payload": loads(r["payload_json"], {}), "created_at": r["created_at"]} for r in rows]
    quiz_events = [e for e in events if e["type"] == "quiz_completed"]
    totals = {
        "questions_asked": sum(1 for e in events if e["type"] == "question_asked"),
        "quizzes_taken": len(quiz_events),
        "avg_score_percent": round(sum(float(e["payload"].get("percent") or 0) for e in quiz_events) / len(quiz_events)) if quiz_events else 0,
        "documents": int(db.scalar("SELECT COUNT(*) FROM documents WHERE user_id = ? AND status = 'ready'", (user["id"],)) or 0),
        "rooms": int(db.scalar("SELECT COUNT(*) FROM room_members WHERE user_id = ?", (user["id"],)) or 0),
        "notes": int(db.scalar("SELECT COUNT(*) FROM notes WHERE user_id = ?", (user["id"],)) or 0),
        "roadmaps": int(db.scalar("SELECT COUNT(*) FROM roadmaps WHERE user_id = ?", (user["id"],)) or 0),
        "study_minutes": 0,
    }
    activity = _activity(events)
    totals["study_minutes"] = sum(a["minutes"] for a in activity)
    skills = _skills(events)
    confusion = [
        {"date": e["created_at"][:10], "topic": e["payload"].get("topic"), "level": e["payload"].get("level")}
        for e in events if e["type"] == "confusion_detected"
    ][-20:]
    ai_rows = db.fetchall("SELECT tier, cached, fallback FROM ai_calls WHERE user_id = ?", (user["id"],))
    calls_compact = sum(1 for r in ai_rows if r["tier"] == "compact" and not r["cached"])
    calls_large = sum(1 for r in ai_rows if r["tier"] == "large" and not r["cached"])
    calls_offline = sum(1 for r in ai_rows if r["tier"] == "none" and not r["cached"])
    cache_hits = sum(1 for r in ai_rows if r["cached"])
    fallbacks = sum(1 for r in ai_rows if r["fallback"] and r["tier"] != "none")
    live_total = calls_compact + calls_large
    level, progress = level_from_xp(int(user.get("xp") or 0))
    return {
        "xp": int(user.get("xp") or 0),
        "level_number": level,
        "level_progress_percent": progress,
        "streak_days": int(user.get("streak_days") or 0),
        "totals": totals,
        "skills": skills,
        "activity_last_14_days": activity,
        "confusion_events": confusion,
        "learning_style": user.get("learning_style"),
        "secondary_style": user.get("secondary_style"),
        "level": user.get("level"),
        "style_scores": loads(user.get("style_scores_json"), {}),
        "badges": list_badges(db, user["id"]),
        "next_step": _next_step(skills, totals, user, db),
        "ai_efficiency": {
            "calls_compact": calls_compact, "calls_large": calls_large, "calls_offline": calls_offline, "cache_hits": cache_hits, "fallbacks": fallbacks,
            "large_share_percent": round(100 * calls_large / live_total) if live_total else 0,
            "cache_hit_percent": round(100 * cache_hits / (live_total + cache_hits)) if (live_total + cache_hits) else 0,
        },
    }


def class_dashboard(db: Connection, class_id: str) -> dict:
    members = db.fetchall("SELECT u.* FROM class_members cm JOIN users u ON u.id = cm.user_id WHERE cm.class_id = ?", (class_id,))
    ids = [m["id"] for m in members]
    style_distribution: dict[str, int] = defaultdict(int)
    for m in members:
        if m.get("learning_style"):
            style_distribution[m["learning_style"]] += 1
    if not ids:
        return {"members": 0, "avg_score_percent": 0, "quizzes_taken": 0, "style_distribution": {}, "weak_skills": [], "confusion_hotspots": [], "participation_balance_avg": None, "active_last_7_days": 0}
    placeholders = ",".join("?" for _ in ids)
    rows = db.fetchall(f"SELECT type, payload_json, created_at, user_id FROM events WHERE user_id IN ({placeholders}) ORDER BY created_at ASC", tuple(ids))
    events = [{"type": r["type"], "payload": loads(r["payload_json"], {}), "created_at": r["created_at"], "user_id": r["user_id"]} for r in rows]
    quiz_events = [e for e in events if e["type"] == "quiz_completed"]
    skills = _skills(events)
    hotspots: dict[str, int] = defaultdict(int)
    for e in events:
        if e["type"] == "confusion_detected" and e["payload"].get("topic"):
            hotspots[str(e["payload"]["topic"])] += 1
    week_ago = (date.fromisoformat(today_str()) - timedelta(days=7)).isoformat()
    active = len({e["user_id"] for e in events if e["created_at"][:10] >= week_ago})
    room_rows = db.fetchall(
        f"SELECT DISTINCT r.id FROM rooms r JOIN room_members rm ON rm.room_id = r.id WHERE rm.user_id IN ({placeholders})", tuple(ids)
    )
    balances: list[float] = []
    if room_rows:
        from app.services.rooms import _members, participation

        for r in room_rows:
            balances.append(participation(_members(db, r["id"]))["balance_score"])
    return {
        "members": len(ids),
        "avg_score_percent": round(sum(float(e["payload"].get("percent") or 0) for e in quiz_events) / len(quiz_events)) if quiz_events else 0,
        "quizzes_taken": len(quiz_events),
        "style_distribution": dict(style_distribution),
        "weak_skills": [s for s in skills if s["mastery_percent"] < 70][:8],
        "confusion_hotspots": sorted(({"topic": k, "count": v} for k, v in hotspots.items()), key=lambda x: -x["count"])[:8],
        "participation_balance_avg": round(sum(balances) / len(balances), 2) if balances else None,
        "active_last_7_days": active,
    }
