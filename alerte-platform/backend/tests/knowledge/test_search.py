"""FTS5, recherche hybride (FixtureEmbedder + Chroma réel), mode dégradé, filtre d'article, empreinte, reprise d'embedding."""
from __future__ import annotations

import io

import httpx
import pytest
from sqlalchemy import func, select

from app.contracts import SearchFilters, SearchScope
from app.core.errors import Conflict
from app.knowledge import kbops
from app.knowledge.embedders import (
    EmbedderError,
    EmbedderUnavailable,
    FixtureEmbedder,
    OpenAICompatEmbedder,
    UnavailableEmbedder,
)
from app.knowledge.indexes import Fts5Index
from app.knowledge.models import Chunk, ChunkEmbedding, Document, KnowledgeBase
from app.knowledge.search import RRF_K, rrf
from tests.knowledge.conftest import LAW_FR, Env

TOPICS = [
    ("seismes", "Article {n} - Les séismes de forte magnitude déclenchent l'alerte sismique et l'évacuation des zones côtières."),
    ("cyclones", "Article {n} - Les cyclones tropicaux imposent la diffusion de bulletins météorologiques aux ports."),
    ("telecom", "Article {n} - Les opérateurs de téléphonie mobile diffusent les messages d'alerte par cell broadcast."),
    ("sante", "Article {n} - Les épidémies de choléra imposent une surveillance épidémiologique et la déclaration obligatoire."),
]


def corpus(env: Env, ws: str, kb: str, prefix: str = "") -> dict[str, str]:
    out = {}
    for name, tpl in TOPICS:
        body = "\n".join(tpl.format(n=n) + f" Détail {name} {prefix}{n}." for n in range(1, 6))
        _, vid = env.add_doc(ws, kb, f"{prefix}{name}.txt", body.encode(), embed=True, title=f"Texte {name}")
        out[name] = vid
    return out


def scope_of(env: Env, ws: str, kb: str) -> SearchScope:
    with env.session() as s:
        return SearchScope(ws, frozenset([kb]), frozenset(env.rt.ui_scope(s, ws, kb).document_version_ids))


def test_rrf_formula():
    s = rrf([["a", "b", "c"], ["c", "a"]])
    assert s["a"] == pytest.approx(1 / (RRF_K + 1) + 1 / (RRF_K + 2)) and RRF_K == 60
    assert s["c"] == pytest.approx(1 / (RRF_K + 3) + 1 / (RRF_K + 1)) and s["b"] == pytest.approx(1 / (RRF_K + 2))


def test_fts5_bm25_french_arabic_and_syntax_safety(env):
    ws = env.workspace()
    kb = env.kb(ws)
    env.add_doc(ws, kb, "a.txt", ("Article 1 - Les opérateurs de téléphonie diffusent les alertes. " + "x " * 80).encode())
    env.add_doc(ws, kb, "b.txt", ("المادة 1: يجب على المشغلين نشر التنبيه فورا. " + "ي " * 80).encode("utf-8"))
    sc = scope_of(env, ws, kb)
    fts = Fts5Index(env.factory)
    assert fts.query("opérateur diffuse alerte", sc, 5)             # racinisation FR
    assert fts.query("المشغل التنبيه", sc, 5)                        # arabe
    assert fts.query('"; DROP TABLE chunk; -- NEAR( * OR', sc, 5) == []  # syntaxe FTS non interprétée
    with env.session() as s:
        assert s.scalar(select(func.count()).select_from(Chunk)) >= 2
    assert fts.query("opérateurs", SearchScope(ws, frozenset(), frozenset()), 5) == []


def test_hybrid_search_real_chroma_with_fixture_embedder(env):
    ws = env.workspace()
    kb = env.kb(ws)
    corpus(env, ws, kb)
    sc = scope_of(env, ws, kb)
    hits = env.rt.search.search(sc, "diffusion d'alerte par les opérateurs de téléphonie mobile", k=5)
    assert hits and hits[0].doc_title == "Texte telecom"
    h = hits[0]
    assert h.signals["lexical"] and h.signals["dense"] and h.signals["degraded"] is False
    assert h.doc_code.startswith("DOC-") and h.page is None or h.page >= 1
    assert env.rt.vector_for(env.embedder.fingerprint.key()).count() == 20
    # filtre exact « Article N »
    art = env.rt.search.search(sc, "Article 3 sismique", k=3)
    assert any(x.article == "Article 3" and x.signals["article"] for x in art)
    only = env.rt.search.search(sc, "alerte", k=10, filters=SearchFilters(article="Article 2"))
    assert only and all(x.article == "Article 2" for x in only)
    typed = env.rt.search.search(sc, "alerte", k=10, filters=SearchFilters(doc_types=frozenset({"inexistant"})))
    assert typed == []


def test_deny_by_default_empty_scope(env):
    ws = env.workspace()
    kb = env.kb(ws)
    corpus(env, ws, kb)
    s = scope_of(env, ws, kb)
    assert env.rt.search.search(SearchScope(ws, frozenset(), s.document_version_ids), "alerte") == []
    assert env.rt.search.search(SearchScope(ws, s.kb_ids, frozenset()), "alerte") == []
    assert env.rt.search.search(s, "   ") == []


def test_degraded_mode_when_embedder_unreachable(env):
    ws = env.workspace()
    kb = env.kb(ws)
    corpus(env, ws, kb)
    sc = scope_of(env, ws, kb)

    class Down:
        fingerprint = env.embedder.fingerprint

        def ensure_fingerprint(self):
            raise EmbedderUnavailable("down")

        def embed(self, texts):
            raise EmbedderUnavailable("down")

    env.rt.search.embedder = Down()
    hits = env.rt.search.search(sc, "séismes alerte sismique", k=3)
    assert hits and all(h.signals["degraded"] is True and h.signals["dense"] is None and h.signals["lexical"] for h in hits)
    env.rt.search.embedder = UnavailableEmbedder()
    assert env.rt.search.search(sc, "séismes", k=3)[0].signals["degraded"] is True


def test_embedder_never_mixed_across_kbs_with_other_fingerprint(env):
    ws = env.workspace()
    kb1, kb2 = env.kb(ws, "K1"), env.kb(ws, "K2")
    corpus(env, ws, kb1)  # empreinte A (dim 64)
    other = FixtureEmbedder(32)
    env.rt.embedder = other
    env.embedder = other
    env.rt.search.embedder = other
    corpus(env, ws, kb2, prefix="b")   # empreinte B (dim 32)
    with env.session() as s:
        keys = {k: s.get(KnowledgeBase, k).embedder_key for k in (kb1, kb2)}
    assert keys[kb1] != keys[kb2]
    sc = SearchScope(ws, frozenset([kb1, kb2]), frozenset(env.rt.ui_scope(env.session(), ws, kb1).document_version_ids
                                                          | env.rt.ui_scope(env.session(), ws, kb2).document_version_ids))
    hits = env.rt.search.search(sc, "alerte sismique", k=20)
    assert hits and all(h.signals["degraded"] for h in hits)           # une KB n'a pas de vecteurs de cette empreinte
    assert all(h.signals["embedder_key"] == keys[kb2] for h in hits)
    assert {h.kb_id for h in hits if h.signals["dense"]} == {kb2}       # le vectoriel ne touche que la KB compatible


def test_embed_refuses_to_mix_fingerprints_unless_reembed(env):
    ws = env.workspace()
    kb = env.kb(ws)
    env.add_doc(ws, kb, "a.txt", LAW_FR.encode(), embed=True)
    k1 = env.embedder.fingerprint.key()
    env.rt.embedder = FixtureEmbedder(32)
    with pytest.raises(Conflict) as e:
        kbops.embed_kb(env.rt, None, kb)
    assert e.value.code == "kb.embedder_mismatch"
    with env.session() as s:
        assert s.get(KnowledgeBase, kb).embedder_key == k1
        assert {x.embedder_key for x in s.scalars(select(ChunkEmbedding))} == {k1}
    res = kbops.embed_kb(env.rt, None, kb, reembed=True)
    k2 = env.rt.embedder.fingerprint.key()
    assert res["embedded"] == 4 and k2 != k1
    with env.session() as s:
        assert {x.embedder_key for x in s.scalars(select(ChunkEmbedding))} == {k2}  # aucun vecteur de l'ancienne empreinte
        assert s.get(KnowledgeBase, kb).embedder_fingerprint["dimension"] == 32


def test_embedding_job_resumable_per_chunk(env):
    ws = env.workspace()
    kb = env.kb(ws)
    env.add_doc(ws, kb, "t.txt", "\n".join(f"Article {i} - Texte numéro {i} sur l'alerte." for i in range(1, 12)).encode())
    with env.session() as s:
        total = s.scalar(select(func.count()).select_from(Chunk))

    class Flaky(FixtureEmbedder):
        def __init__(self):
            super().__init__(64)
            self.fail_after = 2

        def embed(self, texts):
            if self.calls >= self.fail_after:
                raise EmbedderUnavailable("coupure simulée")
            return super().embed(texts)

    flaky = Flaky()
    env.rt.embedder = flaky
    with pytest.raises(EmbedderUnavailable):
        kbops.embed_kb(env.rt, None, kb)
    with env.session() as s:
        done = s.scalar(select(func.count()).select_from(ChunkEmbedding))
    assert 0 < done < total and done == 2 * env.settings.embed_batch_size   # lots déjà commités : conservés
    flaky.fail_after = 10**6
    calls_before = flaky.calls
    res = kbops.embed_kb(env.rt, None, kb)
    assert res["embedded"] == total - done                                  # les chunks déjà vectorisés sont sautés
    assert flaky.calls - calls_before == -(-(total - done) // env.settings.embed_batch_size)
    assert kbops.embed_kb(env.rt, None, kb)["embedded"] == 0               # idempotent


def test_openai_compat_client_batches_errors_and_fingerprint():
    seen = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = __import__("json").loads(req.content)
        seen.append((str(req.url), len(body["input"]), req.headers.get("authorization")))
        if body["input"][0] == "boom500":
            return httpx.Response(503)
        if body["input"][0] == "boom400":
            return httpx.Response(400, text="mauvais modèle")
        data = [{"index": i, "embedding": [float(i + 1), 0.0, 1.0]} for i in reversed(range(len(body["input"])))]
        return httpx.Response(200, json={"data": data})

    emb = OpenAICompatEmbedder("http://h:1/v1", "bge-m3", "SECRET-KEY", batch_size=2, retries=0,
                               transport=httpx.MockTransport(handler))
    assert emb.fingerprint.dimension == 0
    out = emb.embed(["a", "b", "c"])
    assert [n for _, n, _ in seen] == [2, 1] and seen[0][0] == "http://h:1/v1/embeddings" and seen[0][2] == "Bearer SECRET-KEY"
    assert len(out) == 3 and abs(sum(x * x for x in out[0]) - 1) < 1e-6          # ordre par `index`, normalisé
    assert emb.fingerprint.dimension == 3 and emb.fingerprint.model == "bge-m3" and emb.fingerprint.key()
    with pytest.raises(EmbedderUnavailable):
        emb.embed(["boom500"])
    with pytest.raises(EmbedderError) as e:
        emb.embed(["boom400"])
    assert "SECRET-KEY" not in str(e.value)

    def bad_dim(req):
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1.0, 2.0]}]})
    emb2 = OpenAICompatEmbedder("http://h", "m", transport=httpx.MockTransport(handler), retries=0)
    emb2.embed(["x"])
    emb2._client = httpx.Client(transport=httpx.MockTransport(bad_dim))
    with pytest.raises(EmbedderError, match="refus de mélanger"):
        emb2.embed(["y"])


def test_unreachable_server_raises_unavailable():
    def refuse(req):
        raise httpx.ConnectError("refused")
    emb = OpenAICompatEmbedder("http://nowhere", "m", retries=0, transport=httpx.MockTransport(refuse))
    with pytest.raises(EmbedderUnavailable):
        emb.embed(["x"])


def test_replaced_documents_excluded_by_default(env):
    ws = env.workspace()
    kb = env.kb(ws)
    ids = corpus(env, ws, kb)
    sc = scope_of(env, ws, kb)
    assert any(h.doc_title == "Texte seismes" for h in env.rt.search.search(sc, "séismes alerte sismique", 5))
    with env.session() as s:
        d = s.scalar(select(Document).where(Document.title == "Texte seismes"))
        d.validity = "replaced"
        s.commit()
    assert not any(h.doc_title == "Texte seismes" for h in env.rt.search.search(sc, "séismes alerte sismique", 10))
    assert any(h.doc_title == "Texte seismes" for h in env.rt.search_historic.search(sc, "séismes alerte sismique", 10))
    assert ids


def test_ui_scope_has_no_identity_parameters():
    import inspect

    from app.knowledge.runtime import KnowledgeRuntime
    assert list(inspect.signature(KnowledgeRuntime.ui_scope).parameters) == ["self", "session", "workspace_id", "kb_id", "purpose"]
    assert io  # (import utilisé par d'autres tests)
