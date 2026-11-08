from __future__ import annotations

from app.ai.router import get_router
from app.compat import APIRouter, Depends, HTTPException, Response, status
from app.db import Connection
from app.deps import get_current_user, get_db
from app.schemas import ConversationCreate, MessageCreate
from app.services import tutor

router = APIRouter(prefix="/tutor", tags=["tutor"])


@router.get("/conversations")
def list_conversations(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    rows = db.fetchall(
        "SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count "
        "FROM conversations c WHERE c.user_id = ? ORDER BY c.updated_at DESC LIMIT 100",
        (user["id"],),
    )
    return [tutor.serialize_conversation(r, int(r.get("message_count") or 0)) for r in rows]


@router.post("/conversations", status_code=201)
def create_conversation(body: ConversationCreate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = tutor.create_conversation(db, user, body.title, body.language, body.document_id)
    return tutor.serialize_conversation(row, 0)


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    conv = tutor.get_owned_conversation(db, user["id"], conversation_id)
    messages = db.fetchall("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
    return {"conversation": tutor.serialize_conversation(conv, len(messages)), "messages": [tutor.serialize_message(m) for m in messages]}


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> Response:
    tutor.get_owned_conversation(db, user["id"], conversation_id)
    db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    return Response(status_code=204)


@router.post("/conversations/{conversation_id}/messages")
def post_message(conversation_id: str, body: MessageCreate, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    conv = tutor.get_owned_conversation(db, user["id"], conversation_id)
    return tutor.answer_turn(
        db, get_router(), user, conv, body.content, mode=body.mode, use_documents=body.use_documents, style_override=body.style_override
    )


@router.post("/conversations/{conversation_id}/reveal")
def reveal_answer(conversation_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    conv = tutor.get_owned_conversation(db, user["id"], conversation_id)
    question = conv.get("last_question")
    if not question:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Nothing to reveal yet: ask a question first")
    return tutor.answer_turn(db, get_router(), user, conv, question, mode="guided", use_documents=True, reveal=True)
