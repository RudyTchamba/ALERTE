from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.audit.events import EventType
from app.gaps.models import GapReview
from tests.gaps import helpers as H
from tests.gaps.conftest import API

ACT = [H.action("a1", "alerting"), H.action("a2", "alerting")]


def snap(tags=None, actions=("a1",), **kw):
    return H.snapshot([H.inject("inj-001", 1, list(actions), tags)], ACT, **kw)


@pytest.fixture
def gap(env):  # noqa: ANN001
    env.put_exercise("EX1", snap(["life_risk"]))
    env.detect("EX1")
    return env.gaps(exercise="EX1")[0]


def review(env, gid, action, **kw):  # noqa: ANN001, ANN201
    return env.client.post(f"{API}/gaps/{gid}/reviews", json={"action": action, **kw}, headers=env.owner)


def test_review_workflow_append_only_history(env, gap):
    gid = gap["id"]
    r = review(env, gid, "dispute")  # sans motif : refusé
    assert r.status_code == 422 and r.json()["error"]["code"] == "gap.review.reason_required"
    assert review(env, gid, "dispute", comment="   ").status_code == 422
    assert review(env, gid, "reject").status_code == 422
    assert review(env, gid, "comment").status_code == 422
    assert env.gaps()[0]["validation_status"] == "proposed"  # rien n'a changé
    assert review(env, gid, "reopen").status_code == 409  # transition interdite
    ok = review(env, gid, "dispute", comment="le décret Y confère ce pouvoir", reality_label="partially_real", blind=True)
    assert ok.status_code == 201 and ok.json()["from_status"] == "proposed" and ok.json()["to_status"] == "disputed"
    assert ok.json()["blind"] is True and ok.json()["reality_label"] == "partially_real"
    assert review(env, gid, "comment", comment="note").json()["to_status"] == "disputed"
    assert review(env, gid, "confirm", comment="finalement oui", reality_label="real").json()["to_status"] == "confirmed"
    assert review(env, gid, "dispute", comment="doute").status_code == 201
    assert review(env, gid, "reject", comment="faux positif", reality_label="not_real").json()["to_status"] == "rejected"
    assert review(env, gid, "confirm").status_code == 409
    assert review(env, gid, "reopen", comment="réexamen").json()["to_status"] == "proposed"
    d = env.client.get(f"{API}/gaps/{gid}", headers=env.owner).json()
    assert [(x["action"], x["to_status"]) for x in d["reviews"]] == [
        ("dispute", "disputed"), ("comment", "disputed"), ("confirm", "confirmed"), ("dispute", "disputed"),
        ("reject", "rejected"), ("reopen", "proposed")]  # historique conservé, y compris les contestations
    assert all(x["reviewer"] for x in d["reviews"])
    # une lacune rejetée reste en base (et dans la liste filtrée par statut)
    review(env, gid, "reject", comment="encore")
    assert env.gaps(status="rejected")[0]["id"] == gid
    # la revue ne modifie JAMAIS la base de preuve ni la confiance
    assert d["evidence_basis"] == gap["evidence_basis"] and d["confidence"] == gap["confidence"]


def test_gap_review_rows_cannot_be_updated_or_deleted(env, gap):
    review(env, gap["id"], "confirm", comment="ok")
    with env.ctx.session_factory() as s:
        row = s.query(GapReview).first()
        row.comment = "falsifié"
        with pytest.raises(RuntimeError):
            s.flush()
        s.rollback()
    with env.ctx.session_factory() as s:  # même en SQL brut : trigger SQLite
        with pytest.raises(DBAPIError):
            s.execute(text("UPDATE gap_review SET comment='x'"))
        s.rollback()
        with pytest.raises(DBAPIError):
            s.execute(text("DELETE FROM gap_review"))
        s.rollback()


def test_reviews_are_facilitator_only_and_observer_sees_only_confirmed_findings(env, gap):
    obs, aud = env.token("observer"), env.token("auditor")
    assert env.client.post(f"{API}/gaps/{gap['id']}/reviews", json={"action": "confirm"}, headers=obs).status_code == 403
    assert env.client.post(f"{API}/gaps/{gap['id']}/reviews", json={"action": "confirm"}, headers=aud).status_code == 403
    assert env.gaps(headers=obs) == [] and len(env.gaps(headers=aud)) == 1
    assert env.client.get(f"{API}/gaps/{gap['id']}", headers=obs).status_code == 404
    review(env, gap["id"], "confirm", comment="ok")
    assert len(env.gaps(headers=obs)) == 1
    assert env.client.get(f"{API}/gaps/{gap['id']}", headers=obs).status_code == 200
    tok = env.client.post(f"{API}/tokens", json={"role": "player"}, headers=env.owner).json()["token"]
    assert env.client.get(f"{API}/gaps", headers={"Authorization": f"Bearer {tok}"}).status_code == 403


def test_hypotheses_are_hidden_from_observers_even_if_confirmed(env):
    hyp = (EventType.DECISION, {"decision_id": "D1", "seat_code": "SA", "inject_ref": "inj-001", "action_code": "a2",
                                "gap_flags": [{"hint": "technical", "text": "x"}]}, {})
    env.put_exercise("EX1", snap(), [hyp])
    env.detect("EX1")
    h = env.gaps(basis="hypothesis")[0]
    review(env, h["id"], "confirm", comment="plausible")
    assert env.gaps(headers=env.token("observer"), basis="hypothesis") == []


def test_patch_is_journaled_and_severity_needs_a_reason_and_basis_cannot_be_raised(env, gap):
    gid = gap["id"]
    r = env.client.patch(f"{API}/gaps/{gid}", json={"severity": 2}, headers=env.owner)
    assert r.status_code == 422 and r.json()["error"]["code"] == "gap.review.reason_required"
    r = env.client.patch(f"{API}/gaps/{gid}", json={"severity": 2, "title": "Titre humain", "reason": "pas de risque vital ici"},
                         headers=env.owner)
    assert r.status_code == 200 and r.json()["severity"] == 2 and r.json()["auto_severity"] == 3
    env.client.patch(f"{API}/gaps/{gid}", json={"evidence_basis": "documented"}, headers=env.owner)  # champ ignoré
    d = env.client.get(f"{API}/gaps/{gid}", headers=env.owner).json()
    edit = [x for x in d["reviews"] if x["action"] == "edit"][0]
    assert edit["changes"]["severity"] == {"from": 3, "to": 2} and edit["comment"] == "pas de risque vital ici"
    assert d["evidence_basis"] == gap["evidence_basis"]
    # une nouvelle détection n'écrase pas l'édition humaine mais met à jour la valeur automatique
    env.detect("EX1")
    d = env.client.get(f"{API}/gaps/{gid}", headers=env.owner).json()
    assert d["severity"] == 2 and d["title"] == "Titre humain" and d["auto_severity"] == 3


def test_filters(env):
    s = H.snapshot([H.inject("inj-001", 1, ["a1"], ["life_risk"]),
                    H.inject("inj-002", 2, ["a2"], ["public_communication"], recipients=[H.INST["B"]])], ACT,
                   mandates=[H.mandate("m1", "C", "duty", "a2")])
    env.put_exercise("EX1", s)
    env.detect("EX1")
    assert {g["code"] for g in env.gaps()} == {"G1", "G7"}
    assert [g["code"] for g in env.gaps(code="G7")] == ["G7"] and [g["code"] for g in env.gaps(severity=3)] == ["G1"]
    assert [g["code"] for g in env.gaps(institution=H.INST["B"])] == ["G7"]
    assert env.gaps(category="mandate_absent_or_incomplete")[0]["code"] == "G1"
    assert env.gaps(basis="documented") and env.gaps(status="confirmed") == [] and env.gaps(domain="alerting")
    assert env.gaps(domain="autre") == [] and env.gaps(exercise="EX-X") == []
    assert env.client.get(f"{API}/gaps", params={"severity": 9}, headers=env.owner).status_code == 422


def test_references_require_a_source_and_two_jurisdictions(env, gap):
    gid = gap["id"]
    env.knowledge.add("CG1", "DVG1", kb_id="KBG")
    env.knowledge.add("CG2", "DVG2", kb_id="KBG")
    env.knowledge.add("CN1", "DV1", kb_id="KB1")

    def ref(**kw):  # noqa: ANN202
        return env.client.post(f"{API}/international-references", json={"instrument": "Instrument", **kw}, headers=env.owner)

    assert ref(jurisdiction="J1").json()["error"]["code"] == "reference.source_required"  # rien d'inventé
    assert ref(jurisdiction="J1", url="https://x.example").json()["error"]["code"] == "reference.url_needs_summary_tag"
    assert ref(jurisdiction="J1", chunk_id="inconnu").json()["error"]["code"] == "reference.chunk_unresolved"
    assert ref(jurisdiction="J1", chunk_id="CN1").json()["error"]["code"] == "reference.not_global_practices"
    r1 = ref(jurisdiction="J1", chunk_id="CG1", gap_codes=["G1"], domains=["alerting"])
    assert r1.status_code == 201 and r1.json()["evidence_tag"] == "documented" and r1.json()["document_version_id"] == "DVG1"
    u = ref(jurisdiction="J2", url="https://x.example/a", evidence_tag="summary")
    assert u.status_code == 201 and u.json()["evidence_tag"] == "summary" and u.json()["chunk_id"] is None
    same = ref(jurisdiction="j1", chunk_id="CG2")
    assert same.status_code == 201

    def status():  # noqa: ANN202
        return env.client.get(f"{API}/gaps/{gid}", headers=env.owner).json()["reference_status"]

    assert status()["status"] == "insufficient_sources" and status()["count"] == 0
    l1 = env.client.post(f"{API}/gaps/{gid}/references", json={"reference_id": r1.json()["id"], "fit_note": "proche"}, headers=env.owner)
    assert l1.status_code == 201 and l1.json()["status"] == "suggested"
    assert env.client.post(f"{API}/gaps/{gid}/references", json={"reference_id": r1.json()["id"]}, headers=env.owner).status_code == 409
    l2 = env.client.post(f"{API}/gaps/{gid}/references", json={"reference_id": same.json()["id"]}, headers=env.owner)
    st = status()
    assert st["status"] == "insufficient_sources" and st["count"] == 1 and "insuffisantes : 1" in st["message"]  # même juridiction
    l3 = env.client.post(f"{API}/gaps/{gid}/references", json={"reference_id": u.json()["id"]}, headers=env.owner)
    assert status()["status"] == "sufficient" and status()["jurisdictions"] == ["j1", "j2"]
    # refuser une suggestion la retire du décompte
    p = env.client.patch(f"{API}/gap-references/{l3.json()['id']}", json={"status": "rejected"}, headers=env.owner)
    assert p.json()["status"] == "rejected" and status()["status"] == "insufficient_sources"
    env.client.patch(f"{API}/gap-references/{l2.json()['id']}", json={"status": "accepted"}, headers=env.owner)
    listing = env.client.get(f"{API}/international-references", params={"jurisdiction": "J1"}, headers=env.owner).json()
    assert len(listing) == 2
    assert [x["jurisdiction"] for x in env.client.get(f"{API}/international-references", params={"gap_code": "G1"},
                                                      headers=env.owner).json()] == ["J1"]
    d = env.client.get(f"{API}/gaps/{gid}", headers=env.owner).json()
    assert {x["reference"]["jurisdiction"] for x in d["references"]} == {"J1", "j1", "J2"}
    sugg = env.client.get(f"{API}/gaps/{gid}/reference-suggestions", headers=env.owner).json()
    assert sugg == []  # tout est déjà associé


def test_improvement_actions(env, gap):
    gid = gap["id"]
    inst = env.client.post(f"{API}/institutions", json={"code": "OWN", "name": "Owner"}, headers=env.owner).json()["id"]
    r = env.client.post(f"{API}/gaps/{gid}/improvement-actions", json={
        "description": "Désigner un chef de file", "owner_institution_id": inst, "due_date": "2027-03-01", "kpi": "mandat publié"},
        headers=env.owner)
    assert r.status_code == 201 and r.json()["status"] == "planned"
    aid = r.json()["id"]
    assert env.client.patch(f"{API}/improvement-actions/{aid}", json={"status": "done"}, headers=env.owner).json()["status"] == "done"
    assert env.client.get(f"{API}/gaps/{gid}/improvement-actions", headers=env.owner).json()[0]["kpi"] == "mandat publié"
    assert env.client.get(f"{API}/gaps/{gid}", headers=env.owner).json()["improvement_actions"][0]["status"] == "done"
    assert env.client.post(f"{API}/gaps/{gid}/improvement-actions", json={"description": "x", "owner_institution_id": "inconnue"},
                           headers=env.owner).status_code == 404


def test_workspace_isolation(env, gap):
    r = env.client.post(f"{API}/workspaces", json={"name": "B"}, headers=env.owner)
    other = {"Authorization": f"Bearer {r.json()['owner_token']}"}
    gid = gap["id"]
    assert env.client.get(f"{API}/gaps", headers=other).json() == []
    assert env.client.get(f"{API}/gaps/{gid}", headers=other).status_code == 404
    assert env.client.post(f"{API}/gaps/{gid}/reviews", json={"action": "confirm"}, headers=other).status_code == 404
    assert env.client.patch(f"{API}/gaps/{gid}", json={"title": "x"}, headers=other).status_code == 404
    assert env.client.post(f"{API}/gaps/{gid}/improvement-actions", json={"description": "x"}, headers=other).status_code == 404
    assert env.client.get(f"{API}/gaps/{gid}/improvement-actions", headers=other).status_code == 404
    ref = env.client.post(f"{API}/international-references", json={"jurisdiction": "J", "instrument": "I", "url": "https://x",
                                                                   "evidence_tag": "summary"}, headers=env.owner).json()
    assert env.client.post(f"{API}/gaps/{gid}/references", json={"reference_id": ref["id"]}, headers=other).status_code == 404
    assert env.client.get(f"{API}/international-references", headers=other).json() == []
    assert env.client.get(f"{API}/gaps/compare", params={"a": "EX1", "b": "EX1"}, headers=other).json()["summary"] == \
        {"new": 0, "persistent": 0, "resolved": 0}


def test_compare_new_persistent_resolved_by_fingerprint(env):
    a = H.snapshot([H.inject("inj-001", 1, ["a1", "a2"], ["life_risk"])], ACT)
    b = H.snapshot([H.inject("inj-001", 1, ["a1", "a2"], ["life_risk"])], ACT, mandates=[H.mandate("m1", "B", "duty", "a2")])
    b["scenario"]["injects"][0]["tags"] = ["life_risk", "public_communication"]
    env.put_exercise("EXA", a)
    env.put_exercise("EXB", b)
    env.detect("EXA")
    env.detect("EXB")
    # A : G1(a1), G1(a2) ; B : G1(a1) persistante, G1(a2) résolue, G7(a1/a2) nouvelles
    cmp = env.client.get(f"{API}/gaps/compare", params={"a": "EXA", "b": "EXB"}, headers=env.owner).json()
    assert [x["a"]["action_code"] for x in cmp["persistent"]] == ["a1"]
    assert [x["action_code"] for x in cmp["resolved"]] == ["a2"]
    assert {x["code"] for x in cmp["new"]} == {"G7"}
    # un gap rejeté sort de la comparaison
    gid = [g for g in env.gaps(exercise="EXA") if g["action_code"] == "a2"][0]["id"]
    review(env, gid, "reject", comment="faux positif")
    cmp = env.client.get(f"{API}/gaps/compare", params={"a": "EXA", "b": "EXB"}, headers=env.owner).json()
    assert cmp["resolved"] == []
