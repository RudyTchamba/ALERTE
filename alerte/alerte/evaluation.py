"""Measure ALERTE against its targets (design doc 1.7):
T1 retrieval finds the right text, T2 quotes are real, T3 planned gaps are found,
T5 results are stable across runs, T6 a full drill runs in time."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from alerte import config
from alerte.knowledge.ingest import ensure_index
from alerte.knowledge.store import get_store


def eval_retrieval(k: int = 5) -> dict[str, Any]:
    ensure_index()
    store = get_store()
    qs = yaml.safe_load((config.settings.data_dir / "eval" / "questions.yaml").read_text(encoding="utf-8"))["questions"]
    rows, ok = [], 0
    for q in qs:
        hits = store.search(q["q"], k, countries=q.get("country"))
        ids = [h.chunk.doc_id for h in hits]
        good = q["expect"] in ids
        ok += good
        rows.append({"question": q["q"], "expected": q["expect"], "found": good,
                     "rank": ids.index(q["expect"]) + 1 if good else None, "top": ids[:3]})
    return {"target": "T1 >= 0.80", "score": round(ok / len(qs), 3), "passed": ok / len(qs) >= 0.8, "n": len(qs), "rows": rows}


def eval_drills(scenarios: list[str], brain: str = "offline", repeats: int = 1, runs_dir: Path | None = None) -> dict[str, Any]:
    from alerte.sim.engine import Drill
    out: dict[str, Any] = {}
    for sid in scenarios:
        runs, gap_sets = [], []
        for i in range(repeats):
            t0 = time.time()
            d = Drill(sid, brain=brain, run_dir=(runs_dir / f"eval-{sid}-{i + 1}") if runs_dir else None)
            res = d.run()
            s = res.summary
            gap_sets.append({(g.type, g.action) for g in _gaps(res.run_dir)})
            runs.append({"run": res.run_id, "seconds": round(time.time() - t0, 2), "gaps": s["gaps"],
                         "T2_quotes": s["citations"]["rate"], "T3_planned_gaps": s["expected_gap_coverage"]["rate"],
                         "ledger_ok": s["ledger"]["ok"], "fallbacks": s["llm_failures_fallback_used"]})
        stable = None
        if repeats >= 2:
            all_gaps = set().union(*gap_sets)
            in_two = sum(1 for g in all_gaps if sum(g in s for s in gap_sets) >= 2)
            stable = round(in_two / len(all_gaps), 3) if all_gaps else 1.0
        out[sid] = {"runs": runs, "T5_stability": stable,
                    "passed": {"T2 >= 0.95": all(r["T2_quotes"] >= 0.95 for r in runs),
                               "T3 >= 0.80": all(r["T3_planned_gaps"] >= 0.8 for r in runs),
                               "T6 < 20 min": all(r["seconds"] < 1200 for r in runs),
                               "T5 >= 0.80": None if stable is None else stable >= 0.8}}
    return out


def _gaps(run_dir: Path):
    import json
    from alerte.models import Gap
    return [Gap(**g) for g in json.loads((Path(run_dir) / "gaps.json").read_text(encoding="utf-8"))]
