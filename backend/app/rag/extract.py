"""Text extraction for uploaded learning material (PDF, DOCX, TXT, Markdown)."""
from __future__ import annotations

import io
import re
import typing as t
from dataclasses import dataclass


@dataclass
class ExtractedPage:
    page: int
    text: str


class ExtractionError(Exception):
    pass


_WS = re.compile(r"[ \t ]+")
_NL = re.compile(r"\n{3,}")


def _clean(text: str) -> str:
    text = text.replace("\r", "")
    text = _WS.sub(" ", text)
    text = _NL.sub("\n\n", text)
    return text.strip()


def extract_pages(data: bytes, filename: str, mime: str | None = None) -> list[ExtractedPage]:
    name = (filename or "").lower()
    mime = (mime or "").lower()
    if name.endswith(".pdf") or "pdf" in mime:
        return _extract_pdf(data)
    if name.endswith(".docx") or "wordprocessingml" in mime:
        return _extract_docx(data)
    if name.endswith((".txt", ".md", ".markdown", ".csv")) or mime.startswith("text/") or not name:
        return _extract_text(data)
    raise ExtractionError("Unsupported file type. Please upload a PDF, DOCX, TXT or Markdown file.")


def _extract_text(data: bytes) -> list[ExtractedPage]:
    for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover
        text = data.decode("utf-8", "replace")
    text = _clean(text)
    if not text:
        raise ExtractionError("The file is empty.")
    # split long plain-text files into pseudo-pages of ~3000 characters for citation purposes
    pages: list[ExtractedPage] = []
    size = 3000
    for i in range(0, len(text), size):
        pages.append(ExtractedPage(page=len(pages) + 1, text=text[i : i + size]))
    return pages


def _extract_pdf(data: bytes) -> list[ExtractedPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ExtractionError("PDF support requires the 'pypdf' package.") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read the PDF: {exc}") from exc
    pages: list[ExtractedPage] = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:  # pragma: no cover - damaged page
            text = ""
        text = _clean(text)
        if text:
            pages.append(ExtractedPage(page=i, text=text))
    if not pages:
        raise ExtractionError("No extractable text found in the PDF (scanned image PDFs are not supported without OCR).")
    return pages


def _extract_docx(data: bytes) -> list[ExtractedPage]:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise ExtractionError("DOCX support requires the 'python-docx' package.") from exc
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionError(f"Could not read the DOCX file: {exc}") from exc
    paragraphs = [p.text for p in document.paragraphs if p.text and p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))
    text = _clean("\n".join(paragraphs))
    if not text:
        raise ExtractionError("The DOCX file contains no text.")
    return _extract_text(text.encode("utf-8"))


def language_guess(pages: t.Sequence[ExtractedPage]) -> str:
    from app.utils import detect_language

    sample = " ".join(p.text for p in pages[:3])[:4000]
    return detect_language(sample, "en")
