from __future__ import annotations

import itertools

import pytest

from app.core.errors import Conflict
from app.simulation import states
from tests.simulation.conftest import API

ALL_PAIRS = list(itertools.product(states.STATES, states.COMMAND_KINDS))


def test_transition_table_is_closed_and_complete():
    assert set(states.TRANSITIONS) == set(states.STATES)
    for dst in (d for t in states.TRANSITIONS.values() for d in t):
        assert dst in states.STATES
    ok = {(a, b) for a, bs in states.TRANSITIONS.items() for b in bs}
    for a, b in itertools.product(states.STATES, repeat=2):
        assert states.can_transition(a, b) == ((a, b) in ok)
        if (a, b) not in ok:
            with pytest.raises(Conflict) as e:
                states.assert_transition(a, b)
            assert e.value.status_code == 409 and e.value.code == "exercise.invalid_transition"


@pytest.mark.parametrize("state,kind", ALL_PAIRS)
def test_every_state_command_pair_follows_the_table(state, kind):
    expected = state in states.COMMAND_STATES[kind]
    if kind == "step" and state == "running":
        assert states.command_allowed(state, kind, "manual") is True
        assert states.command_allowed(state, kind, "auto") is False
        return
    assert states.command_allowed(state, kind) is expected
    # chaque transition produite par une commande existe dans la table
    target = states.COMMAND_TARGET.get(kind)
    if expected and target:
        if state in (states.DRAFT,):
            assert states.can_transition(states.DRAFT, states.READY) and states.can_transition(states.READY, target)
        else:
            assert states.can_transition(state, target)


FORBIDDEN = [(s, k) for s, k in ALL_PAIRS if k != "start" and not states.command_allowed(s, k)]


@pytest.mark.parametrize("state,kind", FORBIDDEN)
def test_api_returns_409_for_every_forbidden_pair(world, state, kind):
    ex_id = world.new_exercise()
    from sqlalchemy import update

    from app.core.db import session_scope
    from app.simulation.models import Exercise
    with session_scope(world.ctx.session_factory) as s:
        s.execute(update(Exercise).where(Exercise.id == ex_id).values(state=state))
    args = {"surprise": {"title": "t", "body": "b", "recipients": ["MET"]},
            "seat_switch": {"seat": "MET", "controller": "agent"},
            "correction": {"corrects_seq": 1, "reason": "r"}, "speed": {"pace": "auto"}}.get(kind, {})
    r = world.cmd(ex_id, kind, args)
    assert r.status_code == 409 and r.json()["error"]["code"] == "exercise.invalid_transition", r.text


def test_start_from_each_non_startable_state_is_409(world):
    from sqlalchemy import update

    from app.core.db import session_scope
    from app.simulation.models import Exercise
    for state in (states.RUNNING, states.PAUSED, states.INTERRUPTED, states.COMPLETED, states.STOPPED, states.ARCHIVED):
        ex_id = world.new_exercise()
        with session_scope(world.ctx.session_factory) as s:
            s.execute(update(Exercise).where(Exercise.id == ex_id).values(state=state))
        assert world.cmd(ex_id, "start").status_code == 409


def test_unknown_command_kind_is_rejected_by_validation(world):
    ex_id = world.new_exercise()
    assert world.cmd(ex_id, "explode").status_code == 422
    assert API
