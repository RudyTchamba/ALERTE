"""Replay: rebuild what everyone knew and did at any moment of a past drill, from the logbook alone
(no AI calls)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alerte.sim.ledger import read_ledger


@dataclass
class Snapshot:
    seq: int
    sim_time: str
    events: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    board: list[dict[str, Any]] = field(default_factory=list)
    inboxes: dict[str, list[str]] = field(default_factory=dict)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    llm_calls: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


def snapshot(run_dir: Path, upto_seq: int | None = None) -> Snapshot:
    entries = read_ledger(Path(run_dir) / "ledger.jsonl")
    if upto_seq is None:
        upto_seq = entries[-1]["seq"] if entries else 0
    snap = Snapshot(seq=upto_seq, sim_time="")
    for e in entries:
        if e["seq"] > upto_seq:
            break
        snap.sim_time = e.get("sim_time") or snap.sim_time
        p, kind = e["payload"], e["type"]
        if kind == "INJECT":
            snap.events.append({"sim_time": e["sim_time"], "sender": e["actor"], **p})
            for seat in p.get("to", []):
                snap.inboxes.setdefault(seat, []).append(f"[{e['sim_time']}] {p.get('text', '')}")
        elif kind == "DECISION":
            snap.decisions.append(p)
        elif kind == "BOARD":
            snap.board.append(p)
            if p.get("type") == "REQUEST":
                snap.inboxes.setdefault(p.get("recipient", ""), []).append(f"[{e['sim_time']}] REQUEST from {p.get('sender')}: {p.get('text')}")
        elif kind == "GAP":
            snap.gaps.append(p)
        elif kind == "LLM_CALL":
            snap.llm_calls += 1
        elif kind == "ERROR":
            snap.errors.append(p)
    return snap


def timeline(run_dir: Path) -> list[dict[str, Any]]:
    """One row per logbook entry, for the replay slider."""
    return [{"seq": e["seq"], "sim_time": e.get("sim_time", ""), "type": e["type"], "actor": e["actor"]}
            for e in read_ledger(Path(run_dir) / "ledger.jsonl")]
