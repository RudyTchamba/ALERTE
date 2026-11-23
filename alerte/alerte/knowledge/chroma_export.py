"""Export the ALERTE knowledge index into ChromaDB, in the format of the ITU reference code.

This is how our knowledge base is contributed to the ITU AI for Good Lab: the
reference simulation (simulation/server/knowledge/kb.py) reads ChromaDB
collections with cosine distance and string metadata.

  # separate collection next to the reference KB (any embedding model)
  python -m alerte export-chroma --chroma-dir ../simulation/data/chromadb --collection alerte_kb

  # merge into the reference collection: must use the reference embedding model
  python -m alerte export-chroma --collection kb_main --embed ollama --embed-model nomic-embed-text
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from alerte.knowledge.embed import get_embedder
from alerte.knowledge.store import KnowledgeStore

log = logging.getLogger(__name__)


def export_to_chroma(store: KnowledgeStore, chroma_dir: Path, collection: str = "alerte_kb",
                     embed_provider: str | None = None, embed_model: str | None = None,
                     reset: bool = False, include_itu_reference: bool = False) -> int:
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError as e:
        raise RuntimeError("chromadb is not installed: pip install -r requirements-full.txt") from e

    chunks = [c for c in store.chunks if include_itu_reference or c.collection != "ITUREF"]
    if not chunks:
        return 0
    if embed_provider:
        emb = get_embedder(embed_provider, embed_model)
        if emb is None:
            raise RuntimeError("An embedding provider is required to export to ChromaDB")
        vectors = emb.embed([f"{c.title}. {c.article}. {c.text}" for c in chunks])
    elif store.vectors is not None:
        idx = {c.chunk_id: i for i, c in enumerate(store.chunks)}
        vectors = np.stack([store.vectors[idx[c.chunk_id]] for c in chunks])
    else:
        raise RuntimeError("The index has no vectors. Re-run ingest with --embed, or pass --embed here.")

    client = chromadb.PersistentClient(path=str(chroma_dir), settings=ChromaSettings(anonymized_telemetry=False))
    if reset:
        try:
            client.delete_collection(collection)
        except Exception:
            pass
    col = client.get_or_create_collection(name=collection, metadata={"hnsw:space": "cosine"})
    now = datetime.now(timezone.utc).isoformat()
    per_doc: dict[str, int] = {}
    for c in chunks:
        per_doc[c.doc_id] = per_doc.get(c.doc_id, 0) + 1
    seen: dict[str, int] = {}
    metas = []
    for c in chunks:
        seen[c.doc_id] = seen.get(c.doc_id, 0) + 1
        doc = store.documents.get(c.doc_id)
        metas.append({
            # keys used by the ITU reference code
            "source_file": Path(doc.file).name if doc and doc.file else c.doc_id,
            "source_type": {"law": "policy_document", "decree": "policy_document", "strategy": "national_strategy",
                            "standard": "standards_document"}.get(c.doc_type, "international_org_report"),
            "country": c.country,
            "chunk_index": str(seen[c.doc_id] - 1),
            "total_chunks": str(per_doc[c.doc_id]),
            "ingested_at": now,
            "document_category": f"ALERTE_{c.collection}",
            # ALERTE keys
            "doc_id": c.doc_id, "title": c.title[:300], "article": c.article, "reliability": c.reliability,
            "doc_type": c.doc_type, "language": c.language, "institutions": ",".join(c.institutions),
            "topics": ",".join(c.topics), "url": c.url, "contributor": "ALERTE team (ITU AI for Good UAE hackathon)",
        })
    for i in range(0, len(chunks), 1000):
        sl = slice(i, i + 1000)
        col.upsert(ids=[c.chunk_id for c in chunks[sl]], documents=[c.text for c in chunks[sl]],
                   embeddings=vectors[sl].tolist(), metadatas=metas[sl])
    log.info("exported %d passages to %s / %s", len(chunks), chroma_dir, collection)
    return len(chunks)
