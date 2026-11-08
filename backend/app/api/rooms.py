from __future__ import annotations

from app.ai.router import get_router
from app.compat import APIRouter, Depends, HTTPException, status
from app.db import Connection
from app.deps import get_current_user, get_db
from app.schemas import RoomCreate, RoomJoin, RoomMessageCreate, RoomModerate, RoomQuizCreate
from app.services import quiz as quiz_service
from app.services import rooms as room_service

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("")
def list_rooms(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    rows = db.fetchall(
        "SELECT r.*, (SELECT COUNT(*) FROM room_members m WHERE m.room_id = r.id) AS member_count FROM rooms r "
        "JOIN room_members me ON me.room_id = r.id AND me.user_id = ? ORDER BY r.created_at DESC",
        (user["id"],),
    )
    return [
        {"id": r["id"], "code": r["code"], "name": r["name"], "topic": r["topic"], "language": r["language"], "member_count": int(r.get("member_count") or 0),
         "created_at": r["created_at"], "is_owner": r["owner_id"] == user["id"], "quiz_id": r.get("quiz_id")}
        for r in rows
    ]


@router.post("", status_code=201)
def create_room(body: RoomCreate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = room_service.create_room(db, user, body.name, body.topic, body.language)
    return room_service.serialize_room(db, row, user["id"])


@router.post("/join")
def join_room(body: RoomJoin, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = room_service.join_room(db, user, body.code)
    return room_service.serialize_room(db, row, user["id"])


@router.get("/{room_id}")
def get_room(room_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = room_service.get_member_room(db, user["id"], room_id)
    return room_service.serialize_room(db, row, user["id"])


@router.get("/{room_id}/messages")
def get_messages(room_id: str, after: str | None = None, limit: int = 50, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    room_service.get_member_room(db, user["id"], room_id)
    limit = max(1, min(limit, 200))
    if after:
        anchor = db.fetchone("SELECT created_at FROM room_messages WHERE id = ? AND room_id = ?", (after, room_id))
        if anchor:
            rows = db.fetchall(
                "SELECT * FROM room_messages WHERE room_id = ? AND created_at > ? ORDER BY created_at ASC LIMIT ?", (room_id, anchor["created_at"], limit)
            )
        else:
            rows = []
    else:
        rows = db.fetchall("SELECT * FROM room_messages WHERE room_id = ? ORDER BY created_at DESC LIMIT ?", (room_id, limit))
        rows.reverse()
    members = room_service._members(db, room_id)
    return {"messages": [room_service.serialize_message(r) for r in rows], "participation": room_service.participation(members)}


@router.post("/{room_id}/messages")
def post_message(room_id: str, body: RoomMessageCreate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    room = room_service.get_member_room(db, user["id"], room_id)
    return room_service.post_message(db, get_router(), user, room, body.content.strip())


@router.post("/{room_id}/moderate")
def moderate(room_id: str, body: RoomModerate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    room = room_service.get_member_room(db, user["id"], room_id)
    return room_service.moderate(db, get_router(), user, room, body.action, body.message_id)


@router.post("/{room_id}/quiz", status_code=201)
def room_quiz(room_id: str, body: RoomQuizCreate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    room = room_service.get_member_room(db, user["id"], room_id)
    quiz = quiz_service.generate_quiz(
        db, get_router(), user, topic=room["topic"], document_id=None, num_questions=body.num_questions, difficulty="auto",
        language=room["language"], question_types=["mcq"], room_id=room_id,
    )
    db.execute("UPDATE rooms SET quiz_id = ? WHERE id = ?", (quiz["id"], room_id))
    announce = {
        "en": f"📝 A collaborative quiz on **{room['topic']}** is ready ({body.num_questions} questions). Everyone take it, then compare answers together!",
        "fr": f"📝 Un quiz collaboratif sur **{room['topic']}** est prêt ({body.num_questions} questions). Faites-le chacun, puis comparez vos réponses !",
        "ar": f"📝 اختبار تعاوني حول **{room['topic']}** جاهز ({body.num_questions} أسئلة). ليجرّبه الجميع ثم قارنوا إجاباتكم!",
        "tn": f"📝 كويز تعاوني على **{room['topic']}** حاضر ({body.num_questions} أسئلة). الكل يعملو وبعد قارنو أجوبتكم!",
    }
    room_service._post_moderator(db, room_id, announce.get(room["language"], announce["en"]), {"kind": "quiz", "quiz_id": quiz["id"]})
    return quiz


@router.get("/{room_id}/leaderboard")
def get_leaderboard(room_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    room = room_service.get_member_room(db, user["id"], room_id)
    return room_service.leaderboard(db, room)
