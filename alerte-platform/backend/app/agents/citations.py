"""CitationChecker déterministe (doc 08 §8.5). Fonction publique `check_citations`, réutilisable pour les décisions humaines."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ..contracts import SearchScope

MIN_QUOTE_CHARS = 20
_TO_CONFIRM = re.compile(r"to\s*confirm|à\s*confirmer|a\s*confirmer|\btbc\b|\btbd\b", re.I)
_ART_PREFIX = re.compile(r"^(articles?|art)\b\.?\s*", re.I)


@dataclass
class CitationResult:
    chunk_id: str
    check: str  # pass|fail
    reason: str  # ok | unknown_chunk | out_of_scope | not_in_retrieval_set | article_mismatch | article_to_confirm | ...
    article: str | None = None
    quote: str = ""

    @property
    def passed(self) -> bool:
        return self.check == "pass"

    def as_basis(self) -> dict[str, Any]:
        return {"chunk_id": self.chunk_id, "article": self.article, "quote": self.quote, "check": self.check,
                "reason": self.reason}


def normalize_text(s: str) -> str:
    """NFC, casse, ponctuation → espace, caractères invisibles retirés, espaces réduits."""
    s = unicodedata.normalize("NFC", s or "").casefold()
    out = []
    for ch in s:
        cat = unicodedata.category(ch)
        if cat == "Cf" or cat == "Cc" and ch not in "\n\t":
            continue
        out.append(" " if cat.startswith("P") or cat.startswith("Z") or ch in "\n\t" else ch)
    return " ".join("".join(out).split())


def normalize_article(a: Any) -> str:
    s = normalize_text(str(a)) if a is not None else ""
    s = _ART_PREFIX.sub("", s).strip()
    return s


def _chunk_text(chunk: Mapping[str, Any]) -> str:
    return str(chunk.get("text") or chunk.get("content") or chunk.get("chunk_text") or "")


def check_citations(knowledge: Any, session: Any, citations: Sequence[Mapping[str, Any]], *, scope: SearchScope,
                    retrieval_set: Collection[str] | None, allow_replaced: bool = False) -> list[CitationResult]:
    """Contrôle chaque citation `{chunk_id, article, quote}`.

    `retrieval_set=None` désactive le contrôle n°3 (à n'utiliser que si l'appelant n'a pas d'ensemble de
    récupération, ex. soumission humaine dont la recherche n'est pas suivie)."""
    results: list[CitationResult] = []
    for c in citations:
        cid = str(c.get("chunk_id") or "")
        article, quote = c.get("article"), str(c.get("quote") or "")
        res = CitationResult(cid, "fail", "ok", article if article is None else str(article), quote)

        def fail(reason: str, res: CitationResult = res) -> CitationResult:
            res.check, res.reason = "fail", reason
            return res

        if not cid:
            results.append(fail("unknown_chunk"))
            continue
        chunk = knowledge.get_chunk(session, cid)
        if not chunk:
            results.append(fail("unknown_chunk"))
            continue
        if not knowledge.chunk_in_scope(session, cid, scope):
            results.append(fail("out_of_scope"))
            continue
        if retrieval_set is not None and cid not in retrieval_set:
            results.append(fail("not_in_retrieval_set"))
            continue
        cited = "" if article is None else str(article)
        if cited and _TO_CONFIRM.search(cited):
            results.append(fail("article_to_confirm"))
            continue
        real = chunk.get("article")
        real_s = "" if real is None else str(real)
        if real_s and _TO_CONFIRM.search(real_s):
            real_s = ""
        if normalize_article(cited) != normalize_article(real_s):
            results.append(fail("article_mismatch"))
            continue
        nq = normalize_text(quote)
        if len(nq) < MIN_QUOTE_CHARS:
            results.append(fail("quote_too_short"))
            continue
        if nq not in normalize_text(_chunk_text(chunk)):
            results.append(fail("quote_not_in_chunk"))
            continue
        validity = chunk.get("validity") or chunk.get("document_validity") or chunk.get("doc_validity")
        if validity is None and chunk.get("document_version_id") and hasattr(knowledge, "document_meta"):
            meta = knowledge.document_meta(session, chunk["document_version_id"]) or {}
            validity = meta.get("validity")
        if validity == "replaced" and not allow_replaced:
            results.append(fail("document_replaced"))
            continue
        res.check, res.reason = "pass", "ok"
        results.append(res)
    return results
