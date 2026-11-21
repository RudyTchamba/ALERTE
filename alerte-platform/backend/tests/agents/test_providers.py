from __future__ import annotations

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.agents import providers
from app.agents.providers import (
    CassetteError,
    CassetteProvider,
    OpenAICompatProvider,
    ProviderUnavailable,
    RecordingProvider,
    ScriptedProvider,
    provider_for,
)
from app.contracts import LLMMessage
from app.core.config import Settings
from tests.agents.conftest import decide

MSGS = [LLMMessage("system", "sys"), LLMMessage("user", "hi")]
SCHEMA = {"title": "AlerteActionEnvelope", "type": "object"}


class FakeLLMServer:
    """Faux serveur HTTP local compatible OpenAI ; le comportement est piloté par `mode`."""

    def __init__(self) -> None:
        self.mode = "ok"
        self.requests: list[dict] = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # noqa: ANN002, ANN202
                pass

            def do_POST(self):  # noqa: ANN202
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization")})
                mode = outer.mode
                if mode == "slow":
                    time.sleep(1.0)
                if mode == "500":
                    return self._send(500, {"error": "boom"})
                if mode == "no_json_schema" and body.get("response_format", {}).get("type") == "json_schema":
                    return self._send(400, {"error": "unsupported response_format"})
                if mode == "only_plain" and ("response_format" in body or "format" in body):
                    return self._send(400, {"error": "unsupported"})
                if mode == "badbody":
                    return self._send(200, {"nope": 1})
                content = {"invalid": "this is not json", "fenced": "Here:\n```json\n{\"a\": 1}\n```"}.get(mode, '{"a": 1}')
                self._send(200, {"model": "m-served", "choices": [{"message": {"content": content}}],
                                 "usage": {"prompt_tokens": 12, "completion_tokens": 3}})

            def _send(self, code, obj):  # noqa: ANN001, ANN202
                data = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():  # noqa: ANN201
    providers._strategy_cache.clear()
    s = FakeLLMServer()
    yield s
    s.close()


def test_openai_compat_valid_response_usage_and_endpoint(server):  # noqa: ANN001
    p = OpenAICompatProvider(server.url, "my-model", api_key="k", timeout_s=5)
    raw = p.complete(MSGS, schema=SCHEMA, temperature=0.0, max_tokens=50)
    assert raw.text == '{"a": 1}' and raw.tokens_in == 12 and raw.tokens_out == 3 and raw.model == "m-served"
    assert raw.endpoint == f"{server.url}/v1/chat/completions" and raw.provider == "openai_compat"
    req = server.requests[0]
    assert req["path"] == "/v1/chat/completions" and req["body"]["temperature"] == 0.0
    assert req["body"]["response_format"]["type"] == "json_schema" and req["auth"] == "Bearer k"
    assert raw.request_sha256 == providers.request_sha256(MSGS, SCHEMA) and len(raw.response_sha256) == 64


def test_openai_compat_format_fallbacks(server):  # noqa: ANN001
    server.mode = "no_json_schema"
    raw = OpenAICompatProvider(server.url, "m", timeout_s=5).complete(MSGS, schema=SCHEMA)
    assert raw.text == '{"a": 1}'
    bodies = [r["body"] for r in server.requests]
    assert bodies[0]["response_format"]["type"] == "json_schema" and bodies[1]["format"] == SCHEMA
    providers._strategy_cache.clear()
    server.mode, server.requests = "only_plain", []
    OpenAICompatProvider(server.url, "m", timeout_s=5).complete(MSGS, schema=SCHEMA)
    assert [("response_format" in b, "format" in b) for b in (r["body"] for r in server.requests)][-1] == (False, False)
    assert len(server.requests) == 4  # json_schema, ollama format, json_object, plain


def test_openai_compat_invalid_json_is_returned_raw_and_fenced_json_extractable(server):  # noqa: ANN001
    server.mode = "invalid"
    raw = OpenAICompatProvider(server.url, "m", timeout_s=5).complete(MSGS, schema=SCHEMA)
    assert raw.text == "this is not json"  # la validation est faite par le runtime
    server.mode = "fenced"
    raw = OpenAICompatProvider(server.url, "m", timeout_s=5).complete(MSGS, schema=SCHEMA)
    assert json.loads(providers.extract_json_text(raw.text)) == {"a": 1}


def test_openai_compat_500_timeout_and_garbage_are_unavailable(server):  # noqa: ANN001
    p = OpenAICompatProvider(server.url, "m", timeout_s=0.3)
    server.mode = "500"
    with pytest.raises(ProviderUnavailable, match="500"):
        p.complete(MSGS, schema=SCHEMA)
    server.mode = "slow"
    with pytest.raises(ProviderUnavailable, match="délai"):
        p.complete(MSGS, schema=SCHEMA)
    server.mode = "badbody"
    with pytest.raises(ProviderUnavailable):
        OpenAICompatProvider(server.url, "m", timeout_s=5).complete(MSGS, schema=SCHEMA)
    with pytest.raises(ProviderUnavailable):  # connexion refusée
        OpenAICompatProvider("http://127.0.0.1:9", "m", timeout_s=1).complete(MSGS)


def test_runtime_falls_back_on_real_http_500(server, make_runtime):  # noqa: ANN001
    from tests.agents.conftest import make_ctx
    server.mode = "500"
    prov = OpenAICompatProvider(server.url, "m", timeout_s=2)
    res = make_runtime(prov).activate(make_ctx())
    assert res.status == "fallback" and res.decision["author"] == "fallback"


def test_endpoint_sanitized_and_ref_resolution(monkeypatch, tmp_path):  # noqa: ANN001
    assert providers.sanitize_endpoint("http://user:pw@host:8080/v1?key=abc") == "http://host:8080/v1"
    s = Settings(data_dir=tmp_path, llm_base_url="http://cfg.local:1234", llm_model="cfgmodel")
    p = provider_for({"provider": "openai_compat", "endpoint_ref": "ALERTE_LLM_BASE_URL"}, s)
    assert p.endpoint == "http://cfg.local:1234/v1/chat/completions" and p.model == "cfgmodel"
    monkeypatch.setenv("MY_TEAM_LLM", "http://env.local:9/v1")
    p = provider_for({"provider": "openai_compat", "endpoint_ref": "MY_TEAM_LLM", "model": "x"}, s)
    assert p.endpoint == "http://env.local:9/v1/chat/completions"
    monkeypatch.delenv("UNSET_VAR", raising=False)
    with pytest.raises(ProviderUnavailable, match="UNSET_VAR"):
        provider_for({"provider": "openai_compat", "endpoint_ref": "UNSET_VAR", "model": "x"}, s)
    # une URL n'est jamais une référence valable
    with pytest.raises(ProviderUnavailable):
        provider_for({"provider": "openai_compat", "endpoint_ref": "http://evil.example", "model": "x"}, s)


def test_scripted_is_labelled_non_ai():
    p = ScriptedProvider()
    assert p.ai_involved is False
    raw = p.complete(MSGS, schema={"title": "other"})
    assert json.loads(raw.text)["scripted"] is True and raw.provider == "scripted"
    assert provider_for({"provider": "scripted"}, Settings()).ai_involved is False


def test_cassette_replay_identical_and_divergence_detected(tmp_path):  # noqa: ANN001
    rec = RecordingProvider(ScriptedProvider())
    r1 = rec.complete(MSGS, schema=SCHEMA, step_key="step:1")
    path = tmp_path / "data" / "cassettes" / "demo.jsonl"
    rec.save(path)
    s = Settings(data_dir=tmp_path / "data")
    cas = provider_for({"provider": "cassette", "extra": {"cassette": "demo"}}, s)
    assert cas.ai_involved is True and cas.uses_step_key
    r2 = cas.complete(MSGS, schema=SCHEMA, step_key="step:1")
    assert r2.text == r1.text and r2.response_sha256 == r1.response_sha256 and r2.provider == "cassette"
    changed = [LLMMessage("system", "sys CHANGED"), MSGS[1]]
    with pytest.raises(CassetteError, match="diverg"):
        cas.complete(changed, schema=SCHEMA, step_key="step:1")
    with pytest.raises(CassetteError, match="aucune réponse"):
        cas.complete(MSGS, schema=SCHEMA, step_key="step:2")
    with pytest.raises(CassetteError):
        provider_for({"provider": "cassette", "extra": {"cassette": "../../etc/passwd"}}, s)
    with pytest.raises(CassetteError, match="introuvable"):
        provider_for({"provider": "cassette", "extra": {"cassette": "absent"}}, s)


def test_cassette_from_ledger_blobs_rerun_reproduces_decision(tmp_path, make_runtime):  # noqa: ANN001
    """Enregistre une activation, rejoue-la depuis les blobs du LLM_CALL : décision identique ; prompt changé → échec explicite."""
    from tests.agents.conftest import SEARCH, QueueProvider, make_ctx
    rec = make_runtime(RecordingProvider(QueueProvider([SEARCH, decide()])))
    first = rec.activate(make_ctx())
    calls = [e.payload for e in first.events if e.type == "LLM_CALL"]
    cas = CassetteProvider.from_llm_calls(calls, rec.blobs)
    again = make_runtime(cas)
    again.blobs = rec.blobs
    second = again.activate(make_ctx())
    strip = lambda d: {k: v for k, v in d.items() if k != "decision_id"}  # noqa: E731
    assert strip(second.decision) == strip(first.decision) and second.llm_calls == first.llm_calls
    drift = make_ctx()
    drift.inject["body"] = "A DIFFERENT TEXT"
    with pytest.raises(CassetteError):
        make_runtime(CassetteProvider.from_llm_calls(calls, rec.blobs)).activate(drift)


def test_profile_extra_cassette_required():  # noqa: ANN201
    with pytest.raises(CassetteError):
        provider_for({"provider": "cassette"}, Settings())


@pytest.mark.model
@pytest.mark.skipif(not (os.environ.get("ALERTE_LLM_BASE_URL") and os.environ.get("ALERTE_LLM_MODEL")),
                    reason="ALERTE_LLM_BASE_URL / ALERTE_LLM_MODEL non définis")
def test_real_model_produces_valid_envelopes(make_runtime):  # noqa: ANN001
    """Vrai serveur de modèles (machine d'équipe) : taux d'échec de schéma < 5 % sur 20 activations."""
    from tests.agents.conftest import make_ctx
    s = Settings()
    real = provider_for({"provider": "openai_compat", "model": s.llm_model, "endpoint_ref": "ALERTE_LLM_BASE_URL",
                         "timeout_s": 120}, s)
    assert real.ai_involved
    rt = make_runtime(real)
    bad = 0
    for _ in range(20):
        res = rt.activate(make_ctx())
        bad += res.status == "not_recorded" or any(
            e.type == "LLM_CALL" and not e.payload["valid"] for e in res.events)
    assert bad / 20 < 0.05
