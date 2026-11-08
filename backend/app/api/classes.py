from __future__ import annotations

from app.compat import APIRouter, Depends, HTTPException, status
from app.db import Connection
from app.deps import get_current_user, get_db, require_teacher
from app.schemas import ClassCreate, ClassJoin
from app.services import analytics
from app.utils import new_id, now_iso, room_code

router = APIRouter(prefix="/classes", tags=["teacher"])


@router.post("", status_code=201)
def create_class(body: ClassCreate, teacher: dict = Depends(require_teacher), db: Connection = Depends(get_db)) -> dict:
    cid = new_id()
    code = room_code(6)
    while db.fetchone("SELECT 1 FROM classes WHERE code = ?", (code,)):
        code = room_code(6)
    db.execute("INSERT INTO classes (id, code, name, teacher_id, created_at) VALUES (?, ?, ?, ?, ?)", (cid, code, body.name.strip(), teacher["id"], now_iso()))
    return {"id": cid, "code": code, "name": body.name.strip(), "member_count": 0, "created_at": now_iso()}


@router.get("")
def list_classes(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    if user.get("role") == "teacher":
        rows = db.fetchall(
            "SELECT c.*, (SELECT COUNT(*) FROM class_members m WHERE m.class_id = c.id) AS member_count FROM classes c WHERE c.teacher_id = ? ORDER BY c.created_at DESC",
            (user["id"],),
        )
    else:
        rows = db.fetchall(
            "SELECT c.*, (SELECT COUNT(*) FROM class_members m WHERE m.class_id = c.id) AS member_count FROM classes c JOIN class_members me ON me.class_id = c.id AND me.user_id = ? ORDER BY c.created_at DESC",
            (user["id"],),
        )
    return [{"id": r["id"], "code": r["code"], "name": r["name"], "member_count": int(r.get("member_count") or 0), "created_at": r["created_at"]} for r in rows]


@router.post("/join")
def join_class(body: ClassJoin, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    row = db.fetchone("SELECT * FROM classes WHERE code = ?", (body.code.strip().upper(),))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No class with this code")
    if not db.fetchone("SELECT 1 FROM class_members WHERE class_id = ? AND user_id = ?", (row["id"], user["id"])):
        db.execute("INSERT INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)", (row["id"], user["id"], now_iso()))
    return {"joined": True, "class": {"id": row["id"], "name": row["name"], "code": row["code"]}}


@router.get("/{class_id}/dashboard")
def class_dashboard(class_id: str, teacher: dict = Depends(require_teacher), db: Connection = Depends(get_db)) -> dict:
    row = db.fetchone("SELECT * FROM classes WHERE id = ? AND teacher_id = ?", (class_id, teacher["id"]))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Class not found")
    data = analytics.class_dashboard(db, class_id)
    return {"class": {"id": row["id"], "name": row["name"], "code": row["code"]}, **data}
