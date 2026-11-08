from __future__ import annotations

from app.ai.router import get_router
from app.compat import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from app.config import settings
from app.db import Connection
from app.deps import get_current_user, get_db
from app.rag import index as rag_index
from app.rag.chunk import chunk_pages
from app.rag.extract import ExtractionError, extract_pages, language_guess
from app.schemas import DocumentAsk, DocumentSearch
from app.services.gamification import record_event
from app.utils import SUPPORTED_LANGUAGES, dumps, new_id, now_iso, truncate

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_EXT = (".pdf", ".txt", ".md", ".markdown", ".docx")


def serialize_document(row: dict, with_preview: bool = False) -> dict:
    out = {
        "id": row["id"], "title": row["title"], "filename": row["filename"], "mime": row["mime"], "pages": int(row.get("pages") or 0),
        "chunk_count": int(row.get("chunk_count") or 0), "chars": int(row.get("chars") or 0), "language": row["language"],
        "status": row["status"], "error": row.get("error"), "created_at": row["created_at"],
    }
    if with_preview:
        out["preview"] = row.get("preview") or ""
    return out


def _owned(db: Connection, user_id: str, document_id: str) -> dict:
    row = db.fetchone("SELECT * FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return row


@router.post("", status_code=201)
async def upload(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    language: str | None = Form(None),
    user: dict = Depends(get_current_user),
    db: Connection = Depends(get_db),
) -> dict:
    filename = (file.filename or "document").strip()
    if not filename.lower().endswith(_ALLOWED_EXT):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Allowed types: PDF, DOCX, TXT, Markdown")
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File larger than {settings.max_upload_mb} MB")
    doc_id = new_id()
    mime = file.content_type or "application/octet-stream"
    try:
        pages = extract_pages(data, filename, mime)
        chunks = chunk_pages(pages)
        lang = language if language in SUPPORTED_LANGUAGES else language_guess(pages)
        full_text = "\n".join(p.text for p in pages)
        db.execute(
            "INSERT INTO documents (id, user_id, title, filename, mime, pages, chunk_count, chars, language, status, error, preview, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', NULL, ?, ?)",
            (doc_id, user["id"], (title or filename.rsplit(".", 1)[0])[:120], filename, mime, len(pages), len(chunks), len(full_text), lang, truncate(full_text, 1200), now_iso()),
        )
        for c in chunks:
            db.execute("INSERT INTO chunks (id, document_id, idx, page, text) VALUES (?, ?, ?, ?, ?)", (new_id(), doc_id, c.idx, c.page, c.text))
        rag_index.invalidate(doc_id)
        record_event(db, user["id"], "document_uploaded", {"document_id": doc_id, "pages": len(pages), "chunks": len(chunks)})
    except ExtractionError as exc:
        db.execute(
            "INSERT INTO documents (id, user_id, title, filename, mime, pages, chunk_count, chars, language, status, error, preview, created_at) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 'en', 'failed', ?, NULL, ?)",
            (doc_id, user["id"], (title or filename)[:120], filename, mime, str(exc), now_iso()),
        )
    # the uploaded bytes are NOT kept on disk: only the extracted text chunks are stored (data minimisation)
    row = db.fetchone("SELECT * FROM documents WHERE id = ?", (doc_id,))
    assert row
    return serialize_document(row, with_preview=True)


@router.get("")
def list_documents(user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> list[dict]:
    rows = db.fetchall("SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC", (user["id"],))
    return [serialize_document(r) for r in rows]


@router.get("/{document_id}")
def get_document(document_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    return serialize_document(_owned(db, user["id"], document_id), with_preview=True)


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: str, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> Response:
    _owned(db, user["id"], document_id)
    db.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    db.execute("UPDATE conversations SET document_id = NULL WHERE document_id = ?", (document_id,))
    rag_index.invalidate(document_id)
    return Response(status_code=204)


@router.post("/{document_id}/search")
def search_document(document_id: str, body: DocumentSearch, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    _owned(db, user["id"], document_id)
    return {"results": rag_index.search(db, document_id, body.query, k=body.k)}


@router.post("/{document_id}/ask")
def ask_document(document_id: str, body: DocumentAsk, user: dict = Depends(get_current_user), db: Connection = Depends(get_db)) -> dict:
    doc = _owned(db, user["id"], document_id)
    language = body.language if body.language in SUPPORTED_LANGUAGES else user.get("preferred_language", "en")
    sources = rag_index.search(db, document_id, body.question, k=5)
    out = get_router().run(
        "rag_answer",
        {"question": body.question, "language": language, "darija_script": user.get("darija_script", "arabic"), "sources": sources, "source_ids": rag_index.source_ids(sources)},
        user_id=user["id"],
        db=db,
    )
    data = out.data if isinstance(out.data, dict) else {}
    answer = data.get("answer_md") or data.get("_raw") or ""
    used = data.get("used_sources") if isinstance(data.get("used_sources"), list) else list(range(1, len(sources) + 1))
    record_event(db, user["id"], "question_asked", {"document_id": document_id, "topic": doc["title"], "language": language, "complexity": "rag"})
    return {
        "answer": answer,
        "sources": [{**s, "index": i} for i, s in enumerate(sources, 1) if i in used or not used],
        "ai": out.ai,
    }
