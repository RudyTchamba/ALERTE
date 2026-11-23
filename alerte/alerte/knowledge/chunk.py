"""Article-aware chunking.

The ITU reference code cuts every 256 words, which can split one article of law
in two. Here, legal texts are cut at each article / section heading (French,
English, Arabic), so a citation always points to a whole article. Long articles
are split with overlap; texts without articles fall back to headings, then to
word windows (same defaults as the reference: 256 words, 30 overlap).
"""

from __future__ import annotations

import re

ARTICLE_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
    r"((?:ARTICLE|Article|Art\.|ART\.)\s*(?:premier|1er|\d+[A-Za-z\-]*(?:\s*bis|\s*ter)?)"
    r"|(?:SECTION|Section|Sec\.|SEC\.)\s*\d+[A-Za-z\-]*"
    r"|(?:Chapter|CHAPTER|Chapitre|CHAPITRE)\s+[IVXLC\d]+"
    r"|المادة\s*\(?\d+\)?)"
    r"\b[\s.:\-–—)]*(.*)$"
)
HEADING_RE = re.compile(r"^\s*#{1,4}\s+(.+?)\s*$")


def _windows(words: list[str], size: int, overlap: int) -> list[list[str]]:
    if len(words) <= size:
        return [words]
    out, step = [], max(1, size - overlap)
    for start in range(0, len(words), step):
        part = words[start:start + size]
        if len(part) < 20 and out:
            out[-1].extend(part[overlap:] if overlap < len(part) else [])
            break
        out.append(part)
        if start + size >= len(words):
            break
    return out


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return [(label, body)] using article headings, else markdown headings."""
    lines = text.split("\n")
    has_articles = sum(1 for ln in lines if ARTICLE_RE.match(ln)) >= 2
    sections: list[tuple[str, list[str]]] = [("", [])]
    for ln in lines:
        label = None
        m = ARTICLE_RE.match(ln) if (has_articles or HEADING_RE.match(ln)) else None
        if m:
            label = " ".join(m.group(1).split())
            ln = m.group(2).strip(" *#")
        else:
            h = HEADING_RE.match(ln)
            if h:
                label = h.group(1).strip(" *#")
                ln = ""
        if label is not None:
            sections.append((label, [ln] if ln else []))
        else:
            sections[-1][1].append(ln)
    out = []
    for label, body in sections:
        body_text = "\n".join(body).strip()
        if body_text or label:
            out.append((label, body_text))
    return out


def chunk_document(text: str, max_words: int = 320, overlap: int = 30,
                   window: int = 256) -> list[tuple[str, str]]:
    """Return [(article_label, chunk_text)]."""
    sections = split_sections(text)
    if len(sections) <= 1:
        words = text.split()
        return [("", " ".join(w)) for w in _windows(words, window, overlap) if w]
    chunks: list[tuple[str, str]] = []
    pending_label, pending_words = None, []
    for label, body in sections:
        words = body.split()
        # Merge tiny heading-only sections into the next one (keeps context)
        if len(words) < 12 and not ARTICLE_RE.match(label or "") and label:
            pending_label = f"{pending_label} / {label}" if pending_label else label
            pending_words.extend(words)
            continue
        if pending_label is not None:
            if label and ARTICLE_RE.match(label):
                # keep the article as the citation label; carry the heading text into the body
                words = pending_label.split() + pending_words + words
            else:
                label = f"{pending_label} / {label}" if label else pending_label
                words = pending_words + words
            pending_label, pending_words = None, []
        if not words:
            continue
        for part in _windows(words, max_words, overlap):
            chunks.append((label, " ".join(part)))
    if pending_label is not None and pending_words:
        chunks.append((pending_label, " ".join(pending_words)))
    return chunks


def article_ref(label: str) -> str:
    """Short article reference ('Article 33', 'Section 4') from a heading label."""
    m = ARTICLE_RE.match(label or "")
    if m:
        return " ".join(m.group(1).split())
    return (label or "")[:80]
