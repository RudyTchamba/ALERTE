"""JSON canonique (esprit RFC 8785 / JCS) et empreintes SHA-256.

Clés triées, aucun espace, UTF-8, pas de NaN/Infinity. Les entiers sont écrits tels quels ; les
flottants intégrés doivent rester rares (préférer des chaînes pour les dates et les montants).
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def _check(obj: Any) -> None:
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        raise ValueError("NaN/Infinity interdits dans le JSON canonique")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise TypeError("les clés doivent être des chaînes")
            _check(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _check(v)


def canonical_bytes(obj: Any) -> bytes:
    _check(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(obj: Any) -> str:
    return sha256_hex(canonical_bytes(obj))
