"""Sentence-aware chunking with overlap (page numbers preserved for citations)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.rag.extract import ExtractedPage

_SENTENCE = re.compile(r"(?<=[.!?؟。])\s+|\n{2,}")


@dataclass
class Chunk:
    idx: int
    page: int
    text: str


def chunk_pages(pages: list[ExtractedPage], target_chars: int = 700, overlap_sentences: int = 1, min_chars: int = 120) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        sentences = [s.strip() for s in _SENTENCE.split(page.text) if s and s.strip()]
        buf: list[str] = []
        size = 0
        for sentence in sentences:
            # very long "sentences" (tables, lists without punctuation) are hard-split
            while len(sentence) > target_chars * 1.5:
                head, sentence = sentence[:target_chars], sentence[target_chars:]
                buf.append(head)
                size += len(head)
                if size >= target_chars:
                    chunks.append(Chunk(len(chunks), page.page, " ".join(buf)))
                    buf, size = buf[-overlap_sentences:], sum(len(s) for s in buf[-overlap_sentences:])
            buf.append(sentence)
            size += len(sentence) + 1
            if size >= target_chars:
                chunks.append(Chunk(len(chunks), page.page, " ".join(buf)))
                buf = buf[-overlap_sentences:] if overlap_sentences else []
                size = sum(len(s) + 1 for s in buf)
        if buf and (size >= min_chars or not chunks or chunks[-1].page != page.page):
            text = " ".join(buf)
            if chunks and chunks[-1].page == page.page and len(text) < min_chars:
                chunks[-1].text = chunks[-1].text + " " + text
            else:
                chunks.append(Chunk(len(chunks), page.page, text))
    return chunks
