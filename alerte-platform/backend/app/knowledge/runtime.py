"""Objet de service du module : infrastructure (index, embedder, jobs) + services contractuels (CONTRACTS.md).

Enregistré sous `ctx.services["knowledge"]` ; `ctx.services["search"]` est son service de recherche hybride.
Les index (FTS5, Chroma) sont initialisés paresseusement ; SQLite reste la source de vérité.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ..contracts import SearchScope, VectorIndex
from ..core.blobs import BlobStore
from ..core.config import Settings
from ..core.jobs import JobRunner
from .embedders import UnavailableEmbedder
from .indexes import ChromaVectorIndex, Fts5Index, NumpyExactIndex, fts_count
from .models import (
    Chunk,
    ChunkEmbedding,
    Document,
    DocumentVersion,
    KBExpectedDocument,
    KBVersion,
    KBVersionItem,
    KnowledgeBase,
)
from .search import HybridSearchService, ViolationCallback

log = logging.getLogger("alerte.knowledge")


class KnowledgeRuntime:
    def __init__(self, settings: Settings, factory: sessionmaker[Session], blobs: BlobStore, jobs: JobRunner | None,
                 embedder: Any, *, vector_factory: Callable[[str], VectorIndex] | None = None,
                 on_scope_violation: ViolationCallback | None = None,
                 country_lookup: Callable[[Session, str, str], Any] | None = None) -> None:
        self.settings, self.factory, self.blobs, self.jobs, self.embedder = settings, factory, blobs, jobs, embedder
        self.country_lookup = country_lookup
        self._vector_factory = vector_factory
        self._vectors: dict[str, VectorIndex] = {}
        self._vlock = threading.Lock()
        self.lexical = Fts5Index(factory)
        self.violations: list[dict] = []

        def _on_violation(info: dict) -> None:
            self.violations.append(info)
            del self.violations[:-100]
            if on_scope_violation:
                on_scope_violation(info)
            else:
                from .search import default_violation_callback
                default_violation_callback(info)

        self.search = HybridSearchService(factory, self.lexical, self.vector_for, True, embedder, _on_violation)
        self.search_historic = self.search.with_replaced()

    # ------------------------------------------------------------------ index vectoriel
    def vector_for(self, embedder_key: str) -> VectorIndex:
        with self._vlock:
            if embedder_key not in self._vectors:
                self._vectors[embedder_key] = (self._vector_factory(embedder_key) if self._vector_factory
                                               else ChromaVectorIndex(self.settings.vector_dir, embedder_key))
            return self._vectors[embedder_key]

    def exact_for(self, embedder_key: str) -> NumpyExactIndex:
        return NumpyExactIndex(self.factory, embedder_key)

    # ------------------------------------------------------------------ portées (construites UNIQUEMENT ici, côté serveur)
    def ui_scope(self, session: Session, workspace_id: str, kb_id: str, *, purpose: str = "ui_preview") -> SearchScope:
        """Portée de l'interface : versions courantes (non retirées) de CETTE base de l'espace du jeton."""
        ids = session.scalars(select(DocumentVersion.id).join(Document, Document.current_version_id == DocumentVersion.id)
                              .where(Document.workspace_id == workspace_id, Document.kb_id == kb_id,
                                     DocumentVersion.status.in_(("ready", "needs_review")))).all()
        return SearchScope(workspace_id, frozenset([kb_id]), frozenset(ids), purpose)  # type: ignore[arg-type]

    def scope_from_grants(self, session: Session, workspace_id: str, kb_ids: set[str] | frozenset[str], *,
                          purpose: str = "agent", seat_id: str | None = None) -> SearchScope:
        """Pour les autres modules : versions PUBLIÉES des bases accordées (jamais depuis une entrée utilisateur/LLM)."""
        dvs = self.published_document_version_ids(session, workspace_id, kb_ids)
        return SearchScope(workspace_id, frozenset(kb_ids), frozenset(dvs), purpose, seat_id)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ services contractuels (CONTRACTS.md)
    def published_document_version_ids(self, session: Session, workspace_id: str, kb_ids) -> set[str]:  # noqa: ANN001
        out: set[str] = set()
        for kb_id in set(kb_ids):
            kb = session.scalar(select(KnowledgeBase.id).where(KnowledgeBase.id == kb_id,
                                                               KnowledgeBase.workspace_id == workspace_id))
            if not kb:
                continue
            latest = session.scalar(select(KBVersion.id).where(KBVersion.kb_id == kb_id)
                                    .order_by(KBVersion.version_no.desc()).limit(1))
            if latest:
                out.update(session.scalars(select(KBVersionItem.document_version_id)
                                           .where(KBVersionItem.kb_version_id == latest)).all())
        return out

    def kb_overview(self, session: Session, workspace_id: str, kb_id: str) -> dict:
        from ..core.errors import NotFound
        kb = session.scalar(select(KnowledgeBase).where(KnowledgeBase.id == kb_id,
                                                        KnowledgeBase.workspace_id == workspace_id))
        if kb is None:
            raise NotFound("base de connaissances introuvable", code="kb.not_found")
        ver = session.scalar(select(KBVersion).where(KBVersion.kb_id == kb_id).order_by(KBVersion.version_no.desc()).limit(1))
        n_docs = session.scalar(select(func.count()).select_from(Document).where(Document.kb_id == kb_id)) or 0
        n_chunks = session.scalar(select(func.count()).select_from(Chunk).where(Chunk.kb_id == kb_id)) or 0
        n_emb = session.scalar(select(func.count()).select_from(ChunkEmbedding).join(Chunk, Chunk.id == ChunkEmbedding.chunk_id)
                               .where(Chunk.kb_id == kb_id, ChunkEmbedding.embedder_key == kb.embedder_key)) \
            if kb.embedder_key else 0
        return {"id": kb.id, "code": kb.code, "name": kb.name, "kind": kb.kind, "domain": kb.domain,
                "languages": kb.languages or [], "status": kb.status, "country_id": kb.country_id,
                "published_version_no": ver.version_no if ver else None,
                "published_version_id": ver.id if ver else None, "documents": n_docs, "chunks": n_chunks,
                "embedded_chunks": n_emb or 0, "embedder_key": kb.embedder_key,
                "coverage": self.coverage(session, workspace_id, [kb_id])}

    @staticmethod
    def chunk_dict(c: Chunk, code: str | None = None, validity: str | None = None) -> dict:
        return {"id": c.id, "chunk_id": c.id, "page": c.page_start, "workspace_id": c.workspace_id, "kb_id": c.kb_id, "document_version_id": c.document_version_id,
                "doc_code": code, "doc_title": c.doc_title, "article": c.article, "section": c.section,
                "page_start": c.page_start, "page_end": c.page_end, "language": c.language, "text": c.text,
                "text_sha256": c.text_sha256, "evidence_tag": c.evidence_tag, "ordinal": c.ordinal,
                "validity": validity}

    def get_chunk(self, session: Session, chunk_id: str) -> dict | None:
        """Aucun contrôle de portée ici : l'appelant DOIT vérifier `chunk_in_scope` avant de montrer le texte."""
        row = session.execute(select(Chunk, Document.code, Document.validity)
                              .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id)
                              .join(Document, Document.id == DocumentVersion.document_id)
                              .where(Chunk.id == chunk_id)).first()
        return self.chunk_dict(*row) if row else None

    def chunk_in_scope(self, session: Session, chunk_id: str, scope: SearchScope) -> bool:
        if scope.is_empty:
            return False
        from .indexes import scope_conditions
        return session.scalar(select(Chunk.id).where(Chunk.id == chunk_id, *scope_conditions(scope))) is not None

    def coverage(self, session: Session, workspace_id: str, kb_ids) -> dict:  # noqa: ANN001
        rows = session.execute(select(KBExpectedDocument, Document.validity)
                               .outerjoin(Document, Document.id == KBExpectedDocument.matched_document_id)
                               .where(KBExpectedDocument.workspace_id == workspace_id,
                                      KBExpectedDocument.kb_id.in_(list(set(kb_ids))))).all()
        present, missing = 0, []
        for e, validity in rows:
            status = "replaced" if (e.matched_document_id and validity == "replaced") else \
                ("present" if e.matched_document_id else e.status)
            if status == "present":
                present += 1
            else:
                missing.append(e.title)
        n = len(rows)
        return {"ratio": (present / n) if n else None, "expected": n, "present": present, "missing": missing}

    def document_meta(self, session: Session, document_version_id: str) -> dict | None:
        row = session.execute(select(DocumentVersion, Document).join(Document, Document.id == DocumentVersion.document_id)
                              .where(DocumentVersion.id == document_version_id)).first()
        if not row:
            return None
        v, d = row
        return {"document_id": d.id, "document_version_id": v.id, "version_no": v.version_no, "code": d.code,
                "title": d.title, "type": d.doc_type, "jurisdiction": d.jurisdiction, "license": d.license_spdx,
                "redistribution": d.redistribution, "validity": d.validity, "kb_id": d.kb_id}

    # ------------------------------------------------------------------ /ready
    def readiness(self) -> dict:
        info: dict[str, Any] = {"ok": True}
        try:
            with self.factory() as s:
                info["fts5"] = True
                chunks = s.scalar(select(func.count()).select_from(Chunk)) or 0
                fts = fts_count(s)
                info.update(chunks=chunks, fts_rows=fts)
                if chunks != fts:
                    info["ok"] = False
                    info["error"] = "index FTS5 désynchronisé : lancer reindex"
        except Exception as exc:  # noqa: BLE001
            info.update(ok=False, fts5=False, error=str(exc)[:200])
        emb = self.embedder
        if isinstance(emb, UnavailableEmbedder):
            info["embedder"] = {"configured": False, "mode": "degraded (lexical seul)"}
        else:
            info["embedder"] = {"configured": True, "model": emb.fingerprint.model,
                                "fixture": emb.fingerprint.model.startswith("fixture")}
        info["scope_violations_seen"] = len(self.violations)
        return info
