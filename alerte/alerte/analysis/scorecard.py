"""Readiness scorecard on the 13 dimensions of the ITU AI Readiness Framework (Report 2.0).

The score describes what THIS drill revealed (0 = many serious gaps, 5 = no gap found),
not an official rating of the country. Dimensions the story did not probe are
reported as "not assessed" instead of being given a made-up score.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from alerte import config
from alerte.knowledge.mandates import MandateMap
from alerte.models import DimensionScore, Gap, Scenario

# Which dimensions each gap type affects
GAP_DIMENSIONS = {
    "G1": [7, 10], "G2": [7, 3], "G3": [5, 7], "G4": [10, 1], "G5": [10, 3],
    "G6": [10], "G7": [11, 6, 4], "G8": [8, 5, 2, 9], "G9": [2, 13], "G10": [1, 10],
}
# Which dimensions a story probes, from the categories of its required actions and failure modes
CATEGORY_DIMENSIONS = {
    "alerting": [6, 7, 13], "coordination": [7, 3], "health": [3], "data": [1, 10], "inclusion": [11, 4, 6],
    "ai_oversight": [8, 5, 9, 2], "security": [2, 13], "liability": [10], "cross_border": [1, 10],
}
FAILURE_DIMENSIONS = {"language_exclusion": [4, 11], "missed_event": [13, 8], "false_alarm": [8, 2], "over_trust": [8, 9]}


@lru_cache(maxsize=2)
def dimension_names(data_dir: str) -> dict[int, str]:
    p = Path(data_dir) / "framework" / "dimensions.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    return {d["id"]: d["name"] for d in raw["dimensions"]}


def score(scenario: Scenario, mm: MandateMap, gaps: list[Gap]) -> list[DimensionScore]:
    names = dimension_names(str(config.settings.data_dir))
    probed: set[int] = set()
    for ev in scenario.events:
        for code in ev.required_actions:
            probed.update(CATEGORY_DIMENSIONS.get(mm.action(code).category, []))
        probed.update(FAILURE_DIMENSIONS.get(ev.failure_mode, []))
    penalties: dict[int, float] = {d: 0.0 for d in names}
    evidence: dict[int, list[str]] = {d: [] for d in names}
    for g in gaps:
        if g.status == "rejected":
            continue
        weight = (1.0 if g.status == "confirmed" else 0.6) * (0.5 + 0.25 * g.severity)  # severity 3 -> 1.25
        for d in GAP_DIMENSIONS.get(g.type, []):
            penalties[d] += weight
            evidence[d].append(f"{g.gap_id} {g.title}")
    out = []
    for d, name in sorted(names.items()):
        if d not in probed:
            out.append(DimensionScore(dimension_id=d, name=name, score=-1, evidence=["not assessed by this story"]))
            continue
        out.append(DimensionScore(dimension_id=d, name=name, score=round(max(0.0, 5.0 - penalties[d]), 1),
                                  evidence=evidence[d] or ["no gap found on this dimension"]))
    return out
