"""Compare two finished drills: twin countries on the same story, or before/after a change in the law."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alerte.analysis.gaps import GAP_TYPES
from alerte.analysis.report import load_run


def compare_runs(run_a: Path, run_b: Path) -> dict[str, Any]:
    a, b = load_run(run_a), load_run(run_b)
    sa, sb = a.get("summary", {}), b.get("summary", {})
    types = sorted(set(sa.get("gaps_by_type", {})) | set(sb.get("gaps_by_type", {})), key=lambda t: int(t[1:]))
    gaps_rows = [{"type": t, "name": GAP_TYPES.get(t, t), "a": sa.get("gaps_by_type", {}).get(t, 0),
                  "b": sb.get("gaps_by_type", {}).get(t, 0)} for t in types]
    score_rows = []
    sca = {s["dimension_id"]: s for s in a.get("scorecard", [])}
    scb = {s["dimension_id"]: s for s in b.get("scorecard", [])}
    for d in sorted(set(sca) | set(scb)):
        score_rows.append({"dimension_id": d, "name": (sca.get(d) or scb.get(d))["name"],
                           "a": sca.get(d, {}).get("score", -1), "b": scb.get(d, {}).get("score", -1)})
    actions_a = {(g["type"], g["action"]) for g in a.get("gaps", [])}
    actions_b = {(g["type"], g["action"]) for g in b.get("gaps", [])}
    return {
        "a": {"run": Path(run_a).name, "country": sa.get("country"), "title": sa.get("title"), "gaps": sa.get("gaps")},
        "b": {"run": Path(run_b).name, "country": sb.get("country"), "title": sb.get("title"), "gaps": sb.get("gaps")},
        "gaps_by_type": gaps_rows, "scorecard": score_rows,
        "only_in_a": sorted(f"{t} {ac}" for t, ac in actions_a - actions_b),
        "only_in_b": sorted(f"{t} {ac}" for t, ac in actions_b - actions_a),
        "in_both": sorted(f"{t} {ac}" for t, ac in actions_a & actions_b),
    }


def compare_markdown(c: dict[str, Any]) -> str:
    A, B = c["a"]["country"], c["b"]["country"]
    L = [f"# Comparison: {c['a']['title']} vs {c['b']['title']}\n", "## Gaps by type\n",
         f"| Type | Name | {A} | {B} |", "| --- | --- | --- | --- |"]
    L += [f"| {r['type']} | {r['name']} | {r['a']} | {r['b']} |" for r in c["gaps_by_type"]]
    L += ["", "## Readiness scorecard\n", f"| # | Dimension | {A} | {B} |", "| --- | --- | --- | --- |"]
    fmt = lambda v: "not assessed" if v is None or v < 0 else f"{v:.1f}"
    L += [f"| {r['dimension_id']} | {r['name']} | {fmt(r['a'])} | {fmt(r['b'])} |" for r in c["scorecard"]]
    L += ["", f"## Gaps only in {A}\n"] + ([f"- {x}" for x in c["only_in_a"]] or ["- none"])
    L += ["", f"## Gaps only in {B}\n"] + ([f"- {x}" for x in c["only_in_b"]] or ["- none"])
    L += ["", "## Gaps in both\n"] + ([f"- {x}" for x in c["in_both"]] or ["- none"])
    return "\n".join(L) + "\n"
