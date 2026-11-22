"""Mandates -> snapshot -> gaps : ablation de corpus et contrôle négatif avec le VRAI registre (services mandates)."""
from __future__ import annotations

from app.mandates import service as mandates
from tests.gaps import helpers as H
from tests.gaps.conftest import API


def setup_registry(env):  # noqa: ANN001, ANN201
    c, o = env.client, env.owner
    a = c.post(f"{API}/institutions", json={"code": "AAA", "name": "A"}, headers=o).json()["id"]
    b = c.post(f"{API}/institutions", json={"code": "BBB", "name": "B"}, headers=o).json()["id"]
    for code in ("act_x", "act_y"):
        c.post(f"{API}/actions", json={"code": code, "label": f"action {code}", "domain": "dom", "derivation": "referential",
                                       "reference_note": "cadre"}, headers=o)
    env.knowledge.add("CHM", "DVM", text="B peut agir")
    m = c.post(f"{API}/mandates", json={"institution_id": b, "kind": "duty", "action_code": "act_x", "procedure_status": "specific",
                                         "has_deadline": True, "sources": [{"document_version_id": "DVM", "chunk_id": "CHM"}]},
               headers=o).json()
    c.post(f"{API}/mandates/{m['id']}/validate", headers=o)
    return a, b


def build_snapshot(env, a, b, docs, action="act_x", tags=None):  # noqa: ANN001, ANN201
    with env.ctx.session_factory() as s:
        ms = mandates.export_active_mandates(s, env.ws, {a, b}, docs)
        actions = mandates.list_actions(s, env.ws)
        states = {i: mandates.registry_state(s, env.ws, i) for i in (a, b)}
    snap = H.snapshot([H.inject("inj-001", 1, [action], tags or ["life_risk"], recipients=[a])], actions, mandates=ms)
    snap["institutions"] = [{"id": a, "code": "AAA", "name": "A", "kind": "agency", "country_id": None, "domains": []},
                            {"id": b, "code": "BBB", "name": "B", "kind": "agency", "country_id": None, "domains": []}]
    snap["kb"][0]["document_version_ids"] = sorted(docs | {"DV1"})
    snap.pop("registry_states", None)
    return snap, states


def put_live(env, ex, snap):  # noqa: ANN001, ANN201
    """Snapshot SANS `registry_states` : le moteur interroge alors `mandates.registry_state` (avertissement `registry_states_live`)."""
    import json

    from sqlalchemy import text

    from app.audit.events import EventType
    from app.core.canonical_json import canonical_sha256
    from app.gaps.commitment import snapshot_hash
    full = {**snap, "workspace_id": env.ws, "exercise": {**snap["exercise"], "id": ex}}
    full.pop("registry_states", None)
    sha = canonical_sha256(full)
    with env.ctx.session_factory() as s:
        s.execute(text("DELETE FROM exercise_snapshot WHERE exercise_id=:e"), {"e": ex})
        s.execute(text("INSERT INTO exercise_snapshot (exercise_id, payload, payload_sha256) VALUES (:e,:p,:h)"),
                  {"e": ex, "p": json.dumps(full), "h": sha})
        env.ctx.services["ledger"].append(s, ex, EventType.SNAPSHOT, "system", {"snapshot_sha256": snapshot_hash(full)})
        s.commit()


def test_ablation_with_real_registry_and_live_registry_states(env):
    a, b = setup_registry(env)
    snap_with, _ = build_snapshot(env, a, b, {"DVM"})
    snap_without, _ = build_snapshot(env, a, b, set())  # document retiré de la portée => le mandat n'est plus actif
    assert [m["institution_id"] for m in snap_with["mandates"]] == [b] and snap_without["mandates"] == []
    put_live(env, "EXW", snap_with)
    put_live(env, "EXO", snap_without)
    r_with = env.detect("EXW").json()
    assert r_with["warnings"] == ["registry_states_live"] and r_with["gaps"] == []  # mandat actif : aucune lacune
    r_without = env.detect("EXO").json()
    assert [g["code"] for g in r_without["gaps"]] == ["G1"]
    assert r_without["gaps"][0]["evidence_basis"] == "inferred"  # registre jamais revu : « non revu », pas « sans mandat »
    for inst in (a, b):  # revue complète des deux institutions => la même absence devient « documentée »
        assert env.client.put(f"{API}/institutions/{inst}/registry-review", json={"status": "reviewed_complete"},
                              headers=env.owner).status_code == 200
    env.detect("EXO")
    g = env.gaps(exercise="EXO")[0]
    assert g["evidence_basis"] == "documented" and g["registry_state"] == "reviewed_complete"
    # contrefactuel : on remet le document dans la portée (nouvel exercice cloné) -> la lacune disparaît
    put_live(env, "EXO2", build_snapshot(env, a, b, {"DVM"})[0])
    assert env.detect("EXO2").json()["gaps"] == []
    cmp = env.client.get(f"{API}/gaps/compare", params={"a": "EXO", "b": "EXO2"}, headers=env.owner).json()
    assert cmp["summary"] == {"new": 0, "persistent": 0, "resolved": 1}
    # puis on le retire de nouveau : elle revient (nouvelle par rapport à EXO2)
    put_live(env, "EXO3", build_snapshot(env, a, b, set())[0])
    env.detect("EXO3")
    cmp = env.client.get(f"{API}/gaps/compare", params={"a": "EXO2", "b": "EXO3"}, headers=env.owner).json()
    assert cmp["summary"] == {"new": 1, "persistent": 0, "resolved": 0}
    pers = env.client.get(f"{API}/gaps/compare", params={"a": "EXO", "b": "EXO3"}, headers=env.owner).json()
    assert pers["summary"]["persistent"] == 1


def test_negative_control_complete_registry_yields_zero_gaps(env):
    a, b = setup_registry(env)
    for inst in (a, b):
        env.client.put(f"{API}/institutions/{inst}/registry-review", json={"status": "reviewed_complete"}, headers=env.owner)
    snap, _ = build_snapshot(env, a, b, {"DVM"}, tags=["life_risk", "time_critical"])
    put_live(env, "EXN", snap)
    r = env.detect("EXN").json()
    assert r["gaps"] == [] and env.gaps(exercise="EXN") == []


def test_live_registry_states_are_verified_against_the_launch_commitment(env):
    """Le registre n'est pas dans le snapshot : ses états relus en direct sont vérifiés via `commitment_sha256`."""
    import json

    from sqlalchemy import text

    from app.audit.events import EventType
    from app.core.canonical_json import canonical_sha256
    from app.gaps.commitment import compute_commitment, snapshot_hash
    a, b = setup_registry(env)
    for inst in (a, b):
        env.client.put(f"{API}/institutions/{inst}/registry-review", json={"status": "reviewed_complete"}, headers=env.owner)
    snap, _ = build_snapshot(env, a, b, {"DVM"})
    snap["seats"] = [{"seat_id": "S1", "code": "SA", "institution_id": a, "controller": "agent", "agent": {"id": "AG1"}}]
    full = {**snap, "workspace_id": env.ws}
    full.pop("registry_states", None)
    commit = compute_commitment(full, {a: "reviewed_complete"})

    def put(ex, declared):  # noqa: ANN001, ANN202
        p = {**full, "exercise": {**full["exercise"], "id": ex}}
        with env.ctx.session_factory() as s:
            s.execute(text("INSERT INTO exercise_snapshot (exercise_id, payload, payload_sha256) VALUES (:e,:p,:h)"),
                      {"e": ex, "p": json.dumps(p), "h": canonical_sha256(p)})
            env.ctx.services["ledger"].append(s, ex, EventType.SNAPSHOT, "system", {
                "snapshot_sha256": snapshot_hash(p), "commitment_sha256": declared})
            s.commit()

    put("EXV", commit)
    r = env.detect("EXV").json()
    assert r["integrity"]["commitment"] == "match" and r["warnings"] == [] and r["integrity"]["registry_states"] == "live"
    # le registre est dégradé après le lancement : l'engagement ne correspond plus (signalé, jamais silencieux)
    env.client.put(f"{API}/institutions/{a}/registry-review", json={"status": "partial"}, headers=env.owner)
    put("EXV2", commit)
    r = env.detect("EXV2").json()
    assert r["integrity"]["commitment"] == "mismatch" and "commitment_mismatch" in r["warnings"]


def test_reform_hypothesis_resolves_the_gap_without_touching_the_real_registry(env):
    """« Et si… ? » : un mandat hypothétique injecté dans le seul snapshot fait disparaître la lacune ; le registre reste intact."""
    from app.simulation.snapshot import REFORM_SOURCE_ARTICLE, reform_entries
    a, b = setup_registry(env)
    for inst in (a, b):
        env.client.put(f"{API}/institutions/{inst}/registry-review", json={"status": "reviewed_complete"}, headers=env.owner)
    base, _ = build_snapshot(env, a, b, set(), action="act_y")  # personne n'a de mandat pour act_y
    put_live(env, "EXB", base)
    assert [g["code"] for g in env.detect("EXB").json()["gaps"]] == ["G1"]
    reform = reform_entries({"reform_mandates": [
        {"institution_id": a, "action_code": "act_y", "kind": "duty", "description": "A diffuse l'alerte sous 15 min", "has_deadline": True},
        {"institution_id": "NOT-SEATED", "action_code": "act_y"},  # institution absente de l'exercice : ignorée
    ]}, {a, b})
    assert len(reform) == 1 and reform[0]["hypothesis"] is True and reform[0]["evidence_tag"] == "assumed"
    assert reform[0]["sources"][0]["article"] == REFORM_SOURCE_ARTICLE
    what_if, _ = build_snapshot(env, a, b, set(), action="act_y")
    what_if["mandates"] = what_if["mandates"] + reform
    put_live(env, "EXR", what_if)
    assert env.detect("EXR").json()["gaps"] == []
    cmp = env.client.get(f"{API}/gaps/compare", params={"a": "EXB", "b": "EXR"}, headers=env.owner).json()
    assert cmp["summary"] == {"new": 0, "persistent": 0, "resolved": 1}
    real = env.client.get(f"{API}/mandates", headers=env.owner).json()
    assert [m["action_code"] for m in real] == ["act_x"]  # aucun mandat act_y n'a été écrit dans le registre réel
