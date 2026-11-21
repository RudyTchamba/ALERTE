"""Recherche négative (doc 09 §9.5) : requêtes standardisées dans chaque langue de la KB, portée ANALYSTE, contre-preuve
si hit fort. Une recherche lexicale peut manquer un synonyme : d'où la revue humaine et l'état `reviewed_complete`."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from ..contracts import SearchFilters, SearchScope
from . import constants as C


@dataclass
class NegativeResult:
    action_code: str | None
    queries: list[dict[str, str]]
    languages: list[str]
    kb_ids: list[str]
    corpus_documents: int
    coverage: float | None
    coverage_missing: list[str]
    top_hits: list[dict[str, Any]]
    verdict: str                              # no_hit | weak_hit | strong_hit
    counter_hits: list[dict[str, Any]] = field(default_factory=list)
    query_key: str = ""

    def statement(self, lang: str = "fr") -> str:
        cov = "n/d" if self.coverage is None else f"{self.coverage:.0%}"
        if lang == "fr":
            return (f"Non trouvé dans le corpus ({len(self.kb_ids)} base(s), {self.corpus_documents} documents ; langues "
                    f"{', '.join(self.languages) or 'n/d'} ; {len(self.queries)} requêtes) ; couverture documentaire attendue : {cov}.")
        return (f"Not found in the corpus ({len(self.kb_ids)} KB, {self.corpus_documents} documents; languages "
                f"{', '.join(self.languages) or 'n/a'}; {len(self.queries)} queries); expected-document coverage: {cov}.")


def build_queries(label: str, languages: list[str], synonyms: dict[str, list[str]] | None = None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for lang in languages:
        for tpl in C.NEG_QUERY_TEMPLATES.get(lang, ["{label}"]):
            out.append({"lang": lang, "q": tpl.format(label=label)})
        for syn in (synonyms or {}).get(lang, []):
            out.append({"lang": lang, "q": syn})
    seen, uniq = set(), []
    for q in out:
        if (q["lang"], q["q"]) not in seen:
            seen.add((q["lang"], q["q"]))
            uniq.append(q)
    return uniq


def run_negative_search(search: Any, scope: SearchScope, *, action_code: str | None, label: str, languages: list[str],
                        corpus_documents: int, coverage: float | None, coverage_missing: list[str],
                        synonyms: dict[str, list[str]] | None = None, cfg: dict[str, Any] | None = None) -> NegativeResult:
    cfg = {**C.DEFAULT_NEG_CONFIG, **(cfg or {})}
    queries = build_queries(label, languages, synonyms)
    best: dict[str, dict[str, Any]] = {}
    if not scope.is_empty:
        for q in queries:
            filters = SearchFilters(languages=frozenset({q["lang"]}))
            for h in search.search(scope, q["q"], k=int(cfg["k"]), filters=filters):
                rec = {"chunk_id": h.chunk_id, "document_version_id": h.document_version_id, "kb_id": h.kb_id,
                       "doc_code": h.doc_code, "article": h.article, "score": round(float(h.score), 4), "query": q["q"],
                       "snippet": (h.snippet or h.text or "")[:300]}
                if h.chunk_id not in best or rec["score"] > best[h.chunk_id]["score"]:
                    best[h.chunk_id] = rec
    top = sorted(best.values(), key=lambda r: -r["score"])[:5]
    strong = [r for r in top if r["score"] >= cfg["strong_score"]]
    verdict = "strong_hit" if strong else ("weak_hit" if top and top[0]["score"] >= cfg["weak_score"] else "no_hit")
    key = hashlib.sha256(f"{action_code}|{scope.scope_hash()}|{sorted((q['lang'], q['q']) for q in queries)}".encode()).hexdigest()
    return NegativeResult(action_code, queries, languages, sorted(scope.kb_ids), corpus_documents, coverage,
                          coverage_missing, top, verdict, strong, key)
