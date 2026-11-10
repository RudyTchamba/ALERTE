"""Quote checker: every cited article must exist in the library and contain what is quoted."""

from __future__ import annotations

from alerte.knowledge.store import KnowledgeStore
from alerte.models import Citation
from alerte.textutil import tokenize


def _overlap(quote: str, text: str) -> float:
    q = set(tokenize(quote))
    if not q:
        return 1.0
    return len(q & set(tokenize(text))) / len(q)


def check_citation(c: Citation, store: KnowledgeStore) -> Citation:
    c = c.model_copy()
    chunk = store.by_id.get(c.chunk_id) if c.chunk_id else None
    if chunk is None and c.doc_id:
        candidates = store.doc_chunks(c.doc_id)
        if not candidates:
            c.verified, c.check_note = False, f"document {c.doc_id} is not in the library"
            return c
        if c.article:
            by_art = store.find_article(c.doc_id, c.article)
            candidates = by_art or candidates
        chunk = max(candidates, key=lambda ch: _overlap(c.quote or c.article, ch.text + " " + ch.article))
        c.chunk_id = chunk.chunk_id
    if chunk is None:
        c.verified, c.check_note = False, "no document or passage given"
        return c
    if c.doc_id and chunk.doc_id != c.doc_id:
        c.verified, c.check_note = False, f"passage {chunk.chunk_id} belongs to {chunk.doc_id}, not {c.doc_id}"
        return c
    c.doc_id = chunk.doc_id
    if c.article:
        art = c.article.lower().replace(".", "")
        hay = (chunk.article + " " + chunk.text).lower().replace(".", "")
        if art.split()[-1] not in hay:
            c.verified, c.check_note = False, f"'{c.article}' not found in the cited passage"
            return c
    if c.quote:
        score = _overlap(c.quote, chunk.text)
        if score < 0.6:
            c.verified, c.check_note = False, f"quoted words not found in the passage (match {score:.0%})"
            return c
    c.verified = True
    c.check_note = "verified" + (" (source is a summary)" if chunk.reliability == "summary" else "")
    return c


def check_all(citations: list[Citation], store: KnowledgeStore) -> list[Citation]:
    return [check_citation(c, store) for c in citations]
