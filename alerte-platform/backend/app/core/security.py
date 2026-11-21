"""Jetons : générés aléatoirement (≥ 256 bits), jamais stockés en clair (SHA-256 seul)."""
from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_token(prefix: str = "alt") -> tuple[str, str]:
    """Renvoie (jeton en clair — à montrer UNE fois —, empreinte SHA-256 à stocker)."""
    plain = f"{prefix}_{secrets.token_urlsafe(32)}"
    return plain, hash_token(plain)


def hash_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def safe_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
