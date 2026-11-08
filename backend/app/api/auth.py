from __future__ import annotations

from app.compat import APIRouter, Depends, HTTPException, Response, status
from app.db import Connection
from app.deps import get_current_user, get_db
from app.schemas import LoginRequest, RegisterRequest, UpdateMeRequest
from app.security import create_access_token, hash_password, verify_password
from app.services.users import serialize_user
from app.utils import new_id, now_iso

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Connection = Depends(get_db)) -> dict:
    if db.fetchone("SELECT id FROM users WHERE email = ?", (body.email,)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user_id = new_id()
    db.execute(
        "INSERT INTO users (id, email, password_hash, display_name, role, preferred_language, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, body.email, hash_password(body.password), body.display_name.strip(), body.role, body.preferred_language, now_iso()),
    )
    user = db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
    assert user
    return {"access_token": create_access_token(user_id, body.role), "token_type": "bearer", "user": serialize_user(user)}


@router.post("/login")
def login(body: LoginRequest, db: Connection = Depends(get_db)) -> dict:
    user = db.fetchone("SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),))
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return {"access_token": create_access_token(user["id"], user["role"]), "token_type": "bearer", "user": serialize_user(user)}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return serialize_user(user)


@router.patch("/me")
def update_me(body: UpdateMeRequest, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        assignments = ", ".join(f"{k} = ?" for k in updates)
        db.execute(f"UPDATE users SET {assignments} WHERE id = ?", (*updates.values(), user["id"]))
    fresh = db.fetchone("SELECT * FROM users WHERE id = ?", (user["id"],))
    assert fresh
    return serialize_user(fresh)


@router.delete("/me", status_code=204)
def delete_me(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> Response:
    """Right to erasure: delete the account and every record linked to it."""
    uid = user["id"]
    conv_ids = [r["id"] for r in db.fetchall("SELECT id FROM conversations WHERE user_id = ?", (uid,))]
    for cid in conv_ids:
        db.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
    db.execute("DELETE FROM conversations WHERE user_id = ?", (uid,))
    doc_ids = [r["id"] for r in db.fetchall("SELECT id FROM documents WHERE user_id = ?", (uid,))]
    for did in doc_ids:
        db.execute("DELETE FROM chunks WHERE document_id = ?", (did,))
    db.execute("DELETE FROM documents WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM quiz_attempts WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM quizzes WHERE user_id = ? AND room_id IS NULL", (uid,))
    db.execute("UPDATE room_messages SET user_id = NULL, display_name = 'deleted learner' WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM room_members WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM roadmaps WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM notes WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM events WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM badges WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM ai_calls WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM class_members WHERE user_id = ?", (uid,))
    db.execute("DELETE FROM users WHERE id = ?", (uid,))
    return Response(status_code=204)
