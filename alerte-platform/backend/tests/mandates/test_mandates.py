from __future__ import annotations

from app.mandates import service
from tests.mandates.conftest import API, mk_action, mk_inst

CSV = (
    "line_id,country,institution,kind,action,description,source_doc,article,procedure,depends_on,dependency_ready,evidence,assumed_by\n"
    "L01,XX,AAA,power,act_a,Pouvoir A,OLD-S02,,Procédure générale,,yes,inferred,\n"
    "L02,XX,AAA,duty,act_a,Devoir A,OLD-S02,,,Texte à obtenir,no,documented,\n"
    "L03,XX,ZZZ,duty,act_a,Inconnue,OLD-S02,,,,,inferred,\n"
    "L04,XX,AAA,duty,act_inconnue,Action inconnue,OLD-S02,,,,,inferred,\n"
)


def _mandate(client, h, inst, action="act_a", **kw):  # noqa: ANN001, ANN201
    body = {"institution_id": inst, "kind": "power", "action_code": action, "description": "d", **kw}
    r = client.post(f"{API}/mandates", json=body, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_action_derivation_requires_justification(mclient, h):
    r = mclient.post(f"{API}/actions", json={"code": "x", "label": "X", "derivation": "scenario_author"}, headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "action.justification_required"
    a = mk_action(mclient, h, "x", "scenario_author", justification="choix du concepteur")
    assert "concepteur" in a["presentation"] and "officielle" not in a["presentation"]
    assert mk_action(mclient, h, "y", reference_note="Cadre de référence §3")["presentation"] == "attente documentée"
    assert mclient.post(f"{API}/actions", json={"code": "x", "label": "X", "derivation": "referential"}, headers=h).status_code == 409
    r = mclient.patch(f"{API}/actions/{a['id']}", json={"justification": ""}, headers=h)
    assert r.status_code == 422
    assert [x["code"] for x in mclient.get(f"{API}/actions", headers=h).json()] == ["x", "y"]


def test_create_mandate_needs_resolvable_source_and_known_action(mclient, h, knowledge):
    inst = mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    body = {"institution_id": inst, "kind": "power", "action_code": "nope"}
    assert mclient.post(f"{API}/mandates", json=body, headers=h).json()["error"]["code"] == "mandate.unknown_action"
    src = {"document_version_id": "DV1", "chunk_id": "C-missing", "quote": "q"}
    r = mclient.post(f"{API}/mandates", json={**body, "action_code": "act_a", "sources": [src]}, headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "mandate.source_unresolved"
    knowledge.add("C1", "DV1", text="L'agence A   peut agir.")
    ok = mclient.post(f"{API}/mandates", json={**body, "action_code": "act_a", "sources": [
        {"document_version_id": "DV1", "chunk_id": "C1", "quote": "l'agence a peut agir"}]}, headers=h).json()
    assert ok["validation"] == "proposed" and ok["sources"][0]["quote_found"] is True and ok["active"] is False
    bad = mclient.post(f"{API}/mandates", json={**body, "action_code": "act_a", "sources": [
        {"document_version_id": "AUTRE", "chunk_id": "C1"}]}, headers=h)
    assert bad.json()["error"]["code"] == "mandate.source_mismatch"


def test_same_passage_cannot_be_linked_twice_to_a_mandate(mclient, h, knowledge):
    inst = mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    knowledge.add("C1", "DV1")
    knowledge.add("C2", "DV1")
    m = _mandate(mclient, h, inst)
    src = {"document_version_id": "DV1", "chunk_id": "C1", "quote": "x"}
    assert mclient.post(f"{API}/mandates/{m['id']}/sources", json=src, headers=h).status_code == 201
    dup = mclient.post(f"{API}/mandates/{m['id']}/sources", json=src, headers=h)
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "mandate.source_duplicate"
    assert mclient.post(f"{API}/mandates/{m['id']}/sources", json={**src, "chunk_id": "C2"}, headers=h).status_code == 201
    assert len(mclient.get(f"{API}/mandates/{m['id']}", headers=h).json()["sources"]) == 2


def test_validation_workflow_and_inactive_when_source_disappears(mclient, h, knowledge, app):
    inst = mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    knowledge.add("C1", "DV1")
    m = _mandate(mclient, h, inst, sources=[{"document_version_id": "DV1", "chunk_id": "C1"}])
    # rejet sans motif refusé
    assert mclient.post(f"{API}/mandates/{m['id']}/reject", json={"note": ""}, headers=h).status_code == 422
    v = mclient.post(f"{API}/mandates/{m['id']}/validate", json={"note": "ok", "corrections": {"procedure_status": "specific"}},
                     headers=h).json()
    assert v["validation"] == "validated" and v["active"] is True and v["procedure_status"] == "specific"
    hist = mclient.get(f"{API}/mandates/{m['id']}/history", headers=h).json()
    assert [x["action"] for x in hist] == ["create", "correct", "validate"]
    # la source disparaît de la KB -> INACTIF (et exclu de l'export)
    del knowledge.chunks["C1"]
    got = mclient.get(f"{API}/mandates/{m['id']}", headers=h).json()
    assert got["active"] is False and "introuvable" in got["inactive_reason"]
    with app.state.ctx.session_factory() as s:
        assert service.export_active_mandates(s, got_ws(s), {inst}, {"DV1"}) == []
    assert mclient.delete(f"{API}/mandates/{m['id']}", headers=h).status_code == 409  # validé : rejeter d'abord
    assert mclient.post(f"{API}/mandates/{m['id']}/reject", json={"note": "obsolète"}, headers=h).json()["validation"] == "rejected"
    assert mclient.delete(f"{API}/mandates/{m['id']}", headers=h).status_code == 204


def got_ws(session):  # noqa: ANN001, ANN201
    from app.workspaces.models import Workspace
    return session.query(Workspace.id).first()[0]


def test_validate_requires_a_resolvable_source(mclient, h):
    inst = mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    m = _mandate(mclient, h, inst)
    r = mclient.post(f"{API}/mandates/{m['id']}/validate", headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "mandate.validate.no_source"


def test_editing_a_validated_mandate_reopens_validation(mclient, h, knowledge):
    inst = mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    knowledge.add("C1", "DV1")
    m = _mandate(mclient, h, inst, sources=[{"document_version_id": "DV1", "chunk_id": "C1"}])
    mclient.post(f"{API}/mandates/{m['id']}/validate", headers=h)
    r = mclient.patch(f"{API}/mandates/{m['id']}", json={"description": "modifié"}, headers=h).json()
    assert r["validation"] == "proposed"


def test_export_active_mandates_is_filtered_by_document_versions(mclient, h, knowledge, app):
    a, b = mk_inst(mclient, h, "AAA"), mk_inst(mclient, h, "BBB")
    mk_action(mclient, h, "act_a")
    knowledge.add("C1", "DV1")
    knowledge.add("C2", "DV2")
    for inst, ch, dv in ((a, "C1", "DV1"), (b, "C2", "DV2")):
        m = _mandate(mclient, h, inst, sources=[{"document_version_id": dv, "chunk_id": ch}])
        mclient.post(f"{API}/mandates/{m['id']}/validate", headers=h)
    _mandate(mclient, h, a)  # proposé, sans source : jamais exporté
    with app.state.ctx.session_factory() as s:
        ws = got_ws(s)
        full = service.export_active_mandates(s, ws, {a, b}, {"DV1", "DV2"})
        assert {x["institution_id"] for x in full} == {a, b}
        only1 = service.export_active_mandates(s, ws, {a, b}, {"DV1"})  # ablation de corpus
        assert [x["institution_id"] for x in only1] == [a] and only1[0]["sources"][0]["document_version_id"] == "DV1"
        assert service.export_active_mandates(s, ws, {a, b}, set()) == []
        assert service.export_active_mandates(s, ws, {b}, {"DV1", "DV2"})[0]["institution_id"] == b


def test_csv_import_creates_proposed_mandates_without_sources(mclient, h):
    mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    dry = mclient.post(f"{API}/mandates/import-csv?dry_run=true", content=CSV, headers={**h, "content-type": "text/csv"}).json()
    assert dry["created"] == 2 and len(dry["errors"]) == 2
    assert mclient.get(f"{API}/mandates", headers=h).json() == []
    rep = mclient.post(f"{API}/mandates/import-csv", json={"csv_text": CSV}, headers=h).json()
    assert rep["created"] == 2 and {e["import_ref"] for e in rep["errors"]} == {"L03", "L04"}
    rows = mclient.get(f"{API}/mandates", headers=h).json()
    assert all(r["validation"] == "proposed" and r["origin"] == "csv_import" and r["sources"] == [] and not r["active"]
               for r in rows)
    l1, l2 = rows
    assert l1["procedure_status"] == "general" and l2["procedure_status"] == "none"
    assert "OLD-S02" in l1["notes"] and l2["dependency_text"] == "Texte à obtenir" and l2["dependency_ready"] == "no"
    again = mclient.post(f"{API}/mandates/import-csv", json={"csv_text": CSV}, headers=h).json()
    assert again["created"] == 0 and again["skipped"] == 2  # idempotent


def test_registry_review_state(mclient, h, h2):
    inst = mk_inst(mclient, h, "AAA")
    with mclient.app.state.ctx.session_factory() as s:
        ws = got_ws(s)
        assert service.registry_state(s, ws, inst) == "unreviewed"
    r = mclient.put(f"{API}/institutions/{inst}/registry-review", json={"status": "reviewed_complete", "note": "ok"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "reviewed_complete" and r.json()["reviewer"]
    assert mclient.get(f"{API}/institutions/{inst}/registry-review", headers=h).json()["status"] == "reviewed_complete"
    assert mclient.put(f"{API}/institutions/{inst}/registry-review", json={"status": "bad"}, headers=h).status_code == 422
    # autre espace : 404
    assert mclient.put(f"{API}/institutions/{inst}/registry-review", json={"status": "partial"}, headers=h2).status_code == 404


def test_workspace_isolation_and_roles(mclient, h, h2, knowledge):
    inst = mk_inst(mclient, h, "AAA")
    mk_action(mclient, h, "act_a")
    m = _mandate(mclient, h, inst)
    assert mclient.get(f"{API}/mandates/{m['id']}", headers=h2).status_code == 404
    assert mclient.post(f"{API}/mandates/{m['id']}/reject", json={"note": "x"}, headers=h2).status_code == 404
    assert mclient.get(f"{API}/mandates", headers=h2).json() == []
    assert mclient.get(f"{API}/actions", headers=h2).json() == []
    # une institution d'un autre espace est introuvable
    r = mclient.post(f"{API}/mandates", json={"institution_id": inst, "kind": "power", "action_code": "act_a"}, headers=h2)
    assert r.status_code in (404, 422)
    tok = mclient.post(f"{API}/tokens", json={"role": "observer"}, headers=h).json()["token"]
    ob = {"Authorization": f"Bearer {tok}"}
    assert mclient.get(f"{API}/mandates", headers=ob).status_code == 200
    assert mclient.post(f"{API}/actions", json={"code": "z", "label": "Z", "derivation": "referential"}, headers=ob).status_code == 403
    assert mclient.get(f"{API}/mandates").status_code == 401


def test_action_service_contract(mclient, h, app):
    mk_action(mclient, h, "act_a")
    with app.state.ctx.session_factory() as s:
        ws = got_ws(s)
        assert service.action_exists(s, ws, "act_a") and not service.action_exists(s, ws, "zz")
        assert service.list_actions(s, ws)[0]["derivation"] == "referential"
        assert app.state.ctx.services["mandates"].export_active_mandates


ACTIONS_CSV = (
    "code,label,domain,derivation,justification,reference_note\n"
    "act_x,Action X,alerting,scenario_author,Exigée par le scénario,\n"
    "act_y,Action Y,health,referential,,Loi 1\n"
    "bad code,Action invalide,alerting,scenario_author,j,\n"
    "act_z,Sans justification,alerting,scenario_author,,\n"
)


def test_actions_csv_import_dry_run_then_real_then_idempotent(mclient, h):
    """Le catalogue d'actions s'importe en CSV (essai à blanc puis réel) ; c'est un prérequis de l'import des mandats."""
    dry = mclient.post(f"{API}/actions/import-csv?dry_run=true", content=ACTIONS_CSV, headers={**h, "content-type": "text/csv"}).json()
    assert dry["dry_run"] is True and dry["created"] == 2 and len(dry["errors"]) == 2
    assert mclient.get(f"{API}/actions", headers=h).json() == []
    rep = mclient.post(f"{API}/actions/import-csv", json={"csv_text": ACTIONS_CSV}, headers=h).json()
    assert rep["created"] == 2 and {e["import_ref"] for e in rep["errors"]} == {"bad code", "act_z"}
    assert {a["code"] for a in mclient.get(f"{API}/actions", headers=h).json()} == {"act_x", "act_y"}
    again = mclient.post(f"{API}/actions/import-csv", json={"csv_text": ACTIONS_CSV}, headers=h).json()
    assert again["created"] == 0 and again["skipped"] == 2
    mk_inst(mclient, h, "AAA")  # les mandats qui citent ces actions s'importent désormais
    mand = "line_id,country,institution,kind,action,description\nL1,XX,AAA,power,act_x,Pouvoir X\n"
    assert mclient.post(f"{API}/mandates/import-csv", content=mand, headers={**h, "content-type": "text/csv"}).json()["created"] == 1


def test_mandates_import_error_tells_how_to_create_the_missing_action(mclient, h):
    mk_inst(mclient, h, "AAA")
    mand = "line_id,country,institution,kind,action,description\nL1,XX,AAA,power,inconnue,Pouvoir\n"
    rep = mclient.post(f"{API}/mandates/import-csv?dry_run=true", content=mand, headers={**h, "content-type": "text/csv"}).json()
    assert "Catalogue d'actions" in rep["errors"][0]["error"]
