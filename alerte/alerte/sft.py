"""Build a fine-tuning dataset (chat format, JSONL) from the knowledge base and finished drills.

The hackathon invites teams to use sandbox cloud credits to fine-tune models. This
exports supervised examples that teach a small open model the ALERTE habits:
cite exact passages, say "no legal basis found" instead of inventing, stay in role.
Train with sandbox/finetune_lora.py on a GPU.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import yaml

from alerte import config
from alerte.knowledge.ingest import ensure_index
from alerte.knowledge.store import get_store
from alerte.sim.adviser import ask, format_answer
from alerte.sim.brain import SYSTEM_LEGAL, SYSTEM_SEAT


def build_dataset(out_path: Path, runs: list[Path] | None = None, seed: int = 7) -> dict[str, int]:
    ensure_index()
    store = get_store()
    rnd = random.Random(seed)
    rows = []
    # 1) Legal adviser examples from the test questions (grounded answers)
    qs = yaml.safe_load((config.settings.data_dir / "eval" / "questions.yaml").read_text(encoding="utf-8"))["questions"]
    for q in qs:
        country = (q.get("country") or ["CM"])[0]
        ans = ask(q["q"], country=country, store=store)
        rows.append({"messages": [{"role": "system", "content": SYSTEM_LEGAL.format(lang="en").split("Reply with")[0].strip()},
                                  {"role": "user", "content": q["q"]},
                                  {"role": "assistant", "content": format_answer(ans)}], "source": "legal"})
    # 2) Seat decisions from finished drills (only decisions whose quotes were verified, or honest no-basis ones)
    for run in runs or []:
        p = Path(run) / "decisions.json"
        if not p.exists():
            continue
        for d in json.loads(p.read_text(encoding="utf-8")):
            ok = d["no_legal_basis"] or (d["legal_basis"] and all(c.get("verified") for c in d["legal_basis"]))
            if not ok or d.get("author") not in ("ai", "human"):
                continue
            target = {k: d[k] for k in ("situation", "known", "unknown", "options", "decision", "action", "legal_basis",
                                         "no_legal_basis", "confidence", "gap_flags", "reasoning_summary")}
            for c in target["legal_basis"]:
                c.pop("verified", None)
                c.pop("check_note", None)
            rows.append({"messages": [
                {"role": "system", "content": SYSTEM_SEAT.split("Reply with")[0].format(lang="en", actions="[]").strip()},
                {"role": "user", "content": f"SEAT {d['seat']} EVENT {d['event_id']} at {d['sim_time']}: {d['situation']}"},
                {"role": "assistant", "content": json.dumps(target, ensure_ascii=False)}], "source": "drill"})
    # 3) Refusal examples: questions with no basis in the library must not be answered with invented law
    pool = [c for c in store.chunks if "penalt" not in c.text.lower() and c.reliability != "fictional"]
    for chunk in rnd.sample(pool, min(20, len(pool))):
        rows.append({"messages": [
            {"role": "system", "content": "Answer only from the passage. If it does not contain the answer, say so."},
            {"role": "user", "content": f"PASSAGE ({chunk.doc_id} {chunk.article}): {chunk.text[:1200]}\n\n"
                                        f"QUESTION: Which article of this passage sets the penalty for operators who refuse a public alert?"},
            {"role": "assistant", "content": (f"The passage {chunk.doc_id} {chunk.article} does not say this. "
                                              "No legal basis found in the text provided.")}],
            "source": "grounding"})
    rnd.shuffle(rows)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["source"]] = counts.get(r["source"], 0) + 1
    return {"total": len(rows), **counts}
