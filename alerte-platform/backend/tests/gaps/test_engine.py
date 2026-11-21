from __future__ import annotations

from app.audit.events import EventType
from tests.gaps import helpers as H
from tests.gaps.conftest import API

ACT = [H.action("a1", "alerting"), H.action("a2", "alerting")]


def snap(tags=None, actions=("a1",), **kw):
    return H.snapshot([H.inject("inj-001", 1, list(actions), tags)], ACT, **kw)


def only(env, ex, code="G1"):  # noqa: ANN001, ANN201
    gs = [g for g in env.gaps(exercise=ex) if g["code"] == code]
    assert len(gs) == 1, gs
    return gs[0]


def test_detect_is_idempotent_and_records_negative_search_with_coverage(env):
    env.put_exercise("EX1", snap(["life_risk"]))
    r = env.detect("EX1").json()
    assert r["created"] == 1 and r["updated"] == 0 and r["integrity"]["snapshot"] == "verified"
    g = only(env, "EX1")
    assert g["evidence_basis"] == "documented" and g["confidence"] == "medium" and g["severity"] == 3
    assert g["corpus_coverage"] == 1.0 and g["cause"] == "institutional" and g["validation_status"] == "proposed"
    assert g["section"] == "findings" and g["reference_status"]["status"] == "insufficient_sources"
    assert "Non trouvé dans le corpus" in g["description"] and "100%" in g["description"]
    d = env.client.get(f"{API}/gaps/{g['id']}", headers=env.owner).json()
    assert d["negative_searches"][0]["verdict"] == "no_hit" and d["negative_searches"][0]["corpus_documents"] == 1
    assert {e["kind"] for e in d["evidence"]} >= {"mandate", "event", "negative_search"}
    assert len(d["negative_searches"][0]["queries"]) == 3  # 3 requêtes standardisées dans la langue de la KB
    assert all(c[2] == "analyst" for c in env.search.calls)
    r2 = env.detect("EX1").json()
    assert (r2["created"], r2["updated"], r2["unchanged"]) == (0, 0, 1)
    assert len(env.gaps(exercise="EX1")) == 1


def test_negative_search_counter_evidence_demotes_but_keeps_the_gap(env):
    env.search.add("CH-X", "DV1", ["action a1"], score=0.9)
    env.put_exercise("EX1", snap())
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["evidence_basis"] == "inferred" and g["confidence"] == "low"
    d = env.client.get(f"{API}/gaps/{g['id']}", headers=env.owner).json()
    counters = [e for e in d["evidence"] if e["role"] == "counter"]
    assert {e["kind"] for e in counters} == {"negative_search", "chunk"} and d["negative_searches"][0]["verdict"] == "strong_hit"
    assert any("contre-preuve" in n for n in g["detail"]["notes"])
    # un hit faible n'invalide pas
    env.search.docs.clear()
    env.search.add("CH-W", "DV1", ["action a1"], score=0.4)
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["evidence_basis"] == "documented"


def test_corpus_ablation_document_in_scope_makes_the_gap_disappear_and_return(env):
    """La détection dépend du corpus : ajouter/retirer un document de la portée change le résultat."""
    env.search.add("CH-X", "DV1", ["action a1"], score=0.9)
    with_doc = snap()
    without_doc = snap()
    without_doc["kb"][0]["document_version_ids"] = ["DV2"]  # le document pertinent (DV1) retiré de la portée
    env.put_exercise("EXA", with_doc)
    env.put_exercise("EXB", without_doc)
    env.detect("EXA")
    env.detect("EXB")
    assert only(env, "EXA")["evidence_basis"] == "inferred"
    assert only(env, "EXB")["evidence_basis"] == "documented"
    # sans AUCUN document dans la portée : l'absence ne vaut rien
    empty = snap()
    empty["kb"][0]["document_version_ids"] = []
    env.put_exercise("EXC", empty)
    env.detect("EXC")
    g = only(env, "EXC")
    assert g["evidence_basis"] == "inferred" and g["cause"] == "documentary"


def test_incomplete_coverage_is_never_proof_of_absence(env):
    env.knowledge.cov = {"ratio": 0.5, "expected": 2, "present": 1, "missing": ["Loi X"]}
    env.put_exercise("EX1", snap())
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["evidence_basis"] == "inferred" and g["cause"] == "documentary" and g["corpus_coverage"] == 0.5
    assert "50%" in g["description"]
    d = env.client.get(f"{API}/gaps/{g['id']}", headers=env.owner).json()
    assert d["negative_searches"][0]["coverage_missing"] == ["Loi X"]
    # liste attendue non renseignée : couverture inconnue, signalée (null), non inventée
    env.knowledge.cov = {"ratio": None, "expected": 0, "present": 0, "missing": []}
    env.detect("EX1")
    assert only(env, "EX1")["corpus_coverage"] is None


def test_search_service_missing_prevents_documented_claim(env):
    env.ctx.services.pop("search")
    env.put_exercise("EX1", snap())
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["evidence_basis"] == "inferred" and g["detail"]["neg_status"] == "unavailable"


def test_global_practices_kb_is_excluded_from_analyst_scope(env):
    s = snap()
    s["kb"].append({"kb_id": "KBG", "code": "g", "name": "g", "document_version_ids": ["DVG"]})
    env.search.add("CH-G", "DVG", ["action a1"], kb_id="KBG")
    env.put_exercise("EX1", s)
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["evidence_basis"] == "documented"  # la pratique étrangère n'est pas une contre-preuve nationale
    assert all("DVG" not in c[1] for c in env.search.calls)


def _artifact_events(retrieved: list[str]):
    ev = [(EventType.GAP, {"origin_kind": "coordinator_signal", "signal": "MISSING_BASIS", "inject_ref": "inj-001",
                           "action_code": "a1", "institutions": [H.INST["A"]], "evidence": {}}, {}),
          (EventType.DECISION, {"decision_id": "D1", "seat_code": "SA", "inject_ref": "inj-001", "action_code": "a1",
                                "outcome": "no_legal_basis_found", "author": "agent", "gap_flags": []}, {}),
          (EventType.RETRIEVAL, {"query": "q", "scope_hash": "h", "results": [{"chunk_id": c, "score": 0.5, "rank": i}
                                                                            for i, c in enumerate(retrieved)],
                                 "signals": {}}, {"seat_id": "S1", "visibility": "seat"})]
    return ev


def test_cause_artifact_when_relevant_document_in_scope_but_not_retrieved(env):
    env.search.add("CH-X", "DV1", ["action a1"], score=0.9)
    env.put_exercise("EX1", snap(), _artifact_events(["CH-OTHER"]))
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["cause"] == "artifact" and g["evidence_basis"] == "inferred"
    # le document HAD été récupéré : l'agent l'avait sous les yeux -> pas un artefact de retrieval
    env.put_exercise("EX2", snap(), _artifact_events(["CH-X"]))
    env.detect("EX2")
    assert only(env, "EX2")["cause"] != "artifact"
    # aucun RETRIEVAL consigné : on ne conclut pas à un artefact
    env.put_exercise("EX3", snap(), _artifact_events(["CH-OTHER"])[:2])
    env.detect("EX3")
    assert only(env, "EX3")["cause"] != "artifact"


def test_registry_not_reviewed_is_not_absent_mandate_end_to_end(env):
    s = snap()
    s["registry_states"] = {i: "unreviewed" for i in H.INST.values()}
    env.put_exercise("EX1", s)
    env.detect("EX1")
    g = only(env, "EX1")
    assert g["evidence_basis"] == "inferred" and g["registry_state"] == "unreviewed"
    assert any("registre non revu" in n for n in g["detail"]["notes"])


def test_signal_hypothesis_and_scripted_through_the_ledger(env):
    sig = (EventType.GAP, {"origin_kind": "coordinator_signal", "signal": "ORPHAN_REQUEST", "inject_ref": "inj-001",
                           "action_code": "a1", "institutions": [H.INST["A"]], "evidence": {}}, {})
    hyp = (EventType.DECISION, {"decision_id": "D1", "seat_code": "SA", "inject_ref": "inj-001", "action_code": "a2",
                                "outcome": "refer", "author": "agent",
                                "gap_flags": [{"hint": "technical", "text": "capteurs"}]}, {})
    env.put_exercise("EX1", snap(), [sig, hyp])
    env.put_exercise("EX2", snap(ai_mode="scripted"), [sig])
    env.detect("EX1")
    env.detect("EX2")
    g = only(env, "EX1")
    assert g["confidence"] == "high" and g["detail"]["signals"][0]["observed"] is True
    hyps = env.gaps(exercise="EX1", basis="hypothesis")
    assert len(hyps) == 1 and hyps[0]["section"] == "hypotheses" and hyps[0]["origin"] == "agent_hypothesis"
    s2 = only(env, "EX2")
    assert s2["confidence"] == "medium" and s2["detail"]["scripted"] is True and s2["detail"]["signals"][0]["observed"] is False
    assert env.gaps(exercise="EX2", basis="observed") == []


def test_snapshot_tampering_and_commitment_check(env):
    from sqlalchemy import text

    from app.gaps.commitment import compute_commitment
    s = snap()
    full = {**s, "registry_states": {i: "reviewed_complete" for i in H.INST.values()}}

    def full_for(ex):  # noqa: ANN001, ANN202
        return {**full, "workspace_id": env.ws, "exercise": {**s["exercise"], "id": ex}}

    env.put_exercise("EX1", s, commitment=compute_commitment(full_for("EX1")))
    r = env.detect("EX1").json()
    assert r["integrity"]["commitment"] == "match" and r["integrity"]["snapshot"] == "verified" and not r["warnings"]
    assert len(r["integrity"]["rules_sha256"]) == 64
    env.put_exercise("EX2", s, commitment="0" * 64)
    r = env.detect("EX2").json()
    assert r["integrity"]["commitment"] == "mismatch" and "commitment_mismatch" in r["warnings"]
    env.put_exercise("EX3", s)
    assert env.detect("EX3").json()["integrity"]["commitment"] == "absent"
    # le registre change APRÈS le lancement : l'empreinte d'engagement ne correspond plus
    changed = {**full_for("EX1"), "registry_states": {i: "partial" for i in H.INST.values()}}
    assert compute_commitment(changed) != compute_commitment(full_for("EX1"))
    # snapshot modifié après lancement : refus net
    env.put_exercise("EX4", s)
    with env.ctx.session_factory() as ses:
        ses.execute(text("UPDATE exercise_snapshot SET payload = replace(payload, 'action a1', 'action zz') WHERE exercise_id='EX4'"))
        ses.commit()
    r = env.detect("EX4")
    assert r.status_code == 409 and r.json()["error"]["code"] == "gap.snapshot_integrity_failed"
    env.put_exercise("EX5", s, sha="f" * 64)  # colonne payload_sha256 trafiquée
    assert env.detect("EX5").status_code == 409


def test_commitment_and_snapshot_hash_match_the_simulation_formulas(env):
    """Les empreintes écrites par la simulation au lancement doivent être vérifiables par les formules de `gaps`."""
    from app.gaps.commitment import compute_commitment, snapshot_hash
    from app.simulation import snapshot as sim
    s = {**snap(), "workspace_id": "W"}
    reg = {H.INST["A"]: "reviewed_complete"}
    assert snapshot_hash(s) == sim.snapshot_hash(s)
    assert compute_commitment(s, reg) == sim.commitment_hash(s, reg)


def test_hooks_incremental_then_final_marks_stale_and_keeps_reviews(env):
    s = H.snapshot([H.inject("inj-001", 1, ["a1"]), H.inject("inj-002", 2, ["a2"])], ACT)
    env.put_exercise("EX1", s)
    engine = env.ctx.services["gap_engine"]
    with env.ctx.session_factory() as ses:
        out = engine.on_inject_closed(ses, "EX1", "inj-001")
        ses.commit()
    assert [g["action_code"] for g in out] == ["a1"] and out[0]["change"] == "created"
    gid = env.gaps(exercise="EX1")[0]["id"]
    env.client.post(f"{API}/gaps/{gid}/reviews", json={"action": "confirm", "comment": "ok"}, headers=env.owner)
    with env.ctx.session_factory() as ses:
        final = engine.on_exercise_finished(ses, "EX1")
        ses.commit()
    assert sorted(g["action_code"] for g in final) == ["a1", "a2"]
    g1 = [g for g in env.gaps(exercise="EX1") if g["action_code"] == "a1"][0]
    assert g1["id"] == gid and g1["validation_status"] == "confirmed"  # revue humaine conservée
    # une action devenue couverte : le candidat de l'ancien run est marqué périmé (jamais supprimé)
    s2 = H.snapshot([H.inject("inj-001", 1, ["a1"]), H.inject("inj-002", 2, ["a2"])], ACT,
                    mandates=[H.mandate("m1", "B", "duty", "a2")])
    env.put_exercise("EX1", s2)
    r = env.detect("EX1").json()
    assert r["stale"] == 1
    assert [g["action_code"] for g in env.gaps(exercise="EX1")] == ["a1"]
    assert len(env.gaps(exercise="EX1", include_stale=True)) == 2


def test_hook_errors_do_not_break_the_exercise(env):
    engine = env.ctx.services["gap_engine"]
    with env.ctx.session_factory() as ses:
        assert engine.on_inject_closed(ses, "EX-INCONNU", "inj-001") == []


def test_detect_requires_facilitator_and_same_workspace(env):
    env.put_exercise("EX1", snap())
    assert env.detect("EX1", env.token("observer")).status_code == 403
    assert env.detect("EX1", {}).status_code == 401
    # autre espace : le snapshot appartient à A
    r = env.client.post(f"{API}/workspaces", json={"name": "B"}, headers=env.owner)
    other = {"Authorization": f"Bearer {r.json()['owner_token']}"}
    assert env.detect("EX1", other).status_code == 404
    assert env.detect("EX-ABSENT").status_code == 404
