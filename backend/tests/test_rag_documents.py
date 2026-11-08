from __future__ import annotations

import io

from app.rag.bm25 import BM25Index, tokenize
from app.rag.chunk import chunk_pages
from app.rag.extract import ExtractedPage, extract_pages

SAMPLE_TEXT = """Photosynthesis is the process by which green plants convert light energy into chemical energy.
Chlorophyll absorbs light energy, mostly in the blue and red wavelengths. The light-dependent reactions take place in the thylakoid membranes.
The Calvin cycle fixes carbon dioxide into sugars using ATP and NADPH. Stomata regulate gas exchange in leaves.
Cellular respiration is the opposite process: it releases the energy stored in glucose. Mitochondria are the site of respiration.
Osmosis is the movement of water across a semi-permeable membrane. Diffusion moves particles from high to low concentration.
""" * 3


def test_tokenizer_handles_latin_and_arabic():
    assert "photosynthes" in tokenize("Photosynthesis photosynthesis") or "photosynthesi" in tokenize("Photosynthesis")
    toks = tokenize("الخلية النباتية والخلايا الحيوانية")
    assert toks and all(not t.startswith("ال") for t in toks)
    assert tokenize("le la les de") == []  # stopwords removed


def test_bm25_ranks_relevant_passage_first():
    docs = [
        "Chlorophyll absorbs light energy in the thylakoid membranes.",
        "The Calvin cycle fixes carbon dioxide into sugars.",
        "Mitochondria release energy stored in glucose during respiration.",
    ]
    idx = BM25Index(docs)
    top = idx.search("What absorbs light?", k=2)
    assert top and top[0][0] == 0 and top[0][1] == 1.0
    assert idx.search("completely unrelated zebra", k=3) == []


def test_extract_and_chunk_text():
    pages = extract_pages(SAMPLE_TEXT.encode("utf-8"), "bio.txt", "text/plain")
    assert pages and pages[0].page == 1
    chunks = chunk_pages(pages, target_chars=300)
    assert len(chunks) >= 3
    assert all(c.text for c in chunks)
    assert chunks[0].idx == 0 and chunks[1].idx == 1


def test_pdf_extraction_roundtrip():
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    # a blank PDF has no text → an explicit, user-friendly error
    try:
        extract_pages(buf.getvalue(), "blank.pdf", "application/pdf")
        raised = False
    except Exception as exc:  # noqa: BLE001
        raised = "No extractable text" in str(exc)
    assert raised


def test_document_upload_search_ask_and_delete(client, auth, offline_router):
    headers, _ = auth
    files = {"file": ("biology.txt", SAMPLE_TEXT.encode("utf-8"), "text/plain")}
    r = client.post("/api/documents", headers=headers, files=files, data={"title": "Biology notes"})
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["status"] == "ready" and doc["chunk_count"] >= 1 and doc["title"] == "Biology notes" and doc["language"] == "en"

    r = client.get("/api/documents", headers=headers)
    assert any(d["id"] == doc["id"] for d in r.json())

    r = client.post(f"/api/documents/{doc['id']}/search", headers=headers, json={"query": "what absorbs light energy", "k": 3})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results and "Chlorophyll" in results[0]["excerpt"]

    # offline mode: extractive answer, clearly labelled, with sources
    r = client.post(f"/api/documents/{doc['id']}/ask", headers=headers, json={"question": "Where does the Calvin cycle happen and what does it fix?"})
    assert r.status_code == 200
    body = r.json()
    assert body["ai"]["provider"] == "offline" and body["ai"]["notice"]
    assert body["sources"] and "Calvin" in body["answer"]

    r = client.post("/api/documents", headers=headers, files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 415

    r = client.delete(f"/api/documents/{doc['id']}", headers=headers)
    assert r.status_code == 204
    assert client.get(f"/api/documents/{doc['id']}", headers=headers).status_code == 404


def test_document_ask_live_routes_by_sources(client, auth, fake_provider):
    headers, _ = auth
    r = client.post("/api/documents", headers=headers, files={"file": ("bio.md", SAMPLE_TEXT.encode(), "text/markdown")})
    doc = r.json()
    r = client.post(f"/api/documents/{doc['id']}/ask", headers=headers, json={"question": "Compare photosynthesis and respiration across the document in detail"})
    assert r.status_code == 200
    assert r.json()["ai"]["provider"] == "live"
    assert r.json()["answer"].startswith("Fake RAG answer")
    assert r.json()["sources"][0]["index"] == 1
