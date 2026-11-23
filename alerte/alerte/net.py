"""Tiny HTTP helpers on the standard library (no extra dependency, works everywhere)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    pass


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None,
              timeout: float = 120.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise HttpError(f"HTTP {e.code} from {url}: {body}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise HttpError(f"Cannot reach {url}: {e}") from e


def get_json(url: str, headers: dict[str, str] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise HttpError(f"HTTP {e.code} from {url}") from e
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise HttpError(f"Cannot reach {url}: {e}") from e


def download(url: str, dest: str, timeout: float = 60.0) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "ALERTE/1.0 (research; ITU AI for Good hackathon)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as fh:
        n = 0
        while True:
            block = resp.read(65536)
            if not block:
                break
            fh.write(block)
            n += len(block)
    return n
