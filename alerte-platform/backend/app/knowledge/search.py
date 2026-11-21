"""Recherche hybride (doc 07 §7.3) : BM25 FTS5 + vecteurs, fusion RRF k=60, permissions strictes.

Garanties (testées) : (a) la portée n'est construite que par le backend ; (b) portée vide → aucun résultat ;
(c) pré-filtrage dans chaque moteur ; (d) revérification SQL de CHAQUE résultat contre la portée, violation signalée par
`on_scope_violation` ; (e) garde de rappel (rejeu exact NumPy) ; (f) `validity != replaced` par défaut.
"""
from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable, Sequence
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, sessionmaker

from ..contracts import Embedder, Hit, LexicalIndex, SearchFilters, SearchScope, VectorIndex
from .indexes import NumpyExactIndex, count_scope_chunks, scope_conditions
from .models import Chunk, Document, DocumentVersion, KnowledgeBase
from .textproc import article_in_query, article_number

log = logging.getLogger("alerte.knowledge.search")
security_log = logging.getLogger("alerte.security")
RRF_K = 60
CANDIDATES = 50

ViolationCallback = Callable[[dict[str, Any]], None]


def default_violation_callback(info: dict[str, Any]) -> None:
    security_log.error("SCOPE_VIOLATION", extra={"event": "SCOPE_VIOLATION", **{k: str(v) for k, v in info.items()}})


def rrf(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> dict[str, float]:
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return scores


class HybridSearchService:
    """Implémente `contracts.SearchService`. `with_replaced()` donne une variante pour exercices historiques."""

    def __init__(self, factory: sessionmaker[Session], lexical: LexicalIndex,
                 vector: VectorIndex | Callable[[str], VectorIndex] | None,
                 exact: bool, embedder: Embedder | None,
                 on_scope_violation: ViolationCallback | None = None, *, include_replaced: bool = False,
                 candidates: int = CANDIDATES) -> None:
        self._factory, self.lexical, self.vector, self.exact, self.embedder = factory, lexical, vector, exact, embedder
        self.on_scope_violation = on_scope_violation or default_violation_callback
        self.include_replaced, self.candidates = include_replaced, candidates

    def with_replaced(self) -> HybridSearchService:
        return HybridSearchService(self._factory, self.lexical, self.vector, self.exact, self.embedder,
                                   self.on_scope_violation, include_replaced=True, candidates=self.candidates)

    # ------------------------------------------------------------------ revérification SQL
    def _recheck(self, session: Session, ids: Sequence[str], scope: SearchScope, engine: str,
                 allowed_dvs: frozenset[str] | None, filters: SearchFilters | None) -> list[dict]:
        """Ids ordonnés → lignes autoritatives de la base, hors portée ou hors filtre écartées."""
        if not ids:
            return []
        q = select(Chunk, Document.code, Document.validity, Document.doc_type,
                   and_(*scope_conditions(scope)).label("in_scope")) \
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id) \
            .join(Document, Document.id == DocumentVersion.document_id).where(Chunk.id.in_(list(ids)))
        rows = {r[0].id: r for r in session.execute(q).all()}
        out: list[dict] = []
        for cid in ids:
            r = rows.get(cid)
            if r is None:  # entrée d'index périmée (chunk supprimé) : écartée
                log.warning("index périmé : chunk absent de la base", extra={"engine": engine})
                continue
            chunk, code, validity, doc_type, in_scope = r
            if not in_scope:
                self.on_scope_violation({"event": "SCOPE_VIOLATION", "engine": engine, "chunk_id": cid,
                                         "scope_hash": scope.scope_hash(), "workspace_id": scope.workspace_id,
                                         "purpose": scope.purpose, "seat_id": scope.seat_id})
                continue
            if validity == "replaced" and not self.include_replaced:
                continue
            if allowed_dvs is not None and chunk.document_version_id not in allowed_dvs:
                continue
            if filters and filters.article and article_number(chunk.article) != article_number(filters.article):
                continue
            if filters and filters.languages and (chunk.language or "") not in filters.languages:
                continue
            out.append({"chunk": chunk, "code": code})
        return out

    def _narrow(self, session: Session, scope: SearchScope, filters: SearchFilters | None) -> frozenset[str] | None:
        """Les filtres ne peuvent que RESTREINDRE : sous-ensemble de versions (type de document)."""
        if not filters or not filters.doc_types:
            return None
        q = select(DocumentVersion.id).join(Document, Document.id == DocumentVersion.document_id) \
            .where(DocumentVersion.id.in_(list(scope.document_version_ids)), Document.doc_type.in_(list(filters.doc_types)))
        return frozenset(session.scalars(q).all())

    def _article_list(self, session: Session, scope: SearchScope, key: str, limit: int) -> list[str]:
        q = select(Chunk.id, Chunk.article).join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id) \
            .join(Document, Document.id == DocumentVersion.document_id) \
            .where(*scope_conditions(scope), Chunk.article.is_not(None), Chunk.article.contains(key[:1])) \
            .order_by(Document.code, Chunk.document_version_id, Chunk.ordinal)
        if not self.include_replaced:
            q = q.where(Document.validity != "replaced")
        return [cid for cid, art in session.execute(q).all() if article_number(art) == key][:limit]

    # ------------------------------------------------------------------ recherche
    def search(self, scope: SearchScope, query: str, k: int = 5, *, filters: SearchFilters | None = None) -> list[Hit]:
        if scope.is_empty or not (query or "").strip() or k <= 0:
            return []  # deny-by-default
        cand = max(self.candidates, k)
        with self._factory() as s:
            allowed_dvs = self._narrow(s, scope, filters)
            if allowed_dvs is not None and not allowed_dvs:
                return []
            lex = self._recheck(s, [c for c, _ in self.lexical.query(query, scope, cand)], scope, "lexical",
                                allowed_dvs, filters)
            dense, degraded, exact_guard, key = self._dense(s, scope, query, cand, allowed_dvs, filters)
            art_key = (filters.article if filters and filters.article else None) or article_in_query(query)
            art = self._recheck(s, self._article_list(s, scope, article_number(art_key) or "", cand), scope, "article",
                                allowed_dvs, filters) if art_key else []
            lex_ids, dense_ids, art_ids = ([r["chunk"].id for r in lst] for lst in (lex, dense, art))
            fused = rrf([x for x in (lex_ids, dense_ids, art_ids) if x])
            by_id = {r["chunk"].id: r for r in lex + dense + art}
            if filters and filters.article:  # filtre exact : uniquement l'article demandé
                fused = {c: v for c, v in fused.items() if c in set(art_ids)}
            ranked = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
            hits = []
            for cid, score in ranked:
                c, code = by_id[cid]["chunk"], by_id[cid]["code"]
                hits.append(Hit(
                    chunk_id=c.id, document_version_id=c.document_version_id, kb_id=c.kb_id, doc_code=code,
                    doc_title=c.doc_title, article=c.article, page=c.page_start, text=c.text, score=score,
                    snippet=c.text[:300],
                    signals={"lexical": lex_ids.index(cid) + 1 if cid in lex_ids else None,
                             "dense": dense_ids.index(cid) + 1 if cid in dense_ids else None,
                             "article": cid in art_ids, "degraded": degraded, "exact_guard": exact_guard,
                             "embedder_key": key}))
            return hits

    def _dense(self, s: Session, scope: SearchScope, query: str, cand: int, allowed_dvs, filters):  # noqa: ANN001, ANN202
        """Renvoie (résultats revérifiés, dégradé, garde de rappel déclenchée, empreinte)."""
        if self.embedder is None or self.vector is None:
            return [], True, False, None
        vector_for = self.vector if (callable(self.vector) and not hasattr(self.vector, "query")) else None
        try:
            fp = self.embedder.ensure_fingerprint() if hasattr(self.embedder, "ensure_fingerprint") \
                else self.embedder.fingerprint
            qvec = self.embedder.embed([query])[0]
        except Exception as exc:  # noqa: BLE001 - serveur injoignable / mal configuré : lexical seul
            log.warning("embeddings indisponibles : recherche dégradée (%s)", type(exc).__name__)
            return [], True, False, None
        key = fp.key()
        compat = frozenset(s.scalars(select(KnowledgeBase.id).where(
            KnowledgeBase.id.in_(list(scope.kb_ids)), KnowledgeBase.workspace_id == scope.workspace_id,
            KnowledgeBase.embedder_key == key)).all())
        degraded = len(compat) < len(scope.kb_ids)  # certaines KB n'ont pas de vecteurs de CETTE empreinte : jamais mélangées
        if not compat:
            return [], True, False, key
        dscope = dataclasses.replace(scope, kb_ids=compat)
        vector = vector_for(key) if vector_for else self.vector
        exact = NumpyExactIndex(self._factory, key, self.include_replaced) if self.exact else None
        expected = min(cand, count_scope_chunks(s, dscope, embedder_key=key, include_replaced=self.include_replaced))
        guard = False
        try:
            raw = vector.query(qvec, dscope, cand)
        except Exception as exc:  # noqa: BLE001 - index défaillant : exact
            log.warning("index vectoriel en échec (%s) : rejeu exact", type(exc).__name__)
            raw, guard = [], True
        rows = self._recheck(s, [c for c, _ in raw], dscope, getattr(vector, "name", "vector"), allowed_dvs, filters)
        no_post_filter = not (filters and (filters.article or filters.languages))
        if (guard or (no_post_filter and len(rows) < expected)) and exact is not None \
                and getattr(vector, "name", "") != "numpy_exact":
            # garde de rappel : moins de résultats que la portée n'en contient → exact sur les embeddings SQLite
            guard = True
            rows = self._recheck(s, [c for c, _ in exact.query(qvec, dscope, cand)], dscope, "numpy_exact",
                                 allowed_dvs, filters)
        return rows, degraded, guard, key
