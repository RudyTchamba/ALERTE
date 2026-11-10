"""Load crisis stories (scenarios) and role cards."""

from __future__ import annotations

from pathlib import Path

import yaml

from alerte import config
from alerte.models import RoleCard, Scenario


def scenarios_dir() -> Path:
    return config.settings.data_dir / "scenarios"


def list_scenarios() -> list[dict]:
    out = []
    for p in sorted(scenarios_dir().glob("*.yaml")):
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8"))
            out.append({"id": raw["id"], "title": raw["title"], "country": raw["country"],
                        "events": len(raw.get("events", [])), "file": p.name, "twin_of": raw.get("twin_of", "")})
        except Exception as e:  # a broken story must not break the app
            out.append({"id": p.stem, "title": f"(invalid: {e})", "country": "?", "events": 0, "file": p.name, "twin_of": ""})
    return out


def load_scenario(ref: str) -> Scenario:
    p = Path(ref)
    if not p.suffix:
        matches = [s for s in list_scenarios() if s["id"] == ref]
        if not matches:
            raise FileNotFoundError(f"Unknown scenario '{ref}'. Available: {[s['id'] for s in list_scenarios()]}")
        p = scenarios_dir() / matches[0]["file"]
    elif not p.is_absolute() and not p.exists():
        p = scenarios_dir() / p
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Scenario(**raw)


def load_roles(scenario: Scenario) -> dict[str, RoleCard]:
    p = scenarios_dir() / scenario.roles_file
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    roles = {r["code"]: RoleCard(**r) for r in raw["roles"]}
    for code in {c for e in scenario.events for c in e.to}:
        if code not in roles:
            raise ValueError(f"Scenario {scenario.id} sends events to unknown seat '{code}'")
    return roles
