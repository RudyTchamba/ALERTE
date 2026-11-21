from __future__ import annotations

import io
import pathlib
import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.blobs import BlobStore
from app.core.config import Settings
from app.core.db import Base, make_engine, make_sessionmaker
from app.knowledge import kbops
from app.knowledge.embedders import FixtureEmbedder
from app.knowledge.indexes import NumpyExactIndex, create_fts
from app.knowledge.ingest import ingest_version
from app.knowledge.models import KnowledgeBase
from app.knowledge.runtime import KnowledgeRuntime
from app.migrate import import_all_models
from app.workspaces.models import Workspace


class Env:
    """Environnement sans HTTP : SQLite temporaire + runtime knowledge + FixtureEmbedder (déterministe, pas une IA)."""

    def __init__(self, tmp: pathlib.Path, *, chroma: bool = True, embedder=None) -> None:
        self.settings = Settings(data_dir=tmp / "data", log_json=False, log_level="WARNING", embed_provider="fixture",
                                 embed_batch_size=4)
        self.settings.ensure_dirs()
        self.engine = make_engine(self.settings.database_url)
        import_all_models()
        Base.metadata.create_all(self.engine)
        create_fts(self.engine)
        self.factory = make_sessionmaker(self.engine)
        self.embedder = embedder or FixtureEmbedder(64)
        vf = None if chroma else (lambda key: NumpyExactIndex(self.factory, key))
        self.rt = KnowledgeRuntime(self.settings, self.factory, BlobStore(self.settings.blobs_dir), None, self.embedder,
                                   vector_factory=vf)

    def workspace(self, name: str = "ws") -> str:
        with self.factory() as s:
            w = Workspace(name=name, slug=f"{name}-{uuid.uuid4().hex[:6]}")
            s.add(w)
            s.commit()
            return w.id

    def kb(self, ws: str, code: str = "KB1", **kw) -> str:
        with self.factory() as s:
            kb = KnowledgeBase(workspace_id=ws, code=code, name=code, kind="national", **kw)
            s.add(kb)
            s.commit()
            return kb.id

    def add_doc(self, ws: str, kb_id: str, filename: str, data: bytes, *, ingest: bool = True, embed: bool = False,
                **meta) -> tuple[str, str]:
        with self.factory() as s:
            kb = kbops.get_kb(s, ws, kb_id)
            sha, size, _ = kbops.store_upload(self.rt, s, io.BytesIO(data), filename)
            doc, ver = kbops.create_document(s, ws, kb, sha, size, filename, meta)
            s.commit()
            ids = (doc.id, ver.id)
        if ingest:
            ingest_version(self.rt, None, ids[1], embed=embed)
        return ids

    def publish(self, ws: str, kb_id: str):
        with self.factory() as s:
            kv = kbops.publish_kb(s, ws, kb_id, None)
            s.commit()
            return kv.id

    def session(self) -> Session:
        return self.factory()


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


@pytest.fixture
def env_np(tmp_path):
    return Env(tmp_path, chroma=False)


def make_pdf(pages_html: list[str]) -> bytes:
    from weasyprint import HTML
    body = "".join(f'<div style="page-break-after:always">{p}</div>' for p in pages_html)
    return HTML(string=f'<html><body style="font-family:DejaVu Sans, sans-serif">{body}</body></html>').write_pdf()


LAW_FR = """Loi n° 2021-12 relative à l'alerte précoce

Article 1er - Objet
La présente loi organise la diffusion des alertes aux populations par les opérateurs de téléphonie mobile.

Article 2 - Définitions
Au sens de la présente loi, on entend par alerte tout message officiel émis par l'autorité.

Article 33 - Obligations des opérateurs
Les opérateurs de téléphonie mobile sont tenus de diffuser sans délai toute alerte transmise par l'autorité nationale.
"""
