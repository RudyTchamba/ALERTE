"""The logbook: an append-only, hash-chained record of every step of a drill.

Each line of ledger.jsonl holds a SHA-256 fingerprint of its own content plus the
fingerprint of the previous line. Editing or deleting any line breaks the chain
from that point, which `verify_ledger` detects.
"""

from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _canonical(entry: dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _digest(entry: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.seq, self.prev = 0, GENESIS
        if self.path.exists():  # resume an interrupted drill
            for entry in read_ledger(self.path):
                self.seq, self.prev = entry["seq"], entry["hash"]

    def append(self, type_: str, actor: str, payload: Any, sim_time: str = "") -> dict[str, Any]:
        with self._lock:
            entry = {
                "seq": self.seq + 1,
                "real_time": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "sim_time": sim_time,
                "type": type_,
                "actor": actor,
                "payload": payload,
                "prev_hash": self.prev,
            }
            entry["hash"] = _digest(entry)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self.seq, self.prev = entry["seq"], entry["hash"]
            return entry


def read_ledger(path: Path) -> list[dict[str, Any]]:
    out = []
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def verify_ledger(path: Path) -> dict[str, Any]:
    """Return {'ok': bool, 'entries': n, 'first_bad_seq': int|None, 'message': str}."""
    path = Path(path)
    if not path.exists():
        return {"ok": False, "entries": 0, "first_bad_seq": None, "message": f"{path} not found"}
    prev = GENESIS
    n = 0
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                return {"ok": False, "entries": n, "first_bad_seq": lineno, "message": f"line {lineno} is not valid JSON"}
            n += 1
            if entry.get("seq") != n:
                return {"ok": False, "entries": n, "first_bad_seq": entry.get("seq"),
                        "message": f"sequence broken at line {lineno} (expected {n}, found {entry.get('seq')}): an entry was removed or inserted"}
            if entry.get("prev_hash") != prev:
                return {"ok": False, "entries": n, "first_bad_seq": n, "message": f"entry {n} does not follow entry {n - 1}"}
            if _digest(entry) != entry.get("hash"):
                return {"ok": False, "entries": n, "first_bad_seq": n, "message": f"entry {n} was modified after it was written"}
            prev = entry["hash"]
    return {"ok": True, "entries": n, "first_bad_seq": None, "message": f"intact: {n} entries, chain verified"}
