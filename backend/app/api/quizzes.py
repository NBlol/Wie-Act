from __future__ import annotations

from app.ai.router import get_router
from app.compat import APIRouter, Depends
from app.db import Connection
from app.deps import get_current_user, get_db
from app.schemas import QuizGenerate, QuizSubmit
from app.services import quiz as quiz_service

router = APIRouter(prefix="/quizzes", tags=["quizzes"])


@router.post("/generate", status_code=201)
def generate(body: QuizGenerate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    return quiz_service.generate_quiz(
        db, get_router(), user,
        topic=body.topic, document_id=body.document_id, num_questions=body.num_questions, difficulty=body.difficulty,
        language=body.language, question_types=list(dict.fromkeys(body.question_types)) or ["mcq"], room_id=None,
    )


@router.get("")
def list_quizzes(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    return quiz_service.quiz_summaries(db, user["id"])


@router.get("/{quiz_id}")
def get_quiz(quiz_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = quiz_service.get_accessible_quiz(db, user["id"], quiz_id)
    data = quiz_service.serialize_quiz(row)
    attempts = db.fetchall(
        "SELECT id, percent, score, total, created_at FROM quiz_attempts WHERE quiz_id = ? AND user_id = ? ORDER BY created_at DESC", (quiz_id, user["id"])
    )
    data["attempts"] = attempts
    return data


@router.post("/{quiz_id}/submit")
def submit(quiz_id: str, body: QuizSubmit, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = quiz_service.get_accessible_quiz(db, user["id"], quiz_id)
    return quiz_service.submit_quiz(db, get_router(), user, row, [a.model_dump() for a in body.answers], body.time_spent_s)
