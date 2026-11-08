"""Per-document retrieval index (built from the `chunks` table, cached in memory)."""
from __future__ import annotations

import threading
import typing as t

from app.db import Connection
from app.rag.bm25 import BM25Index
from app.utils import truncate

_lock = threading.Lock()
_indexes: dict[str, tuple[int, BM25Index, list[dict]]] = {}


def _load_chunks(db: Connection, document_id: str) -> list[dict]:
    return db.fetchall("SELECT id, idx, page, text FROM chunks WHERE document_id = ? ORDER BY idx", (document_id,))


def get_index(db: Connection, document_id: str) -> tuple[BM25Index, list[dict]]:
    count = int(db.scalar("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document_id,)) or 0)
    with _lock:
        cached = _indexes.get(document_id)
        if cached and cached[0] == count:
            return cached[1], cached[2]
    chunks = _load_chunks(db, document_id)
    index = BM25Index([c["text"] for c in chunks])
    with _lock:
        _indexes[document_id] = (count, index, chunks)
    return index, chunks


def invalidate(document_id: str) -> None:
    with _lock:
        _indexes.pop(document_id, None)


def search(db: Connection, document_id: str, query: str, k: int = 5, excerpt_chars: int = 900) -> list[dict]:
    """Return ranked passages: [{chunk_id, document_id, page, score, excerpt}]."""
    index, chunks = get_index(db, document_id)
    if not chunks:
        return []
    results = []
    for i, score in index.search(query, k=k):
        chunk = chunks[i]
        results.append(
            {
                "chunk_id": chunk["id"],
                "document_id": document_id,
                "page": int(chunk["page"]),
                "score": score,
                "excerpt": truncate(chunk["text"], excerpt_chars),
            }
        )
    return results


def sample_chunks(db: Connection, document_id: str, limit: int = 8, excerpt_chars: int = 1200) -> list[dict]:
    """Evenly spaced passages used when no query is available (quiz / notes from a whole document)."""
    chunks = _load_chunks(db, document_id)
    if not chunks:
        return []
    if len(chunks) <= limit:
        picked = chunks
    else:
        step = len(chunks) / limit
        picked = [chunks[int(i * step)] for i in range(limit)]
    return [
        {"chunk_id": c["id"], "document_id": document_id, "page": int(c["page"]), "score": 1.0, "excerpt": truncate(c["text"], excerpt_chars)}
        for c in picked
    ]


def source_ids(sources: t.Sequence[dict]) -> str:
    return ",".join(sorted(str(s.get("chunk_id")) for s in sources))
