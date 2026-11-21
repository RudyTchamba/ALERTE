"""Identifiants ULID (triables par le temps, non devinables) — sans dépendance externe."""
from __future__ import annotations

import os
import threading
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_lock = threading.Lock()
_last_ms = 0
_last_rand = 0


def _encode(value: int, length: int) -> str:
    out = []
    for _ in range(length):
        out.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(out))


def new_id() -> str:
    """ULID monotone au sein d'un processus : 48 bits de temps (ms) + 80 bits aléatoires."""
    global _last_ms, _last_rand
    with _lock:
        ms = int(time.time() * 1000)
        if ms == _last_ms:
            _last_rand += 1  # garde l'ordre strict dans la même milliseconde
        else:
            _last_ms = ms
            _last_rand = int.from_bytes(os.urandom(10), "big")
        rand = _last_rand & ((1 << 80) - 1)
    return _encode(ms, 10) + _encode(rand, 16)


def is_ulid(value: str) -> bool:
    return len(value) == 26 and all(c in _CROCKFORD for c in value.upper())
