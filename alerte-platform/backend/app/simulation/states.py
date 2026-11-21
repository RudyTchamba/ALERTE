"""Machine à états de l'exercice par TABLE de transitions (doc 08 §8.10). Transition absente -> 409."""
from __future__ import annotations

from ..core.errors import Conflict

DRAFT, READY, RUNNING, PAUSED, INTERRUPTED, COMPLETED, STOPPED, ARCHIVED = (
    "draft", "ready", "running", "paused", "interrupted", "completed", "stopped", "archived")
STATES = (DRAFT, READY, RUNNING, PAUSED, INTERRUPTED, COMPLETED, STOPPED, ARCHIVED)
STARTED_STATES = frozenset({RUNNING, PAUSED, INTERRUPTED, COMPLETED, STOPPED, ARCHIVED})
TERMINAL_STATES = frozenset({COMPLETED, STOPPED, ARCHIVED})

TRANSITIONS: dict[str, frozenset[str]] = {
    DRAFT: frozenset({READY}),
    READY: frozenset({DRAFT, RUNNING}),
    RUNNING: frozenset({PAUSED, INTERRUPTED, COMPLETED, STOPPED}),
    PAUSED: frozenset({RUNNING, STOPPED}),
    INTERRUPTED: frozenset({RUNNING}),
    COMPLETED: frozenset({ARCHIVED}),
    STOPPED: frozenset({ARCHIVED}),
    ARCHIVED: frozenset(),
}

COMMAND_KINDS = ("start", "pause", "resume", "step", "speed", "stop", "surprise", "seat_switch", "correction")
# commande -> états où elle est valide (`step` exige en plus pace=manual quand l'état est running)
COMMAND_STATES: dict[str, frozenset[str]] = {
    "start": frozenset({DRAFT, READY}),
    "pause": frozenset({RUNNING}),
    "resume": frozenset({PAUSED, INTERRUPTED}),
    "step": frozenset({RUNNING, PAUSED}),
    "speed": frozenset({RUNNING}),
    "stop": frozenset({RUNNING, PAUSED}),
    "surprise": frozenset({RUNNING, PAUSED}),
    "seat_switch": frozenset({RUNNING, PAUSED}),
    "correction": STARTED_STATES,
}
# état résultant d'une commande (None : l'état ne change pas)
COMMAND_TARGET = {"start": RUNNING, "pause": PAUSED, "resume": RUNNING, "stop": STOPPED}
PACES = ("manual", "auto", "auto_delay")


def can_transition(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, frozenset())


def assert_transition(src: str, dst: str) -> None:
    if not can_transition(src, dst):
        raise Conflict(f"transition interdite : {src} -> {dst}", code="exercise.invalid_transition",
                       details={"from": src, "to": dst})


def command_allowed(state: str, kind: str, pace: str = "auto") -> bool:
    if state not in COMMAND_STATES.get(kind, frozenset()):
        return False
    return not (kind == "step" and state == RUNNING and pace != "manual")


def assert_command_allowed(state: str, kind: str, pace: str = "auto") -> None:
    if not command_allowed(state, kind, pace):
        raise Conflict(f"commande '{kind}' interdite dans l'état '{state}'", code="exercise.invalid_transition",
                       details={"state": state, "command": kind})
