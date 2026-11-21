"""Journalisation structurée (JSON sur stdout). Aucun jeton, clé d'API ni prompt complet dans les logs."""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime

_SECRET = re.compile(r"(?i)(bearer\s+|token=|stream_token=|api[_-]?key=)[A-Za-z0-9._~+/=-]+")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = _SECRET.sub(r"\1***", record.getMessage())
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": msg,
        }
        for key in ("request_id", "exercise_id", "job_id", "workspace_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO", as_json: bool = True) -> None:
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if as_json else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level.upper())
    logging.getLogger("uvicorn.access").addFilter(_AccessFilter())


class _AccessFilter(logging.Filter):
    """Masque les paramètres sensibles dans les journaux d'accès."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(_SECRET.sub(r"\1***", a) if isinstance(a, str) else a for a in record.args)
        return True
