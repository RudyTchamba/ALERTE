"""Projet de texte vérifiable : citations contrôlées, ancrage dans le registre, vérification publique par empreinte."""
from __future__ import annotations

import json

from sqlalchemy import text

from app.contracts import RawCompletion
from tests.gaps import helpers as H
from tests.gaps.conftest import API

ART = "Le ministre chargé de la protection civile organise les secours en cas de catastrophe sur tout le territoire."


class Provider:
    def __init__(self, replies):  # noqa: ANN001
        self.replies, self.calls = list(replies), []

    def complete(self, messages, *, schema=None, temperature=0.0, max_tokens=None):  # noqa: ANN001, ANN201
        self.calls.append(list(messages))
        return RawCompletion(text=json.dumps(self.replies.pop(0)), model="m", provider="fake", tokens_in=1, tokens_out=1,
                             ms=1, request_sha256="x", endpoint="local")


def draft(chunk_id: str = "CH1", article: str | None = "1") -> dict:
    return {"title": "Avis de crue", "article_label": "Article 1er",
            "article_text": "La Direction de la protection civile émet l'avis de crue dans un délai d'une heure.",
            "explanation": "L'exercice a montré que personne n'émet l'avis de crue.",
            "citations": [{"chunk_id": chunk_id, "article": article}]}


def setup(env):  # noqa: ANN001, ANN201
    env.knowledge.add("CH1", "DV1", text=ART)
    env.knowledge.chunk_in_scope = lambda session, cid, scope: cid in env.knowledge.chunks
    env.search.add("CH1", "DV1", ["action"])
    snap = H.snapshot([H.inject("inj-001", 1, ["a1"], ["life_risk"])], [H.action("a1")])
    env.put_exercise("EXR", snap)
    env.detect("EXR")
    return next(g for g in env.gaps(exercise="EXR") if g["code"] == "G1")


def test_draft_is_cited_anchored_and_publicly_verifiable(env):
    gap = setup(env)
    prov = Provider([draft("CH-INVENTE"), draft()])
    env.ctx.services["reform_llm"] = prov
    r = env.client.post(f"{API}/gaps/{gap['id']}/reform-drafts", headers=env.owner)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["verified"] is True and d["content"]["citations"][0]["check"] == "pass"
    assert "failed the check" in prov.calls[1][-1].content  # la relance donne le motif d'échec
    assert d["content"]["citations"][0]["quote"] == ART  # passage recopié du corpus par le système
    assert d["anchors"]["ledger_head_seq"] >= 1 and len(d["anchors"]["ledger_head_hash"]) == 64
    assert d["anchors"]["gap_fingerprint"] == gap["fingerprint"]
    assert env.client.get(f"{API}/gaps/{gap['id']}/reform-drafts", headers=env.owner).json()[0]["sha256"] == d["sha256"]

    v = env.client.get(f"{API}/verify/reform/{d['sha256']}").json()  # sans jeton
    assert v["found"] and v["ok"] and v["content_ok"] and v["ledger_ok"] and v["anchor_ok"]
    assert v["content"]["article_text"].startswith("La Direction")
    assert env.client.get(f"{API}/verify/reform/{'0' * 64}").json() == {"found": False}
    assert env.client.get(f"{API}/verify/reform/not-a-hash").status_code == 404

    with env.ctx.session_factory() as s:  # falsification du texte stocké : l'empreinte ne correspond plus
        raw = s.execute(text("SELECT content FROM reform_draft WHERE id=:i"), {"i": d["id"]}).scalar()
        c = json.loads(raw) if isinstance(raw, str) else dict(raw)
        c["article_text"] = "Personne n'est responsable."
        s.execute(text("UPDATE reform_draft SET content=:c WHERE id=:i"), {"c": json.dumps(c), "i": d["id"]})
        s.commit()
    v2 = env.client.get(f"{API}/verify/reform/{d['sha256']}").json()
    assert v2["found"] and not v2["ok"] and not v2["content_ok"]


def test_failed_citations_are_removed_not_trusted(env):
    gap = setup(env)
    env.ctx.services["reform_llm"] = Provider([draft("CH-INVENTE"), draft("CH1", "99")])  # puis mauvais article
    d = env.client.post(f"{API}/gaps/{gap['id']}/reform-drafts", headers=env.owner).json()
    assert d["verified"] is False and d["content"]["citations"] == [] and d["content"]["rejected_citations"] == 1


def test_requires_facilitator_and_corpus(env):
    gap = setup(env)
    obs = env.token("observer")
    assert env.client.post(f"{API}/gaps/{gap['id']}/reform-drafts", headers=obs).status_code == 403
    env.search.docs.clear()
    env.ctx.services["reform_llm"] = Provider([])
    r = env.client.post(f"{API}/gaps/{gap['id']}/reform-drafts", headers=env.owner)
    assert r.status_code == 422 and r.json()["error"]["code"] == "reform.no_sources"


def test_article_none_written_literally_is_read_as_no_article(env):
    gap = setup(env)
    env.knowledge.add("CH2", "DV1", text=ART)
    env.knowledge.chunks["CH2"]["article"] = None
    env.search.add("CH2", "DV1", ["action"])
    env.ctx.services["reform_llm"] = Provider([draft("CH2", "none")])
    d = env.client.post(f"{API}/gaps/{gap['id']}/reform-drafts", headers=env.owner).json()
    assert d["verified"] is True and d["content"]["citations"][0]["article"] is None
