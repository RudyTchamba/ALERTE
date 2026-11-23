"""One way to read a drill, whether it is running now or finished on disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alerte import config
from alerte.analysis.report import load_run
from alerte.models import Scenario
from alerte.sim.scenario import load_roles


def runs_list() -> list[Path]:
    d = config.settings.runs_dir
    if not d.exists():
        return []
    return sorted([p for p in d.iterdir() if (p / "summary.json").exists()], key=lambda p: p.stat().st_mtime, reverse=True)


def role_dicts(scenario: Scenario) -> dict[str, dict[str, str]]:
    return {c: {"name": r.name, "institution": r.institution, "kind": r.kind} for c, r in load_roles(scenario).items()}


def run_dataset(run_dir: Path) -> dict[str, Any]:
    """Everything a screen needs from a finished run."""
    data = load_run(run_dir)
    sc = Scenario(**data["scenario"])
    data["scenario_obj"] = sc
    data["roles"] = role_dicts(sc)
    return data


def ai_calls(run_dir: Path) -> list[dict[str, Any]]:
    """Every AI model call of a run (prompt and raw answer), from the logbook."""
    from alerte.sim.ledger import read_ledger
    f = Path(run_dir) / "ledger.jsonl"
    if not f.exists():
        return []
    return [{"seq": e["seq"], **e["payload"]} for e in read_ledger(f) if e["type"] == "LLM_CALL"]
