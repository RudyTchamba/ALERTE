from __future__ import annotations

import xml.etree.ElementTree as ET

from app.simulation.alerting import is_alert, sim_minutes
from tests.simulation.conftest import API
from tests.simulation.fakes import Behavior, decision

CAP = "{urn:oasis:names:tc:emergency:cap:1.2}"


def alerts(world, ex_id, who=None):
    r = world.client.get(f"{API}/exercises/{ex_id}/public-alerts", headers=who or world.obs)
    assert r.status_code == 200, r.text
    return r.json()


def test_sim_minutes_and_alert_detection():
    assert sim_minutes("J1 06:00") == 360 and sim_minutes("D2 01:30") == 1440 + 90 and sim_minutes("14h05") == 845
    assert sim_minutes("T+2h") is None and sim_minutes(None) is None
    assert is_alert("Diffuser l'alerte aux populations", None, "act")
    assert is_alert(None, "issue_flood_warning", "act")
    assert not is_alert("Diffuser l'alerte", None, "refer")  # un renvoi n'alerte personne
    assert not is_alert("Activer le plan ORSEC", "activate_emergency_plan", "act")


def test_issued_alert_is_cap_exercise_with_delay_and_blocked_one_is_not_broadcast(world):
    def script(c):
        if c.seat_code == "OPS" and c.inject["inject_ref"] == "inj-001":
            return Behavior(decision=decision("coordinate", action="Coordonner les secours"))
        if c.seat_code == "MET" and c.inject["inject_ref"] == "inj-001":
            return Behavior(decision=decision("broadcast_public_alert", action="Alerte crue", status="not_verified"))
        if c.seat_code == "DPC":
            return Behavior(decision=decision("relay_alert", action="Diffuser l'alerte aux populations"))
    world.runtime.script = script
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    r = alerts(world, ex_id)
    assert r["verdict"] == "alerted" and r["hazard"]["sim_time"] == "D1 01:00"
    by = {a["seat"]: a for a in r["alerts"]}
    assert by["MET"]["status"] == "blocked" and "cap_xml" not in by["MET"]
    first = r["first_alert"]
    assert first["seat"] == "DPC" and first["sim_time"] == "D1 02:00" and first["delay_minutes"] == 60
    root = ET.fromstring(first["cap_xml"])
    assert root.find(f"{CAP}status").text == "Exercise" and root.find(f"{CAP}scope").text == "Public"
    assert root.find(f"{CAP}info/{CAP}senderName").text == "Inst DPC"
    assert root.find(f"{CAP}info/{CAP}headline").text == "Diffuser l'alerte aux populations"


def test_silent_when_nobody_alerts_and_scoped_observer_only(world):
    world.runtime.script = lambda c: Behavior(decision=decision("coordinate", action="Coordonner les secours"))
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    assert alerts(world, ex_id)["verdict"] == "silent"
    scoped = world.token("observer", exercise_id=ex_id)
    assert alerts(world, ex_id, scoped)["first_alert"] is None
    other = world.new_exercise()
    r = world.client.get(f"{API}/exercises/{other}/public-alerts", headers=scoped)
    assert r.status_code == 403
