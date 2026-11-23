"""The AI-model path, tested against a mock OpenAI-compatible server (no real model needed)."""

from alerte.sim.engine import Drill
from alerte.sim.ledger import read_ledger, verify_ledger
from alerte.sim.llm_client import LLMClient, extract_json


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('Sure!\n```json\n{"a": {"b": 2}}\n```') == {"a": {"b": 2}}
    assert extract_json('Answer: {"text": "a } brace", "n": 3} thanks') == {"text": "a } brace", "n": 3}


def test_health(mock_llm):
    ok, msg = LLMClient().health()
    assert ok, msg


def test_llm_drill_records_every_call(mock_llm):
    d = Drill("cm01", brain="llm")
    res = d.run()
    entries = read_ledger(res.run_dir / "ledger.jsonl")
    calls = [e for e in entries if e["type"] == "LLM_CALL"]
    assert calls, "AI calls must be written to the logbook"
    assert all("prompt" in e["payload"] and "answer" in e["payload"] for e in calls)
    assert res.summary["citations"]["rate"] >= 0.9
    assert verify_ledger(res.run_dir / "ledger.jsonl")["ok"]
    assert res.summary["llm_failures_fallback_used"] == 0
    assert all(e["payload"].get("event_id") for e in calls if e["payload"]["kind"] in ("decide", "reply", "react"))


def test_llm_garbage_falls_back_to_rules(mock_llm):
    mock_llm.mode = "garbage"
    d = Drill("cm01", brain="llm")
    for _ in range(3):
        d.step()
    res = d.finish()
    assert res.summary["llm_failures_fallback_used"] > 0
    assert all(x.author in ("fallback", "scripted") for x in d.decisions)      # HydroSense is scripted; the rest fell back
    assert any(x.author == "fallback" for x in d.decisions)
    assert any(e["type"] == "ERROR" for e in read_ledger(res.run_dir / "ledger.jsonl"))


def test_llm_server_down_still_finishes(mock_llm):
    mock_llm.mode = "down"
    res = Drill("ae01", brain="llm").run()
    assert res.summary["gaps"] > 0 and res.summary["ledger"]["ok"]


def test_ai_decisions_are_labelled_ai_and_differ_between_seats(mock_llm):
    d = Drill("ae-core", brain="llm")
    d.step()
    d.step()
    ai = [x for x in d.decisions if x.author == "ai"]
    assert ai and all(x.statement for x in ai)
    assert len({x.statement for x in ai}) == len(ai), "each seat speaks in its own words"
    assert all(x.author == "scripted" for x in d.decisions if x.seat == "HYDRO")   # HydroSense never calls the model


def test_agents_discuss_each_others_decisions(mock_llm):
    d = Drill("ae-core", brain="llm")
    res = d.run()
    talk = [m for m in d.messages if m.round == 3]
    assert talk, "in AI mode the seats react to each other"
    assert {m.type.value for m in talk} <= {"OBJECTION", "INFO"} and all(m.author == "ai" for m in talk)
    assert any(m.type.value == "OBJECTION" for m in talk)
    assert res.summary["discussion_messages"] == len(talk)
    calls = [e for e in read_ledger(res.run_dir / "ledger.jsonl") if e["type"] == "LLM_CALL"]
    assert any(e["payload"]["kind"] == "react" for e in calls) and len(calls) <= 150


def test_call_budget_is_a_hard_cap(mock_llm, monkeypatch):
    from alerte import config
    monkeypatch.setattr(config.settings, "llm_budget", 12)
    d = Drill("ae-core", brain="llm")
    res = d.run()
    calls = [e for e in read_ledger(res.run_dir / "ledger.jsonl") if e["type"] == "LLM_CALL"]
    assert len(calls) <= 12
    assert res.summary["decisions_by_author"].get("fallback", 0) > 0   # past the cap, seats fall back and say so


def test_rule_engine_is_never_labelled_ai():
    d = Drill("ae-core", brain="offline")
    res = d.run()
    assert {x.author for x in d.decisions} <= {"rules", "scripted"}
    assert not [m for m in d.messages if m.round == 3], "the rule engine does not deliberate"
    assert "ai" not in res.summary["decisions_by_author"]
