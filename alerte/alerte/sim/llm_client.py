"""One door to any AI model: an OpenAI-compatible chat client on the standard library.

Works with Ollama (http://localhost:11434/v1), vLLM, llama.cpp server, LM Studio,
Hugging Face TGI, the ITU sandbox, or any hosted OpenAI-compatible endpoint.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from alerte import config
from alerte.net import HttpError, get_json, post_json


class LLMError(RuntimeError):
    pass


def extract_json(text: str) -> dict[str, Any]:
    """Parse the first JSON object in a model answer (handles ```json fences and chatter)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
                    break
        start = text.find("{", start + 1)
    raise LLMError("no JSON object found in the model answer")


class LLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None,
                 timeout: float | None = None, temperature: float | None = None, max_tokens: int | None = None):
        s = config.settings
        self.base_url = (base_url or s.llm_base_url).rstrip("/")
        self.model = model or s.llm_model
        self.api_key = api_key or s.llm_api_key
        self.timeout = timeout or s.llm_timeout
        self.temperature = s.llm_temperature if temperature is None else temperature
        self.max_tokens = max_tokens or s.llm_max_tokens
        self._json_mode_ok = True

    def health(self, timeout: float = 8) -> tuple[bool, str]:
        try:
            data = get_json(f"{self.base_url}/models", headers={"Authorization": f"Bearer {self.api_key}"}, timeout=timeout)
            ids = [m.get("id") for m in data.get("data", [])]
            if ids and self.model not in ids:
                return True, f"reachable; model '{self.model}' not in {ids[:8]} (it may still work)"
            return True, "reachable"
        except HttpError as e:
            return False, str(e)

    def chat(self, messages: list[dict[str, str]], json_mode: bool = True) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": self.temperature,
                                   "max_tokens": self.max_tokens, "stream": False}
        if json_mode and self._json_mode_ok:
            payload["response_format"] = {"type": "json_object"}
        t0 = time.time()
        try:
            resp = post_json(f"{self.base_url}/chat/completions", payload,
                             headers={"Authorization": f"Bearer {self.api_key}"}, timeout=self.timeout)
        except HttpError as e:
            if json_mode and self._json_mode_ok and ("response_format" in str(e) or "HTTP 400" in str(e)):
                self._json_mode_ok = False  # some servers reject response_format: retry without it
                return self.chat(messages, json_mode)
            raise LLMError(str(e)) from e
        try:
            content = resp["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"unexpected response shape: {str(resp)[:300]}") from e
        meta = {"model": resp.get("model", self.model), "seconds": round(time.time() - t0, 2),
                "usage": resp.get("usage", {})}
        return content, meta

    def chat_json(self, system: str, user: str, retries: int = 1) -> tuple[dict[str, Any], dict[str, Any]]:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        last_err: Exception | None = None
        for attempt in range(retries + 1):
            content, meta = self.chat(messages)
            meta["raw"] = content
            try:
                return extract_json(content), meta
            except LLMError as e:
                last_err = e
                messages = messages + [{"role": "assistant", "content": content},
                                       {"role": "user", "content": "Your answer was not valid JSON. Reply again with ONLY the JSON object."}]
        raise LLMError(f"invalid JSON after {retries + 1} attempts: {last_err}")
