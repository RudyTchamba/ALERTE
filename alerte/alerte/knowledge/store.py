"""The knowledge store: chunks on disk + hybrid search (keywords + meaning) with filters.

Files written by `alerte ingest` in the index folder:
  chunks.jsonl   one chunk per line (text + metadata)
  documents.json document metadata
  vectors.npy    optional, one normalised vector per chunk
  vectors.json   which embedding provider/model produced them
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

import numpy as np

from alerte import config
from alerte.knowledge.bm25 import BM25
from alerte.knowledge.embed import Embedder, get_embedder
from alerte.models import Chunk, DocumentMeta, SearchHit

log = logging.getLogger(__name__)


class KnowledgeStore:
    def __init__(self, chunks: list[Chunk], documents: dict[str, DocumentMeta],
                 vectors: np.ndarray | None = None, vector_info: dict | None = None):
        self.chunks = chunks
        self.documents = documents
        self.by_id = {c.chunk_id: c for c in chunks}
        self.bm25 = BM25(f"{c.title} {c.article} {c.text}" for c in chunks)
        self.vectors = vectors
        self.vector_info = vector_info or {}
        self._embedder: Embedder | None = None
        self._embedder_failed = False

    # ------------------------------------------------------------------ load / save
    @classmethod
    def load(cls, index_dir: Path | None = None) -> "KnowledgeStore":
        index_dir = Path(index_dir or config.settings.index_dir)
        cpath = index_dir / "chunks.jsonl"
        if not cpath.exists():
            raise FileNotFoundError(
                f"No knowledge index in {index_dir}. Run:  python -m alerte ingest")
        chunks = [Chunk.model_validate_json(line) for line in cpath.read_text(encoding="utf-8").splitlines() if line.strip()]
        docs_raw = json.loads((index_dir / "documents.json").read_text(encoding="utf-8"))
        documents = {d["doc_id"]: DocumentMeta(**d) for d in docs_raw}
        vectors, info = None, None
        vpath, ipath = index_dir / "vectors.npy", index_dir / "vectors.json"
        if vpath.exists() and ipath.exists():
            vectors = np.load(vpath)
            info = json.loads(ipath.read_text(encoding="utf-8"))
            if vectors.shape[0] != len(chunks):
                log.warning("vectors.npy does not match chunks; ignoring vectors (re-run ingest)")
                vectors, info = None, None
        return cls(chunks, documents, vectors, info)

    @staticmethod
    def save(index_dir: Path, chunks: list[Chunk], documents: Iterable[DocumentMeta],
             vectors: np.ndarray | None = None, vector_info: dict | None = None) -> None:
        index_dir.mkdir(parents=True, exist_ok=True)
        with (index_dir / "chunks.jsonl").open("w", encoding="utf-8") as fh:
            for c in chunks:
                fh.write(c.model_dump_json() + "\n")
        (index_dir / "documents.json").write_text(
            json.dumps([d.model_dump(mode="json") for d in documents], ensure_ascii=False, indent=1), encoding="utf-8")
        for name in ("vectors.npy", "vectors.json"):
            (index_dir / name).unlink(missing_ok=True)
        if vectors is not None:
            np.save(index_dir / "vectors.npy", vectors)
            (index_dir / "vectors.json").write_text(json.dumps(vector_info or {}), encoding="utf-8")

    # ------------------------------------------------------------------ search
    def _allowed(self, countries, institutions, collections, doc_types, include_fictional,
                 include_replaced, doc_ids) -> set[int] | None:
        if not any([countries, institutions, collections, doc_types, doc_ids]) and include_fictional and include_replaced:
            return None
        cset = set(countries or [])
        iset = set(institutions or [])
        colset = set(collections or [])
        tset = set(doc_types or [])
        dset = set(doc_ids or [])
        allowed = set()
        for i, c in enumerate(self.chunks):
            if not include_fictional and c.reliability == "fictional":
                continue
            if not include_replaced and c.status == "replaced":
                continue
            if cset and c.country not in cset:
                continue
            if colset and c.collection not in colset:
                continue
            if tset and c.doc_type not in tset:
                continue
            if dset and c.doc_id not in dset:
                continue
            # Institution wall: general texts (no institution tag) are open to all
            if iset and c.institutions and not (iset & set(c.institutions)):
                continue
            allowed.add(i)
        return allowed

    def _query_vector(self, query: str) -> np.ndarray | None:
        if self.vectors is None or self._embedder_failed:
            return None
        try:
            if self._embedder is None:
                self._embedder = get_embedder(self.vector_info.get("provider"), self.vector_info.get("model"))
            if self._embedder is None:
                return None
            return self._embedder.embed_query(query)
        except Exception as e:  # embedding server down -> keyword search only
            log.warning("Embedding unavailable (%s); using keyword search only", e)
            self._embedder_failed = True
            return None

    def search(self, query: str, k: int = 5, *, countries: list[str] | None = None,
               institutions: list[str] | None = None, collections: list[str] | None = None,
               doc_types: list[str] | None = None, doc_ids: list[str] | None = None,
               include_fictional: bool = False, include_replaced: bool = False) -> list[SearchHit]:
        allowed = self._allowed(countries, institutions, collections, doc_types,
                                include_fictional, include_replaced, doc_ids)
        if allowed is not None and not allowed:
            return []
        bm = self.bm25.scores(query, allowed)
        ranked_bm = sorted(bm.items(), key=lambda kv: -kv[1])[:100]
        qv = self._query_vector(query)
        if qv is None:
            top = ranked_bm[:k]
            best = top[0][1] if top else 1.0
            return [SearchHit(chunk=self.chunks[i], score=round(s / best, 4)) for i, s in top]
        sims = self.vectors @ qv
        if allowed is not None:
            mask = np.full(len(self.chunks), -np.inf, dtype=np.float32)
            idx = np.fromiter(allowed, dtype=np.int64)
            mask[idx] = sims[idx]
            sims = mask
        ranked_vec = [int(i) for i in np.argsort(-sims)[:100] if np.isfinite(sims[i])]
        # Reciprocal rank fusion of both rankings
        fused: dict[int, float] = {}
        for rank, (i, _) in enumerate(ranked_bm):
            fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        for rank, i in enumerate(ranked_vec):
            fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        top = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        best = top[0][1] if top else 1.0
        return [SearchHit(chunk=self.chunks[i], score=round(s / best, 4)) for i, s in top]

    # ------------------------------------------------------------------ helpers
    def doc_chunks(self, doc_id: str) -> list[Chunk]:
        return [c for c in self.chunks if c.doc_id == doc_id]

    def find_article(self, doc_id: str, article: str) -> list[Chunk]:
        art = article.lower().replace(".", "").strip()
        out = []
        for c in self.doc_chunks(doc_id):
            label = (c.article or "").lower().replace(".", "")
            if art and (label == art or label.startswith(art + " ") or art in label.split(" / ")):
                out.append(c)
        return out

    def stats(self) -> dict:
        by_col: dict[str, int] = {}
        for c in self.chunks:
            by_col[c.collection] = by_col.get(c.collection, 0) + 1
        return {"documents": len(self.documents), "chunks": len(self.chunks), "by_collection": by_col,
                "vectors": None if self.vectors is None else {**self.vector_info, "dim": int(self.vectors.shape[1])}}


_cache: dict[str, KnowledgeStore] = {}


def get_store(index_dir: Path | None = None, refresh: bool = False) -> KnowledgeStore:
    key = str(Path(index_dir or config.settings.index_dir).resolve())
    if refresh or key not in _cache:
        _cache[key] = KnowledgeStore.load(Path(key))
    return _cache[key]
