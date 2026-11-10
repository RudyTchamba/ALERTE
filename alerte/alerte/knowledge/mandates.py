"""The who-does-what map (mandate graph): powers, duties and leads of institutions,
each linked to an article or marked as an assumption."""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

import yaml

from alerte import config
from alerte.models import ActionDef, MandateLine


class MandateMap:
    def __init__(self, actions: dict[str, ActionDef], lines: list[MandateLine]):
        self.actions = actions
        self.lines = lines

    # -------------------------------------------------------------- queries
    def for_country(self, country: str) -> list[MandateLine]:
        return [ln for ln in self.lines if ln.country == country]

    def holders(self, action: str, country: str, kinds: tuple[str, ...] = ("power", "duty", "lead")) -> list[MandateLine]:
        return [ln for ln in self.lines if ln.country == country and ln.action == action and ln.kind in kinds]

    def institution_lines(self, institution: str, country: str) -> list[MandateLine]:
        return [ln for ln in self.lines if ln.country == country and ln.institution == institution]

    def holds(self, institution: str, action: str, country: str) -> list[MandateLine]:
        return [ln for ln in self.holders(action, country) if ln.institution == institution]

    def lead_of(self, action: str, country: str) -> str | None:
        leads = [ln.institution for ln in self.holders(action, country, ("lead",))]
        return leads[0] if len(leads) == 1 else None

    def action(self, code: str) -> ActionDef:
        return self.actions.get(code) or ActionDef(code=code, label=code.replace("_", " "))

    def to_rows(self, country: str | None = None) -> list[dict]:
        return [ln.model_dump() for ln in self.lines if country is None or ln.country == country]


def _read_lines(path: Path) -> list[MandateLine]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if (r.get("line_id") or "").strip() and not r["line_id"].startswith("#")]
    return [MandateLine(**{k: (v or "").strip() for k, v in r.items() if k}) for r in rows]


@lru_cache(maxsize=4)
def _load(data_dir: str) -> MandateMap:
    base = Path(data_dir) / "mandates"
    raw = yaml.safe_load((base / "actions.yaml").read_text(encoding="utf-8"))
    actions = {a["code"]: ActionDef(**a) for a in raw["actions"]}
    lines: list[MandateLine] = []
    for p in sorted(base.glob("*_mandates.csv")):
        lines.extend(_read_lines(p))
    unknown = {ln.action for ln in lines} - set(actions)
    if unknown:
        raise ValueError(f"mandate lines use unknown actions: {sorted(unknown)}")
    return MandateMap(actions, lines)


def load_mandates(refresh: bool = False) -> MandateMap:
    if refresh:
        _load.cache_clear()
    return _load(str(config.settings.data_dir))
