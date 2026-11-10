"""Shared test fixtures: isolated folders, a built index, and a mock OpenAI-compatible AI server."""

from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def alerte_env(tmp_path_factory):
    base = tmp_path_factory.mktemp("alerte")
    os.environ["ALERTE_INDEX_DIR"] = str(base / "index")
    os.environ["ALERTE_RUNS_DIR"] = str(base / "runs")
    os.environ["ALERTE_ITU_ROOT"] = str(base / "no-itu")       # do not index the ITU corpus in unit tests
    os.environ["ALERTE_BRAIN"] = "offline"
    os.environ["ALERTE_EMBED"] = "none"
    os.environ["ALERTE_SLACK_WEBHOOK_URL"] = ""
    from alerte import config
    config.reload()
    from alerte.knowledge.ingest import build_index
    from alerte.knowledge.store import get_store
    build_index(include_itu=False, embed_provider="none")
    get_store(refresh=True)
    yield base


class _MockState:
    mode = "good"          # good | garbage | down
    calls = 0


def _answer(system: str, user: str) -> dict:
    passages = re.findall(r"- doc_id=(\S+) chunk_id=(\S+) article=(.*?) reliability=\S+ title=.*?\n  text: (.*)", user)
    cite = []
    if passages:
        doc, chunk, art, text = passages[0]
        words = text.replace("…", "").split()[:10]
        cite = [{"doc_id": doc, "chunk_id": chunk, "article": "" if art.strip() == "-" else art.strip(), "quote": " ".join(words)}]
    if "Another institution sent you a request" in system:
        action = re.search(r"action=(\w+)", user).group(1)
        holds = re.search(rf"- \w+ {action}:", user) is not None
        return {"status": "accepted" if holds else "not_our_role",
                "text": "We act." if holds else "Not our role.", "legal_basis": cite if holds else []}
    if "colleagues have just posted their decisions" in system:
        me = re.search(r"YOU ARE: .*?\((\w+)\)", user).group(1)
        stance = "object" if me in ("OPS", "ANTIC") else "agree"
        return {"stance": stance, "to": "ALL", "text": f"{me} {stance}s with the colleagues' plan for this event."}
    if "policy and legal adviser" in system:
        return {"national": "The national texts say little.", "missing": "No duty is set.", "recommendation": "Adopt a decree.",
                "citations": cite}
    acts = re.search(r"ACTIONS THIS EVENT MAY REQUIRE: (.*)", user).group(1)
    action = "" if acts.strip() == "none" else acts.split(",")[0].strip()
    me = re.search(r"ROLE CARD\ncode: (\w+)", user).group(1)
    return {"statement": f"{me} here: we take {action or 'note of this'} within our own mandate and tell the others.",
            "situation": "mock", "known": [f"{me} saw an event"], "unknown": ["validation"], "options": ["act", "refer"],
            "decision": f"Mock decision by {me}", "action": action, "legal_basis": cite, "no_legal_basis": not cite,
            "confidence": "medium", "gap_flags": [], "reasoning_summary": "mock reasoning", "requests": []}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _send(self, code: int, obj) -> None:
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._send(200, {"data": [{"id": "mock-model"}]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n))
        _MockState.calls += 1
        if _MockState.mode == "down":
            self._send(500, {"error": "server down"})
            return
        system, user = req["messages"][0]["content"], req["messages"][1]["content"]
        content = "I think the answer is maybe." if _MockState.mode == "garbage" else "```json\n" + json.dumps(_answer(system, user)) + "\n```"
        self._send(200, {"model": "mock-model", "choices": [{"message": {"content": content}}],
                         "usage": {"prompt_tokens": 10, "completion_tokens": 10}})


@pytest.fixture()
def mock_llm():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    old = {k: os.environ.get(k) for k in ("ALERTE_LLM_BASE_URL", "ALERTE_LLM_MODEL", "NO_PROXY", "no_proxy")}
    os.environ["ALERTE_LLM_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/v1"
    os.environ["ALERTE_LLM_MODEL"] = "mock-model"
    os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
    from alerte import config
    config.reload()
    _MockState.mode, _MockState.calls = "good", 0
    yield _MockState
    server.shutdown()
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    config.reload()


@pytest.fixture()
def data_dir() -> Path:
    from alerte import config
    return config.settings.data_dir
