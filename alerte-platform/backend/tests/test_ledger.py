from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update

from app.audit.events import EventType, Visibility
from app.audit.ledger import Ledger, genesis_hash
from app.audit.models import LedgerEvent
from app.core.db import Base, make_engine, make_sessionmaker, session_scope
from app.core.ids import new_id
from tests.conftest import auth

API = "/api/v1"


@pytest.fixture
def db(tmp_path):
    eng = make_engine(f"sqlite:///{(tmp_path / 'l.sqlite').as_posix()}")
    Base.metadata.create_all(eng, tables=[LedgerEvent.__table__, __import__("app.audit.models", fromlist=["LedgerAnchor"]).LedgerAnchor.__table__])
    return make_sessionmaker(eng), Ledger(tmp_path / "anchors")


def _fill(factory, ledger, ex, n=6):
    with session_scope(factory) as s:
        for i in range(n):
            ledger.append(s, ex, EventType.INJECT if i % 2 == 0 else EventType.BOARD, "coord",
                          {"n": i, "text": f"événement {i}", "decision_id": new_id()}, sim_time=f"D1 0{i}:00",
                          visibility=Visibility.PUBLIC)


def test_append_builds_a_gapless_hash_chain(db):
    factory, ledger = db
    ex = new_id()
    _fill(factory, ledger, ex)
    with session_scope(factory) as s:
        evs = list(s.scalars(select(LedgerEvent).where(LedgerEvent.exercise_id == ex).order_by(LedgerEvent.seq)))
        assert [e.seq for e in evs] == [1, 2, 3, 4, 5, 6]
        assert evs[0].prev_hash == genesis_hash(ex)
        assert all(evs[i].prev_hash == evs[i - 1].hash for i in range(1, 6))
        v = ledger.verify(s, ex)
        assert v["ok"] and v["checked"] == 6 and v["head_seq"] == 6


def test_verify_detects_payload_modification_and_reports_first_bad_seq(db):
    factory, ledger = db
    ex = new_id()
    _fill(factory, ledger, ex)
    with session_scope(factory) as s:  # modification d'un payload au milieu (sans toucher aux octets canoniques)
        s.execute(update(LedgerEvent).where(LedgerEvent.exercise_id == ex, LedgerEvent.seq == 3)
                  .values(payload={"n": 999}))
    with session_scope(factory) as s:
        v = ledger.verify(s, ex)
        assert not v["ok"] and v["first_bad_seq"] == 3 and "colonnes" in v["reason"]


def test_verify_detects_canonical_bytes_tampering_and_rehash_attempt(db):
    factory, ledger = db
    ex = new_id()
    _fill(factory, ledger, ex)
    with session_scope(factory) as s:
        s.execute(update(LedgerEvent).where(LedgerEvent.exercise_id == ex, LedgerEvent.seq == 2)
                  .values(canonical=b'{"forged":true}'))
    with session_scope(factory) as s:
        v = ledger.verify(s, ex)
        assert not v["ok"] and v["first_bad_seq"] == 2


def test_verify_detects_a_deleted_middle_event(db):
    factory, ledger = db
    ex = new_id()
    _fill(factory, ledger, ex)
    with session_scope(factory) as s:
        s.execute(delete(LedgerEvent).where(LedgerEvent.exercise_id == ex, LedgerEvent.seq == 4))
    with session_scope(factory) as s:
        v = ledger.verify(s, ex)
        assert not v["ok"] and v["first_bad_seq"] == 4


def test_truncation_of_the_end_is_detected_through_anchors(db):
    factory, ledger = db
    ex = new_id()
    _fill(factory, ledger, ex, n=4)
    with session_scope(factory) as s:
        ledger.write_anchor(s, ex, "round_close")
    _fill_more = 3
    with session_scope(factory) as s:
        for i in range(_fill_more):
            ledger.append(s, ex, EventType.STATE, "coord", {"i": i})
        ledger.write_anchor(s, ex, "round_close")
    with session_scope(factory) as s:
        assert ledger.verify(s, ex)["ok"]
        s.execute(delete(LedgerEvent).where(LedgerEvent.exercise_id == ex, LedgerEvent.seq > 5))  # suppression de fin
    with session_scope(factory) as s:
        v = ledger.verify(s, ex)
        assert not v["ok"] and v["truncated_after_anchor"] is True


def test_anchor_file_is_append_only_jsonl_and_cross_checked(db, tmp_path):
    factory, ledger = db
    ex = new_id()
    _fill(factory, ledger, ex, n=3)
    with session_scope(factory) as s:
        ledger.write_anchor(s, ex)
    p = tmp_path / "anchors" / f"{ex}.jsonl"
    assert p.is_file() and len(p.read_text(encoding="utf-8").splitlines()) == 1


def test_seq_is_gapless_under_concurrent_writers(db):
    factory, ledger = db
    ex = new_id()

    def work(k):
        for i in range(25):
            with session_scope(factory) as s:
                ledger.append(s, ex, EventType.TOOL_CALL, f"seat:{k}", {"k": k, "i": i})

    ts = [threading.Thread(target=work, args=(k,)) for k in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    with session_scope(factory) as s:
        v = ledger.verify(s, ex)
        assert v["ok"] and v["checked"] == 100 and v["head_seq"] == 100


def test_replay_digest_is_stable_across_exercises_but_chain_head_differs(db):
    factory, ledger = db
    a, b = new_id(), new_id()
    for ex, ms in ((a, 11), (b, 987)):
        with session_scope(factory) as s:
            ledger.append(s, ex, EventType.INJECT, "coord", {"inject": new_id(), "n": 1}, sim_time="D1 06:00",
                          visibility=Visibility.PUBLIC)
            ledger.append(s, ex, EventType.LLM_CALL, "seat:MET", {"ms": ms, "model": "m", "call": new_id(), "tokens_in": 10},
                          seat_id=new_id(), visibility=Visibility.AUDIT)
    with session_scope(factory) as s:
        assert ledger.replay_digest(s, a) == ledger.replay_digest(s, b)
        assert ledger.head(s, a)[1] != ledger.head(s, b)[1]


def test_replay_digest_changes_when_content_changes(db):
    factory, ledger = db
    a, b = new_id(), new_id()
    for ex, txt in ((a, "x"), (b, "y")):
        with session_scope(factory) as s:
            ledger.append(s, ex, EventType.BOARD, "seat:A", {"text": txt}, visibility=Visibility.BOARD)
    with session_scope(factory) as s:
        assert ledger.replay_digest(s, a) != ledger.replay_digest(s, b)


def test_read_filters_by_visibility_and_seat(db):
    factory, ledger = db
    ex, seat1, seat2 = new_id(), new_id(), new_id()
    with session_scope(factory) as s:
        ledger.append(s, ex, EventType.INJECT, "coord", {"k": "pub"}, visibility=Visibility.PUBLIC)
        ledger.append(s, ex, EventType.BOARD, "seat:A", {"k": "board"}, visibility=Visibility.BOARD)
        ledger.append(s, ex, EventType.RETRIEVAL, "seat:A", {"k": "s1"}, seat_id=seat1, visibility=Visibility.SEAT)
        ledger.append(s, ex, EventType.RETRIEVAL, "seat:B", {"k": "s2"}, seat_id=seat2, visibility=Visibility.SEAT)
        ledger.append(s, ex, EventType.LLM_CALL, "seat:A", {"k": "audit"}, visibility=Visibility.AUDIT)
    with session_scope(factory) as s:
        keys = lambda evs: [e.payload["k"] for e in evs]  # noqa: E731
        assert keys(ledger.read(s, ex, visibilities={Visibility.PUBLIC})) == ["pub"]
        assert keys(ledger.read(s, ex, visibilities={Visibility.PUBLIC, Visibility.BOARD, Visibility.SEAT}, seat_id=seat1)) == ["pub", "board", "s1"]
        assert keys(ledger.read(s, ex, visibilities={Visibility.PUBLIC, Visibility.BOARD, Visibility.SEAT, Visibility.AUDIT})) == ["pub", "board", "s1", "s2", "audit"]


def test_append_rejects_unknown_type_visibility_and_seat_without_id(db):
    factory, ledger = db
    with session_scope(factory) as s:
        with pytest.raises(ValueError):
            ledger.append(s, new_id(), "NOPE", "a", {})
        with pytest.raises(ValueError):
            ledger.append(s, new_id(), EventType.BOARD, "a", {}, visibility="secret")
        with pytest.raises(ValueError):
            ledger.append(s, new_id(), EventType.BOARD, "a", {}, visibility=Visibility.SEAT)


def test_ledger_http_routes_enforce_workspace_guard_and_role_visibility(client: TestClient, app, owner):
    ctx = app.state.ctx
    ex = new_id()
    with session_scope(ctx.session_factory) as s:
        ledger = ctx.service("ledger")
        ledger.append(s, ex, EventType.INJECT, "coord", {"k": "pub"}, visibility=Visibility.PUBLIC)
        ledger.append(s, ex, EventType.LLM_CALL, "seat:A", {"k": "audit"}, visibility=Visibility.AUDIT)
    # sans garde d'exercice enregistrée : introuvable (jamais de fuite)
    assert client.get(f"{API}/exercises/{ex}/ledger", headers=owner).status_code == 404
    ctx.services["exercise_guard"] = lambda session, p, exercise_id: None
    obs = auth(client.post(f"{API}/tokens", json={"role": "observer"}, headers=owner).json()["token"])
    assert [e["payload"]["k"] for e in client.get(f"{API}/exercises/{ex}/ledger", headers=obs).json()] == ["pub"]
    assert len(client.get(f"{API}/exercises/{ex}/ledger", headers=owner).json()) == 2
    assert client.get(f"{API}/exercises/{ex}/ledger/verify", headers=obs).status_code == 403
    v = client.get(f"{API}/exercises/{ex}/ledger/verify", headers=owner).json()
    assert v["ok"] and v["checked"] == 2
    assert client.get(f"{API}/exercises/{ex}/replay-digest", headers=owner).json()["events"] == 2
    exp = client.get(f"{API}/exercises/{ex}/ledger/export", headers=owner)
    assert exp.status_code == 200 and len(exp.text.strip().splitlines()) == 2
