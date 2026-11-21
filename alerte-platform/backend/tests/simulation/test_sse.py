from __future__ import annotations

import json
import time

from sqlalchemy import update

from app.core.auth import Principal
from app.core.db import session_scope, utcnow
from app.simulation import sse
from app.simulation.models import StreamToken
from tests.conftest import auth
from tests.simulation.conftest import API
from tests.simulation.test_human import decision_body, setup_human


def token_for(world, ex_id, who):
    r = world.client.post(f"{API}/exercises/{ex_id}/stream-token", headers=who)
    assert r.status_code == 200, r.text
    assert r.json()["expires_in"] == 60 and r.json()["exercise_id"] == ex_id
    return r.json()["stream_token"]


def frames(text: str) -> list[dict]:
    out = []
    for block in text.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            k, _, v = line.partition(": ")
            fields[k] = v
        if "event" in fields:
            out.append({"id": int(fields["id"]) if "id" in fields else None, "event": fields["event"],
                        "data": json.loads(fields["data"])})
    return out


def stream(world, ex_id, who, **params):
    q = "&".join([f"stream_token={token_for(world, ex_id, who)}"] + [f"{k}={v}" for k, v in params.items()])
    return world.client.get(f"{API}/exercises/{ex_id}/stream?{q}")


def done_exercise(world):
    ex_id = world.new_exercise()
    assert world.run(ex_id) == "completed"
    return ex_id


def test_stream_token_is_single_use_and_bound(world):
    ex_id = done_exercise(world)
    other = done_exercise(world)
    t = token_for(world, ex_id, world.fac)
    assert world.client.get(f"{API}/exercises/{ex_id}/stream?stream_token={t}").status_code == 200
    again = world.client.get(f"{API}/exercises/{ex_id}/stream?stream_token={t}")
    assert again.status_code == 401 and again.json()["error"]["code"] == "stream.invalid_token"
    t2 = token_for(world, ex_id, world.fac)  # lié à l'exercice
    assert world.client.get(f"{API}/exercises/{other}/stream?stream_token={t2}").status_code == 401
    assert world.client.get(f"{API}/exercises/{ex_id}/stream?stream_token=garbage").status_code == 401
    assert world.client.get(f"{API}/exercises/{ex_id}/stream").status_code == 401
    # expiré (60 s)
    t3 = token_for(world, ex_id, world.fac)
    with session_scope(world.ctx.session_factory) as s:
        s.execute(update(StreamToken).values(expires_at=utcnow().replace(year=2020)))
    assert world.client.get(f"{API}/exercises/{ex_id}/stream?stream_token={t3}").status_code == 401
    # exige une authentification pour obtenir un jeton ; pas hors espace
    assert world.client.post(f"{API}/exercises/{ex_id}/stream-token").status_code == 401


def test_stream_frames_follow_the_contract(world):
    ex_id = done_exercise(world)
    r = stream(world, ex_id, world.aud)
    assert r.headers["content-type"].startswith("text/event-stream") and r.text.startswith("retry: 3000\n\n")
    fr = frames(r.text)
    led = world.ledger(ex_id)
    assert [f["id"] for f in fr] == [e["seq"] for e in led]
    assert [f["event"] for f in fr] == [e["type"] for e in led]
    f0 = fr[0]["data"]
    assert set(f0) == {"seq", "type", "actor", "seat", "sim_time", "real_time", "visibility", "payload"}
    assert fr[-1]["event"] == "STATE" and fr[-1]["data"]["payload"]["to"] == "completed"
    dec = next(f for f in fr if f["event"] == "DECISION")
    assert dec["data"]["seat"] is not None and dec["data"]["actor"].startswith("seat:")


def test_resume_with_last_event_id_and_after_has_no_gap_no_duplicate(world):
    ex_id = done_exercise(world)
    full = [f["id"] for f in frames(stream(world, ex_id, world.aud).text)]
    for cut in (0, 1, 5, len(full) // 2, len(full) - 1, len(full)):
        t = token_for(world, ex_id, world.aud)
        r = world.client.get(f"{API}/exercises/{ex_id}/stream?stream_token={t}", headers={"Last-Event-ID": str(cut)})
        assert [f["id"] for f in frames(r.text)] == [i for i in full if i > cut], cut
        r2 = stream(world, ex_id, world.aud, after=cut)
        assert [f["id"] for f in frames(r2.text)] == [i for i in full if i > cut]
    # filtre de types : la visibilité reste imposée par le jeton
    r = stream(world, ex_id, world.aud, types="DECISION,INJECT")
    assert {f["event"] for f in frames(r.text)} == {"DECISION", "INJECT"}


def test_live_stream_is_continuous_while_the_exercise_runs(world):
    ex_id = world.new_exercise()
    world.mgr.hooks.before_step = lambda k: time.sleep(0.03)
    p = Principal(workspace_id=world.ws, role="auditor", token_id="t", exercise_id=ex_id)
    world.start(ex_id)
    got = []
    for chunk in sse.event_stream(world.ctx, p, ex_id, 0):
        for f in frames(chunk):
            got.append(f["id"])
        if len(got) == 5:  # coupure en cours d'exécution puis reprise avec Last-Event-ID
            break
    resumed = [f["id"] for c in sse.event_stream(world.ctx, p, ex_id, got[-1]) for f in frames(c)]
    world.wait(ex_id, {"completed"})
    assert got + resumed == [e["seq"] for e in world.ledger(ex_id)]


def test_role_filtering_is_server_side(world):
    from app.contracts import PostedMessage
    from tests.simulation.fakes import Behavior
    world.runtime.script = lambda c: Behavior(messages=[PostedMessage("DPC", "INFO", "fyi")]) \
        if c.seat_code == "OPS" and c.round == 1 else None
    ex_id, player = setup_human(world)
    world.client.post(f"{API}/seats/me/search", json={"query": "alerts"}, headers=player)
    world.client.post(f"{API}/seats/me/decision", json=decision_body(), headers=player)
    world.wait(ex_id, {"completed"})
    by_role = {}
    for name, who in (("aud", world.aud), ("fac", world.fac), ("obs", world.obs), ("player", player)):
        by_role[name] = frames(stream(world, ex_id, who).text)
    vis = lambda fr: {f["data"]["visibility"] for f in fr}  # noqa: E731
    assert vis(by_role["aud"]) == {"public", "board", "seat", "audit"} == vis(by_role["fac"])
    assert vis(by_role["obs"]) == {"public"}
    assert vis(by_role["player"]) == {"public", "board", "seat"}
    # le joueur ne reçoit que les événements privés de SON siège
    own_seat = {f["data"]["seat"] for f in by_role["player"] if f["data"]["visibility"] == "seat"}
    assert own_seat == {"MET"}
    assert any(f["data"]["visibility"] == "seat" and f["data"]["seat"] == "OPS" for f in by_role["aud"])
    assert not any(f["event"] in ("LLM_CALL", "CITATION_CHECK", "ERROR", "GAP", "FACILITATOR", "SNAPSHOT") for f in by_role["obs"])
    # l'observateur voit toujours l'état et les injects
    assert {"STATE", "INJECT", "DECISION"} <= {f["event"] for f in by_role["obs"]}


def test_heartbeat_and_close_on_terminal_state(world, monkeypatch):
    ex_id = world.new_exercise()
    fired = []
    world.mgr.hooks.before_step = lambda k: fired.append(1) or world.mgr.submit_command(ex_id, "pause", {}, "t") \
        if k == "inject:1:round:1:seat:OPS" and not fired else None
    world.start(ex_id)
    world.wait(ex_id, {"paused"})
    monkeypatch.setattr(sse, "HEARTBEAT_INTERVAL", 0.1)
    p = Principal(workspace_id=world.ws, role="auditor", token_id="t", exercise_id=ex_id)
    gen = sse.event_stream(world.ctx, p, ex_id, 10**6)
    assert next(gen) == "retry: 3000\n\n"
    hb = next(gen)
    gen.close()
    assert hb.startswith("event: heartbeat") and "id:" not in hb
    # reprise sur un exercice terminé : le flux se ferme sans bloquer
    world.mgr.hooks.before_step = None
    world.cmd(ex_id, "stop")
    world.wait(ex_id, {"stopped"})
    last = world.ledger(ex_id)[-1]["seq"]
    assert list(sse.event_stream(world.ctx, p, ex_id, last)) == ["retry: 3000\n\n"]


def test_stream_requires_exercise_access(world):
    ex_id = done_exercise(world)
    ws2 = world.client.post(f"{API}/workspaces", json={"name": "Other"}, headers=world.owner).json()["owner_token"]
    assert world.client.post(f"{API}/exercises/{ex_id}/stream-token", headers=auth(ws2)).status_code == 404
