from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.core.db import session_scope
from app.scenarios.faults import FAULT_CODES, FAULT_MODES
from tests.conftest import auth

API = "/api/v1"
LEGACY = Path(__file__).resolve().parents[3].parent / "alerte" / "data" / "scenarios" / "cm01_rising_waters.yaml"


class FakeMandates:
    def __init__(self) -> None:
        self.codes = {"validate_forecast": "referential", "send_alert": "scenario_author"}

    def action_exists(self, session, ws, code):  # noqa: ANN001, ANN201
        return code in self.codes

    def list_actions(self, session, ws):  # noqa: ANN001, ANN201
        return [{"code": c, "derivation": d} for c, d in self.codes.items()]


@pytest.fixture
def env(client, owner, app):  # noqa: ANN001, ANN201
    h = owner
    app.state.ctx.services["mandates"] = FakeMandates()
    c = client.post(f"{API}/countries", json={"name": "Testland", "iso2": "TL"}, headers=h).json()
    inst = {}
    for code in ("MET", "DPC", "OPS"):
        inst[code] = client.post(f"{API}/institutions", json={"code": code, "name": code, "country_id": c["id"]},
                                 headers=h).json()["id"]
    return {"h": h, "country": c["id"], "inst": inst, "ws": client.get(f"{API}/workspaces/current", headers=h).json()["id"]}


def mk_scenario(client, env, code="S1", **kw):  # noqa: ANN001, ANN201
    r = client.post(f"{API}/scenarios", json={"code": code, "title": "Floods", "country_id": env["country"], "language": "fr", **kw},
                    headers=env["h"])
    assert r.status_code == 201, r.text
    return r.json()


def mk_inject(client, env, sid, title="Inj", recipients=("MET",), **kw):  # noqa: ANN001, ANN201
    body = {"title": title, "body": "Heavy rain", "sim_time": "D1 06:00", "from_actor": "SENSORS",
            "recipients": [env["inst"][c] for c in recipients], **kw}
    r = client.post(f"{API}/scenarios/{sid}/injects", json=body, headers=env["h"])
    assert r.status_code == 201, r.text
    return r.json()


def test_fault_mode_catalogue_has_15_modes():
    assert len(FAULT_MODES) == 15 and len(FAULT_CODES) == 15
    spec12 = {"false_alarm", "missed_event", "bad_input_data", "wrong_area", "language_error", "exclusion",
              "fabricated_content", "spoofing", "over_trust", "privacy_breach", "data_leaves_country", "model_drift"}
    assert spec12 <= FAULT_CODES and {"degraded_inputs", "silent_institution", "llm_outage"} <= FAULT_CODES


def test_catalogue_endpoint_and_scenario_crud(client, env):  # noqa: ANN001
    h = env["h"]
    assert len(client.get(f"{API}/fault-modes", headers=h).json()) == 15
    s = mk_scenario(client, env)
    assert s["status"] == "draft" and s["version"] == 1 and s["inject_count"] == 0 and s["country_id"] == env["country"]
    assert client.post(f"{API}/scenarios", json={"code": "S1", "title": "x"}, headers=h).status_code == 409
    assert client.post(f"{API}/scenarios", json={"code": "S2", "title": "x", "country_id": "nope"}, headers=h).status_code == 404
    up = client.patch(f"{API}/scenarios/{s['id']}", json={"title": "New", "version": 2}, headers=h).json()
    assert up["title"] == "New" and up["version"] == 2
    assert client.get(f"{API}/scenarios/{s['id']}", headers=h).status_code == 200
    assert client.post(f"{API}/scenarios/{s['id']}/archive", headers=h).json()["status"] == "archived"
    assert client.get(f"{API}/scenarios", headers=h).json() == []
    assert len(client.get(f"{API}/scenarios?include_archived=true", headers=h).json()) == 1
    assert client.patch(f"{API}/scenarios/{s['id']}", json={"title": "x"}, headers=h).status_code == 409
    assert client.post(f"{API}/scenarios/{s['id']}/injects", json={"title": "x"}, headers=h).status_code == 409


def test_injects_ordering_insert_delete_and_validation(client, env):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    a, b, c = (mk_inject(client, env, sid, t) for t in "ABC")
    assert [a["seq"], b["seq"], c["seq"]] == [1, 2, 3]
    ins = mk_inject(client, env, sid, "X", seq=2)
    assert ins["seq"] == 2
    order = [i["title"] for i in client.get(f"{API}/scenarios/{sid}/injects", headers=h).json()]
    assert order == ["A", "X", "B", "C"]
    ids = [c["id"], a["id"], b["id"], ins["id"]]
    r = client.put(f"{API}/scenarios/{sid}/injects/order", json={"inject_ids": ids}, headers=h)
    assert [(i["title"], i["seq"]) for i in r.json()] == [("C", 1), ("A", 2), ("B", 3), ("X", 4)]
    assert client.put(f"{API}/scenarios/{sid}/injects/order", json={"inject_ids": ids[:3]}, headers=h).status_code == 422
    assert client.put(f"{API}/scenarios/{sid}/injects/order", json={"inject_ids": ids[:3] + [ids[0]]}, headers=h).status_code == 422
    assert client.delete(f"{API}/injects/{a['id']}", headers=h).status_code == 204
    assert [(i["title"], i["seq"]) for i in client.get(f"{API}/scenarios/{sid}/injects", headers=h).json()] == \
           [("C", 1), ("B", 2), ("X", 3)]
    bad = client.post(f"{API}/scenarios/{sid}/injects", json={"title": "t", "fault_mode": "gremlins"}, headers=h)
    assert bad.status_code == 422
    assert client.post(f"{API}/scenarios/{sid}/injects", json={"title": "t", "tags": ["Bad Tag"]}, headers=h).status_code == 422
    p = client.patch(f"{API}/injects/{b['id']}", json={"fault_mode": "over_trust", "tags": ["life_risk", "time_critical"],
                                                       "system_output": {"claim": "RED alert", "confidence": 0.99}}, headers=h)
    assert p.json()["fault_mode"] == "over_trust" and p.json()["tags"] == ["life_risk", "time_critical"]
    assert p.json()["system_output"]["claim"] == "RED alert"


def test_recipients_and_demands(client, env, app):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    inj = mk_inject(client, env, sid)
    r = client.put(f"{API}/injects/{inj['id']}/recipients", json={"institution_ids": [env["inst"]["DPC"], env["inst"]["OPS"]]}, headers=h)
    assert sorted(r.json()["recipients"]) == sorted([env["inst"]["DPC"], env["inst"]["OPS"]])
    assert client.put(f"{API}/injects/{inj['id']}/recipients", json={"institution_ids": ["ghost"]}, headers=h).status_code == 404
    d = client.put(f"{API}/injects/{inj['id']}/demands", json={"demands": [
        {"action_code": "validate_forecast", "justification": "forecast must be validated"}]}, headers=h)
    assert d.status_code == 200 and d.json()["demands"][0]["action_code"] == "validate_forecast" and d.json()["warnings"] == []
    u = client.put(f"{API}/injects/{inj['id']}/demands", json={"demands": [{"action_code": "nope"}]}, headers=h)
    assert u.status_code == 422 and u.json()["error"]["code"] == "inject.unknown_action"
    assert client.get(f"{API}/injects/{inj['id']}", headers=h).json()["demands"][0]["action_code"] == "validate_forecast"
    del app.state.ctx.services["mandates"]  # sans le catalogue : accepté avec avertissement
    w = client.put(f"{API}/injects/{inj['id']}/demands", json={"demands": [{"action_code": "anything"}]}, headers=h).json()
    assert w["demands"][0]["action_code"] == "anything" and w["warnings"]


def test_lint_all_cases(client, env, app):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    lint = lambda: client.get(f"{API}/scenarios/{sid}/lint", headers=h).json()  # noqa: E731
    assert {i["code"] for i in lint()["issues"]} == {"scenario.no_injects"} and lint()["ok"] is False
    no_rec = mk_inject(client, env, sid, "no recipient", recipients=())
    everyone = mk_inject(client, env, sid, "everyone", recipients=("MET", "DPC", "OPS"), fault_mode="false_alarm")
    one = mk_inject(client, env, sid, "one", recipients=("MET",), fault_mode="over_trust")
    client.put(f"{API}/injects/{one['id']}/demands", json={"demands": [{"action_code": "send_alert"}]}, headers=h)
    # une action retirée du catalogue après coup est signalée
    app.state.ctx.services["mandates"].codes.pop("send_alert")
    # destinataire archivé
    client.post(f"{API}/institutions/{env['inst']['OPS']}/archive", headers=h)
    rep = lint()
    codes = {(i["code"], i["seq"]) for i in rep["issues"]}
    assert ("inject.no_recipient", no_rec["seq"]) in codes
    assert ("inject.unknown_action", one["seq"]) in codes
    assert ("inject.unknown_recipient", everyone["seq"]) in codes
    assert ("scenario.few_fault_modes", None) in codes and rep["ok"] is False
    assert rep["stats"]["distinct_fault_modes"] == 2 and rep["stats"]["injects"] == 3
    assert rep["stats"]["estimated_llm_calls"]["max"] == (0 + 3 + 1) * 2 * 4
    # tous les destinataires (institutions actives de l'espace) -> avertissement d'inégalité d'information
    client.put(f"{API}/injects/{everyone['id']}/recipients", json={"institution_ids": [env["inst"]["MET"], env["inst"]["DPC"]]}, headers=h)
    codes = {(i["code"], i["seq"]) for i in lint()["issues"]}
    assert ("inject.all_recipients", everyone["seq"]) in codes
    sev = {i["code"]: i["severity"] for i in lint()["issues"]}
    assert sev["inject.all_recipients"] == "warning" and sev["inject.no_recipient"] == "error"


def test_lint_budget_estimate_and_six_fault_modes(client, env):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    modes = ["false_alarm", "missed_event", "over_trust", "spoofing", "privacy_breach", "llm_outage"]
    for i in range(7):
        mk_inject(client, env, sid, f"i{i}", recipients=("MET", "DPC"), fault_mode=modes[i % 6])
    rep = client.get(f"{API}/scenarios/{sid}/lint", headers=h).json()
    codes = {i["code"] for i in rep["issues"]}
    assert "scenario.few_fault_modes" not in codes and rep["stats"]["distinct_fault_modes"] == 6
    assert rep["stats"]["estimated_llm_calls"]["max"] == 7 * 2 * 2 * 4 == 112 and "scenario.budget_estimate" not in codes
    for i in range(7):
        mk_inject(client, env, sid, f"j{i}", recipients=("MET", "DPC", "OPS"), fault_mode="exclusion")
    rep = client.get(f"{API}/scenarios/{sid}/lint", headers=h).json()
    assert any(i["code"] == "scenario.budget_estimate" and i["severity"] == "warning" for i in rep["issues"])


def test_ready_requires_clean_lint(client, env):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    mk_inject(client, env, sid, recipients=())
    r = client.patch(f"{API}/scenarios/{sid}", json={"status": "ready"}, headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "scenario.lint_errors"
    inj = client.get(f"{API}/scenarios/{sid}/injects", headers=h).json()[0]
    client.put(f"{API}/injects/{inj['id']}/recipients", json={"institution_ids": [env["inst"]["MET"]]}, headers=h)
    assert client.patch(f"{API}/scenarios/{sid}", json={"status": "ready"}, headers=h).json()["status"] == "ready"


def test_clone_copies_everything_independently(client, env):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    inj = mk_inject(client, env, sid, tags=["life_risk"], fault_mode="spoofing")
    client.put(f"{API}/injects/{inj['id']}/demands", json={"demands": [{"action_code": "send_alert", "justification": "j"}]}, headers=h)
    r = client.post(f"{API}/scenarios/{sid}/clone", headers=h)
    assert r.status_code == 201 and r.json()["code"] == "S1-copy" and r.json()["cloned_from_id"] == sid and r.json()["status"] == "draft"
    cid = r.json()["id"]
    ci = client.get(f"{API}/scenarios/{cid}/injects", headers=h).json()
    assert len(ci) == 1 and ci[0]["id"] != inj["id"] and ci[0]["tags"] == ["life_risk"] and ci[0]["fault_mode"] == "spoofing"
    assert ci[0]["recipients"] == [env["inst"]["MET"]] and ci[0]["demands"][0]["justification"] == "j"
    client.delete(f"{API}/injects/{ci[0]['id']}", headers=h)
    assert len(client.get(f"{API}/scenarios/{sid}/injects", headers=h).json()) == 1
    assert client.post(f"{API}/scenarios/{sid}/clone", json={"code": "S1-copy"}, headers=h).status_code == 409


def test_yaml_roundtrip_and_import_errors(client, env):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env, description="Desc")["id"]
    a = mk_inject(client, env, sid, "Rain é", recipients=("MET", "DPC"), tags=["life_risk"], fault_mode="false_alarm",
                  system_output={"text": "RED", "p": 0.7}, source_note="note")
    client.put(f"{API}/injects/{a['id']}/demands", json={"demands": [{"action_code": "validate_forecast", "justification": "j"}]}, headers=h)
    mk_inject(client, env, sid, "Second", recipients=("OPS",))
    r = client.get(f"{API}/scenarios/{sid}/export.yaml", headers=h)
    assert r.status_code == 200 and "yaml" in r.headers["content-type"]
    doc = yaml.safe_load(r.text)
    assert doc["format"] == "alerte-scenario" and doc["scenario"]["country"] == {"iso2": "TL", "name": "Testland"}
    assert doc["injects"][0]["recipients"] == ["DPC", "MET"] and "Rain é" in r.text and str(env["ws"]) not in r.text
    # suppression du scénario puis réimport : contenu identique
    client.delete(f"{API}/scenarios/{sid}", headers=h)
    imp = client.post(f"{API}/scenarios/import", content=r.content, headers={**h, "Content-Type": "application/yaml"})
    assert imp.status_code == 201, imp.text
    assert imp.json()["warnings"] == [] and imp.json()["scenario"]["status"] == "draft"
    again = client.get(f"{API}/scenarios/{imp.json()['scenario']['id']}/export.yaml", headers=h)
    assert yaml.safe_load(again.text) == doc
    assert client.post(f"{API}/scenarios/import", content=r.content, headers=h).status_code == 409  # code déjà pris
    for bad in (b"", b"a: [unclosed", b"just: a mapping", yaml.safe_dump({"format": "alerte-scenario", "scenario": {"code": "Z"}}).encode()):
        assert client.post(f"{API}/scenarios/import", content=bad, headers=h).status_code == 422, bad


def test_yaml_import_warns_on_unknown_recipient_action_country(client, env):  # noqa: ANN001
    text = yaml.safe_dump({"format": "alerte-scenario", "format_version": 1,
                           "scenario": {"code": "IMP", "title": "T", "language": "en", "country": {"name": "Nowhere"}},
                           "injects": [{"title": "I", "recipients": ["MET", "GHOST"], "fault_mode": "over_trust",
                                        "demands": [{"action_code": "unknown_action"}]}]})
    r = client.post(f"{API}/scenarios/import", content=text.encode(), headers=env["h"])
    assert r.status_code == 201
    w = " ".join(r.json()["warnings"])
    assert "Nowhere" in w and "GHOST" in w and "unknown_action" in w
    inj = client.get(f"{API}/scenarios/{r.json()['scenario']['id']}/injects", headers=env["h"]).json()[0]
    assert inj["recipients"] == [env["inst"]["MET"]]
    bad_fm = yaml.safe_dump({"format": "alerte-scenario", "scenario": {"code": "B", "title": "T"},
                             "injects": [{"title": "I", "fault_mode": "gremlins"}]})
    assert client.post(f"{API}/scenarios/import", content=bad_fm.encode(), headers=env["h"]).status_code == 422


def test_snapshot_and_readiness_contract(client, env, app):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    a = mk_inject(client, env, sid, "A", recipients=("MET", "DPC"), tags=["life_risk"], fault_mode="over_trust",
                  system_output={"text": "RED"})
    client.put(f"{API}/injects/{a['id']}/demands", json={"demands": [
        {"action_code": "validate_forecast", "justification": "j1", "derivation": "scenario_author"}]}, headers=h)
    svc = app.state.ctx.services["scenarios"]
    with session_scope(app.state.ctx.session_factory) as s:
        snap = svc.export_scenario_snapshot(s, env["ws"], sid)
        checks = svc.readiness_scenario_checks(s, env["ws"], sid)
    assert set(snap) == {"id", "code", "title", "language", "injects"} and snap["language"] == "fr"
    inj = snap["injects"][0]
    assert set(inj) == {"inject_ref", "seq", "sim_time", "title", "body", "from_actor", "recipients", "tags", "demands",
                        "fault_mode", "system_output"}
    assert inj["inject_ref"] == "inj-001" and sorted(inj["recipients"]) == sorted([env["inst"]["MET"], env["inst"]["DPC"]])
    assert inj["tags"] == ["life_risk"] and inj["system_output"] == {"text": "RED"} and inj["fault_mode"] == "over_trust"
    # la dérivation vient du catalogue (référentiel), pas de la saisie de l'auteur
    assert inj["demands"] == [{"action_code": "validate_forecast", "derivation": "referential", "justification": "j1"}]
    assert all(set(c) >= {"id", "level", "ok", "message"} for c in checks) and all(c["ok"] for c in checks if c["level"] == "blocking")
    # sans destinataire : un contrôle bloquant échoue
    mk_inject(client, env, sid, "B", recipients=())
    with session_scope(app.state.ctx.session_factory) as s:
        bad = [c for c in svc.readiness_scenario_checks(s, env["ws"], sid) if c["id"] == "scenario.recipients"][0]
    assert bad["ok"] is False and bad["level"] == "blocking"


def test_isolation_roles_and_reference_guards(client, env):  # noqa: ANN001
    h = env["h"]
    sid = mk_scenario(client, env)["id"]
    inj = mk_inject(client, env, sid)
    other = auth(client.post(f"{API}/workspaces", json={"name": "Autre"}, headers=h).json()["owner_token"])
    for method, path, body in [("get", f"/scenarios/{sid}", None), ("patch", f"/scenarios/{sid}", {"title": "x"}),
                               ("get", f"/scenarios/{sid}/lint", None), ("get", f"/scenarios/{sid}/export.yaml", None),
                               ("post", f"/scenarios/{sid}/clone", None), ("post", f"/scenarios/{sid}/archive", None),
                               ("get", f"/scenarios/{sid}/injects", None), ("post", f"/scenarios/{sid}/injects", {"title": "x"}),
                               ("put", f"/scenarios/{sid}/injects/order", {"inject_ids": []}),
                               ("get", f"/injects/{inj['id']}", None), ("patch", f"/injects/{inj['id']}", {"title": "x"}),
                               ("delete", f"/injects/{inj['id']}", None), ("delete", f"/scenarios/{sid}", None),
                               ("put", f"/injects/{inj['id']}/recipients", {"institution_ids": []}),
                               ("put", f"/injects/{inj['id']}/demands", {"demands": []})]:
        r = getattr(client, method)(API + path, headers=other, **({"json": body} if body is not None else {}))
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get(f"{API}/scenarios", headers=other).json() == []
    # un destinataire d'un autre espace est refusé
    oc = client.post(f"{API}/institutions", json={"code": "ZZ", "name": "ZZ"}, headers=other).json()["id"]
    assert client.put(f"{API}/injects/{inj['id']}/recipients", json={"institution_ids": [oc]}, headers=h).status_code == 404
    obs = auth(client.post(f"{API}/tokens", json={"role": "observer"}, headers=h).json()["token"])
    assert client.get(f"{API}/scenarios", headers=obs).status_code == 200
    assert client.post(f"{API}/scenarios", json={"code": "Q", "title": "q"}, headers=obs).status_code == 403
    pl = auth(client.post(f"{API}/tokens", json={"role": "player"}, headers=h).json()["token"])
    assert client.get(f"{API}/scenarios", headers=pl).status_code == 403
    # gardes de référence : institution destinataire / pays du scénario non supprimables
    assert client.delete(f"{API}/institutions/{env['inst']['MET']}", headers=h).status_code == 409
    assert client.delete(f"{API}/countries/{env['country']}", headers=h).status_code == 409


@pytest.mark.skipif(not LEGACY.is_file(), reason="ancien scénario absent")
def test_realistic_legacy_scenario_content_lints(client, owner, app):  # noqa: ANN001
    """Contenu réel de l'ancien dossier (lecture seule) : 14 injects, destinataires par codes d'institutions."""
    legacy = yaml.safe_load(LEGACY.read_text(encoding="utf-8"))
    h = owner
    app.state.ctx.services["mandates"] = FakeMandates()
    codes = {c for e in legacy["events"] for c in e["to"]}
    ids = {c: client.post(f"{API}/institutions", json={"code": c, "name": c}, headers=h).json()["id"] for c in codes}
    sid = client.post(f"{API}/scenarios", json={"code": legacy["id"], "title": legacy["title"], "language": legacy["language"]},
                      headers=h).json()["id"]
    fm = {"language_exclusion": "exclusion", "data_abroad": "data_leaves_country", "": "none", None: "none"}
    for e in legacy["events"]:
        r = client.post(f"{API}/scenarios/{sid}/injects", json={
            "title": e["text"]["en"][:60], "body": e["text"]["en"], "sim_time": e["sim_time"], "from_actor": e["sender"],
            "fault_mode": fm.get(e.get("failure_mode"), e.get("failure_mode") or "none"),
            "recipients": [ids[c] for c in e["to"]]}, headers=h)
        assert r.status_code == 201, r.text
    rep = client.get(f"{API}/scenarios/{sid}/lint", headers=h).json()
    assert rep["stats"]["injects"] == len(legacy["events"]) and rep["ok"] is True
    assert rep["stats"]["distinct_fault_modes"] >= 6
    assert any(i["code"] == "scenario.budget_estimate" for i in rep["issues"])  # 15 injects à plusieurs destinataires
