"""Signature Ed25519 des ancres de tête du ledger.

Une ancre signée prouve qu'au moment de sa création, la tête (seq, hash) du journal d'un exercice était celle-là,
attestée par la clé de l'instance. La clé publique est publiée (`GET /ledger/public-key`) pour une vérification
externe, sans jeton. Clé : `ALERTE_SIGNING_KEY_PATH` (PEM PKCS#8) ; à défaut, une clé est créée une fois dans
`<data_dir>/keys/ledger-ed25519.pem` (droits 600). Limite : celui qui détient la clé privée peut signer.
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def verify_with_public_pem(public_pem: str, data: bytes, signature: str) -> tuple[bool, str | None]:
    """Vérifie une signature avec une clé publique PEM fournie ; renvoie (valide, key_id)."""
    try:
        key = serialization.load_pem_public_key(public_pem.encode())
        if not isinstance(key, Ed25519PublicKey):
            return False, None
        raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        kid = hashlib.sha256(raw).hexdigest()[:16]
        key.verify(base64.b64decode(signature), data)
        return True, kid
    except (InvalidSignature, ValueError, TypeError):
        return False, None


def anchor_message(exercise_id: str, seq: int, hash_: str) -> bytes:
    return f"ALERTE-ANCHOR-v1|{exercise_id}|{seq}|{hash_}".encode()


class AnchorSigner:
    def __init__(self, key: Ed25519PrivateKey) -> None:
        self._key = key
        self.public_key: Ed25519PublicKey = key.public_key()

    @classmethod
    def load_or_create(cls, path: Path) -> AnchorSigner:
        path = Path(path)
        if path.is_file():
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if not isinstance(key, Ed25519PrivateKey):
                raise ValueError("la clé de signature doit être Ed25519")
            return cls(key)
        key = Ed25519PrivateKey.generate()
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(pem)
        return cls(key)

    def sign(self, exercise_id: str, seq: int, hash_: str) -> str:
        return base64.b64encode(self._key.sign(anchor_message(exercise_id, seq, hash_))).decode()

    def verify(self, exercise_id: str, seq: int, hash_: str, signature: str) -> bool:
        try:
            self.public_key.verify(base64.b64decode(signature), anchor_message(exercise_id, seq, hash_))
            return True
        except (InvalidSignature, ValueError):
            return False

    def sign_bytes(self, data: bytes) -> str:
        return base64.b64encode(self._key.sign(data)).decode()

    def public_pem(self) -> str:
        return self.public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def key_id(self) -> str:
        raw = self.public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return hashlib.sha256(raw).hexdigest()[:16]
