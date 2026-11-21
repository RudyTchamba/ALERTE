"""Chunking conscient des articles (FR/EN/AR) : 1 chunk = 1 article ; sinon fenêtres ~512 tokens à 25 % de recouvrement."""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass

DEFAULT_PARAMS = {"strategy": "article-aware", "max_chars": 2000, "overlap_chars": 200,
                  "window_tokens": 512, "window_overlap": 0.25, "tokens_per_word": 1.3}

_NUM = r"(?:premier|1er|\d+(?:[.\-]\d+)*[A-Za-z]?(?:\s*(?:bis|ter|quater))?)"
ARTICLE_RE = re.compile(
    rf"^[ \t]*(?:#{{1,6}}[ \t]*)?(?:\*\*)?((?:ARTICLE|Article|Art\.?|ART\.?)[ \t]*{_NUM}"
    r"|المادة[ \t]*\(?(?:[0-9٠-٩]+|الأولى|الاولى)\)?)"
    r"(?:\*\*)?(?P<rest>[^\n]*)$", re.M)
SECTION_RE = re.compile(
    r"^[ \t]*(?:#{1,6}[ \t]*)?((?:CHAPITRE|Chapitre|CHAPTER|Chapter|TITRE|Titre|TITLE|Title|SECTION|Section|PARTIE|Partie|PART|Part)"
    r"[ \t]+[IVXLC\d]+[^\n]{0,120}|(?:الفصل|الباب|القسم)[ \t]+[^\n]{1,100})$", re.M)
_REF_CONT_LATIN = re.compile(r"^[a-zàâçéèêëîïôûùüÿœ]")           # « Article 12 de la loi… » : renvoi, pas un titre
_REF_CONT_AR = re.compile(r"^\s*(?:من|و|أو|في|بشأن|بموجب|من هذا)\b")


@dataclass
class ChunkDraft:
    text: str
    article: str | None
    section: str | None
    char_start: int
    char_end: int
    page_start: int | None = None
    page_end: int | None = None


def _is_heading(m: re.Match) -> bool:
    rest = m.group("rest").strip(" \t*:–—-.)/")
    raw = m.group("rest").lstrip()
    if not raw or raw[0] in ".:–—-)/*":
        return True
    if _REF_CONT_AR.match(raw):
        return False
    return not _REF_CONT_LATIN.match(rest if rest else raw)


def _split_long(text: str, base: int, max_chars: int, overlap: int) -> list[tuple[str, int, int]]:
    """Coupe par paragraphes, recouvrement `overlap` caractères (calé sur un espace). Renvoie (texte, début, fin)."""
    if len(text) <= max_chars:
        return [(text, base, base + len(text))]
    # unités = paragraphes, eux-mêmes découpés en phrases/mots si trop longs
    units: list[tuple[int, int]] = []
    for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]*)*", text):
        s, e = m.start(), m.end()
        while e - s > max_chars:
            cut = text.rfind(" ", s + max_chars // 2, s + max_chars)
            cut = cut if cut > s else s + max_chars
            units.append((s, cut))
            s = cut
        units.append((s, e))
    out: list[tuple[str, int, int]] = []
    cur_s = cur_e = None
    for s, e in units:
        if cur_s is None:
            cur_s, cur_e = s, e
        elif e - cur_s <= max_chars:
            cur_e = e
        else:
            out.append((text[cur_s:cur_e], base + cur_s, base + cur_e))
            ov = max(cur_e - overlap, cur_s)
            sp = text.find(" ", ov, cur_e)
            ov = sp + 1 if sp != -1 else ov
            cur_s, cur_e = (min(ov, s), e) if e - min(ov, s) <= max_chars else (s, e)
    if cur_s is not None:
        out.append((text[cur_s:cur_e], base + cur_s, base + cur_e))
    return out


def _windows(text: str, params: dict) -> list[tuple[str, int, int]]:
    words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    size = max(20, int(params["window_tokens"] / params["tokens_per_word"]))
    step = max(1, int(size * (1 - params["window_overlap"])))
    out = []
    i = 0
    while i < len(words):
        j = min(i + size, len(words))
        s, e = words[i][0], words[j - 1][1]
        out.append((text[s:e], s, e))
        if j >= len(words):
            break
        i += step
    return out


def chunk_pages(pages: list[tuple[int | None, str]], params: dict | None = None) -> list[ChunkDraft]:
    """`pages` = [(numéro de page|None, texte normalisé)]. Renvoie des brouillons de chunks avec pages et articles."""
    p = {**DEFAULT_PARAMS, **(params or {})}
    parts, starts, offset = [], [], 0
    for num, txt in pages:
        starts.append((offset, num))
        parts.append(txt)
        offset += len(txt) + 1
    full = "\n".join(parts)
    page_offsets = [s for s, _ in starts]

    def page_at(pos: int) -> int | None:
        i = bisect.bisect_right(page_offsets, max(0, pos)) - 1
        return starts[i][1] if i >= 0 else None

    heads = [m for m in ARTICLE_RE.finditer(full) if _is_heading(m)]
    sections = [(m.start(), " ".join(m.group(1).split())) for m in SECTION_RE.finditer(full)]
    sec_pos = [s for s, _ in sections]

    def section_at(pos: int) -> str | None:
        i = bisect.bisect_right(sec_pos, pos) - 1
        return sections[i][1][:300] if i >= 0 else None

    drafts: list[ChunkDraft] = []

    def emit(seg_text: str, seg_start: int, article: str | None, *, windows: bool = False) -> None:
        stripped = seg_text.strip()
        if not stripped:
            return
        lead = len(seg_text) - len(seg_text.lstrip())
        base = seg_start + lead
        pieces = _windows(stripped, p) if windows else _split_long(stripped, base, p["max_chars"], p["overlap_chars"])
        for t, s, e in pieces:
            if windows:
                s, e = base + s, base + e
            if t.strip():
                drafts.append(ChunkDraft(t.strip(), article, section_at(s), s, e, page_at(s), page_at(max(s, e - 1))))

    if len(heads) >= 2:
        if heads[0].start() > 0:
            emit(full[:heads[0].start()], 0, None)
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(full)
            # un titre de section placé juste avant le prochain article ne doit pas polluer l'article courant
            seg = full[m.start():end]
            for sp, _ in sections:
                if m.start() < sp < end and i + 1 < len(heads):
                    seg = full[m.start():sp]
                    break
            emit(seg, m.start(), " ".join(m.group(1).replace("**", "").replace("#", "").split()))
    else:
        emit(full, 0, None, windows=True)
    return drafts
