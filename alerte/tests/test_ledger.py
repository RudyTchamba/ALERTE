import json

from alerte.sim.ledger import Ledger, read_ledger, verify_ledger


def _make(tmp_path, n=5):
    led = Ledger(tmp_path / "ledger.jsonl")
    for i in range(n):
        led.append("TEST", "A", {"i": i, "text": "é"}, f"D1 0{i}:00")
    return tmp_path / "ledger.jsonl"


def test_intact(tmp_path):
    p = _make(tmp_path)
    r = verify_ledger(p)
    assert r["ok"] and r["entries"] == 5


def test_modified_entry_detected(tmp_path):
    p = _make(tmp_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    e = json.loads(lines[2])
    e["payload"]["i"] = 99
    lines[2] = json.dumps(e, ensure_ascii=False)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    r = verify_ledger(p)
    assert not r["ok"] and r["first_bad_seq"] == 3


def test_deleted_entry_detected(tmp_path):
    p = _make(tmp_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    del lines[1]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not verify_ledger(p)["ok"]


def test_rehashed_forgery_detected(tmp_path):
    """Changing an entry AND recomputing its own hash still breaks the next link."""
    from alerte.sim.ledger import _digest
    p = _make(tmp_path)
    lines = p.read_text(encoding="utf-8").splitlines()
    e = json.loads(lines[1])
    e["payload"]["i"] = 42
    e["hash"] = _digest(e)
    lines[1] = json.dumps(e, ensure_ascii=False)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    r = verify_ledger(p)
    assert not r["ok"] and r["first_bad_seq"] == 3


def test_resume_continues_chain(tmp_path):
    p = _make(tmp_path, 3)
    led = Ledger(p)
    led.append("TEST", "B", {"after": "resume"})
    assert verify_ledger(p)["ok"]
    assert read_ledger(p)[-1]["seq"] == 4
