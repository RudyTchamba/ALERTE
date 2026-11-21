"""Adaptateurs d'index : FTS5 (BM25), NumPy exact (sur SQLite), ChromaDB (HNSW persistant).

Chaque adaptateur PRÉ-FILTRE sur la portée (SQL / `where` Chroma). Le service de recherche revérifie néanmoins
chaque résultat en SQL (doc 07 §7.3) : les adaptateurs ne sont jamais la frontière de sécurité.

Expérience Chroma (voir `tests/knowledge/test_chroma_filter.py`, chromadb 1.5.9, HNSW local) : le filtre `where` sur
métadonnées est appliqué AVANT la recherche (pré-filtrage par liste d'ids autorisés) ; aucun résultat hors filtre n'a
été observé. Le rappel sous une portée de 1 % du corpus est mesuré par ce test et protégé de toute façon par la garde
de rappel du service (rejeu exact NumPy si moins de résultats que prévu).
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from sqlalchemy import bindparam, select, text
from sqlalchemy.orm import Session, sessionmaker

from ..contracts import SearchScope, VectorRecord
from .embedders import blob_to_vec
from .models import Chunk, ChunkEmbedding, Document, DocumentVersion
from .textproc import analyze

log = logging.getLogger("alerte.knowledge.index")

FTS_DDL = ("CREATE VIRTUAL TABLE IF NOT EXISTS chunk_fts USING fts5("
           "search_text, doc_title, article, chunk_id UNINDEXED, kb_id UNINDEXED, document_version_id UNINDEXED, "
           "workspace_id UNINDEXED, tokenize='unicode61 remove_diacritics 2')")


def fts5_available(conn) -> bool:  # noqa: ANN001
    try:
        return bool(conn.exec_driver_sql("SELECT sqlite_compileoption_used('ENABLE_FTS5')").scalar())
    except Exception:  # noqa: BLE001
        return False


def create_fts(engine) -> None:  # noqa: ANN001
    with engine.begin() as conn:
        if not fts5_available(conn):
            raise RuntimeError("SQLite sans FTS5 : le module knowledge ne peut pas démarrer")
        conn.exec_driver_sql(FTS_DDL)


def fts_insert(session: Session, rows: Sequence[dict]) -> None:
    if rows:
        session.execute(text("INSERT INTO chunk_fts(search_text, doc_title, article, chunk_id, kb_id, document_version_id, "
                             "workspace_id) VALUES (:search_text, :doc_title, :article, :chunk_id, :kb_id, "
                             ":document_version_id, :workspace_id)"), list(rows))


def fts_delete_kb(session: Session, kb_id: str) -> None:
    session.execute(text("DELETE FROM chunk_fts WHERE kb_id = :kb"), {"kb": kb_id})


def fts_count(session: Session) -> int:
    return session.execute(text("SELECT count(*) FROM chunk_fts")).scalar() or 0


def chunk_fts_row(c: Chunk) -> dict:
    return {"search_text": c.search_text, "doc_title": analyze(c.doc_title), "article": analyze(c.article or ""),
            "chunk_id": c.id, "kb_id": c.kb_id, "document_version_id": c.document_version_id,
            "workspace_id": c.workspace_id}


def scope_conditions(scope: SearchScope) -> list:
    """Conditions SQL de portée sur `chunk` (ET entre kb_ids et document_version_ids, + espace de travail)."""
    return [Chunk.workspace_id == scope.workspace_id, Chunk.kb_id.in_(list(scope.kb_ids)),
            Chunk.document_version_id.in_(list(scope.document_version_ids))]


def count_scope_chunks(session: Session, scope: SearchScope, *, embedder_key: str | None = None,
                       include_replaced: bool = False) -> int:
    if scope.is_empty:
        return 0
    from sqlalchemy import func
    q = select(func.count()).select_from(Chunk).join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id) \
        .join(Document, Document.id == DocumentVersion.document_id).where(*scope_conditions(scope))
    if embedder_key:
        q = q.join(ChunkEmbedding, ChunkEmbedding.chunk_id == Chunk.id).where(ChunkEmbedding.embedder_key == embedder_key)
    if not include_replaced:
        q = q.where(Document.validity != "replaced")
    return session.scalar(q) or 0


class Fts5Index:
    """`contracts.LexicalIndex` : BM25 sur `search_text` ; pré-filtrage de portée dans le SQL."""

    name = "fts5"

    def __init__(self, factory: sessionmaker[Session], include_replaced: bool = False) -> None:
        self._factory = factory
        self.include_replaced = include_replaced

    @staticmethod
    def match_expr(query: str) -> str | None:
        toks = list(dict.fromkeys(analyze(query, for_query=True).split()))[:40]
        return " OR ".join('"' + t.replace('"', '""') + '"' for t in toks) or None

    def query(self, text_: str, scope: SearchScope, k: int) -> list[tuple[str, float]]:
        expr = self.match_expr(text_)
        if scope.is_empty or not expr:
            return []
        sql = ("SELECT f.chunk_id, bm25(chunk_fts, 1.0, 2.0, 3.0) AS s FROM chunk_fts f "
               "JOIN chunk c ON c.id = f.chunk_id JOIN document_version dv ON dv.id = c.document_version_id "
               "JOIN document d ON d.id = dv.document_id "
               "WHERE chunk_fts MATCH :q AND c.workspace_id = :ws AND c.kb_id IN :kbs "
               "AND c.document_version_id IN :dvs"
               + ("" if self.include_replaced else " AND d.validity != 'replaced'")
               + " ORDER BY s LIMIT :k")
        stmt = text(sql).bindparams(bindparam("kbs", expanding=True), bindparam("dvs", expanding=True))
        with self._factory() as s:
            rows = s.execute(stmt, {"q": expr, "ws": scope.workspace_id, "kbs": list(scope.kb_ids),
                                    "dvs": list(scope.document_version_ids), "k": k}).all()
        return [(r[0], -float(r[1])) for r in rows]


class NumpyExactIndex:
    """`contracts.VectorIndex` exact : lit les embeddings SQLite (source de vérité) restreints à la portée."""

    name = "numpy_exact"

    def __init__(self, factory: sessionmaker[Session], embedder_key: str, include_replaced: bool = False) -> None:
        self._factory, self.embedder_key, self.include_replaced = factory, embedder_key, include_replaced

    def upsert(self, records: Sequence[VectorRecord]) -> None:  # SQLite est la source : rien à copier
        return None

    def delete(self, chunk_ids: Sequence[str]) -> None:
        return None

    def reset(self) -> None:
        return None

    def query(self, vector: Sequence[float], scope: SearchScope, k: int) -> list[tuple[str, float]]:
        if scope.is_empty:
            return []
        q = select(ChunkEmbedding.chunk_id, ChunkEmbedding.vector, ChunkEmbedding.dim) \
            .join(Chunk, Chunk.id == ChunkEmbedding.chunk_id) \
            .join(DocumentVersion, DocumentVersion.id == Chunk.document_version_id) \
            .join(Document, Document.id == DocumentVersion.document_id) \
            .where(ChunkEmbedding.embedder_key == self.embedder_key, *scope_conditions(scope))
        if not self.include_replaced:
            q = q.where(Document.validity != "replaced")
        with self._factory() as s:
            rows = s.execute(q).all()
        qv = np.asarray(vector, dtype=np.float32)
        ids, vecs = [], []
        for cid, blob, dim in rows:
            if dim == qv.shape[0]:  # dimensions différentes = empreinte différente : jamais comparées
                ids.append(cid)
                vecs.append(blob_to_vec(blob))
        if not ids:
            return []
        m = np.vstack(vecs)
        norms = np.linalg.norm(m, axis=1) * (np.linalg.norm(qv) or 1.0)
        sims = (m @ qv) / np.where(norms == 0, 1.0, norms)
        order = np.argsort(-sims, kind="stable")[:k]
        return [(ids[i], float(sims[i])) for i in order]


class ChromaVectorIndex:
    """`contracts.VectorIndex` sur ChromaDB persistant (une collection par empreinte d'embedder, distance cosinus)."""

    name = "chroma"
    _lock = threading.RLock()

    def __init__(self, path: Path, embedder_key: str) -> None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        Path(path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(path), settings=ChromaSettings(anonymized_telemetry=False))
        self.collection_name = f"alerte_chunks_{embedder_key}"
        self._col = self._get()

    def _get(self):  # noqa: ANN202
        return self._client.get_or_create_collection(self.collection_name, metadata={"hnsw:space": "cosine"})

    def upsert(self, records: Sequence[VectorRecord]) -> None:
        recs = list(records)
        with self._lock:
            for i in range(0, len(recs), 500):
                b = recs[i:i + 500]
                self._col.upsert(ids=[r.chunk_id for r in b], embeddings=[list(r.vector) for r in b],
                                 metadatas=[{"kb_id": r.kb_id, "document_version_id": r.document_version_id,
                                             "workspace_id": getattr(r, "workspace_id", "")} for r in b])

    def delete(self, chunk_ids: Sequence[str]) -> None:
        ids = list(chunk_ids)
        with self._lock:
            for i in range(0, len(ids), 500):
                self._col.delete(ids=ids[i:i + 500])

    def reset(self) -> None:
        with self._lock:
            try:
                self._client.delete_collection(self.collection_name)
            except Exception:  # noqa: BLE001 - collection absente
                pass
            self._col = self._get()

    def count(self) -> int:
        with self._lock:
            return self._col.count()

    def query(self, vector: Sequence[float], scope: SearchScope, k: int) -> list[tuple[str, float]]:
        if scope.is_empty:
            return []
        where = {"$and": [{"kb_id": {"$in": sorted(scope.kb_ids)}},
                          {"document_version_id": {"$in": sorted(scope.document_version_ids)}}]}
        with self._lock:
            n = self._col.count()
            if n == 0:
                return []
            res = self._col.query(query_embeddings=[list(vector)], n_results=min(k, n), where=where,
                                  include=["distances"])
        return [(i, 1.0 - float(d)) for i, d in zip(res["ids"][0], res["distances"][0], strict=False)]
