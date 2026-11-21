"""Stockage de blobs adressé par contenu (SHA-256), portable : aucun chemin absolu n'est jamais stocké en base."""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import BinaryIO


class BlobStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, sha256: str) -> Path:
        if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
            raise ValueError("empreinte SHA-256 invalide")
        return self.root / sha256[:2] / sha256

    def exists(self, sha256: str) -> bool:
        return self.path_for(sha256).is_file()

    def put_bytes(self, data: bytes) -> str:
        sha = hashlib.sha256(data).hexdigest()
        target = self.path_for(sha)
        if target.exists():
            return sha
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return sha

    def put_stream(self, stream: BinaryIO, *, max_bytes: int | None = None, chunk: int = 1 << 20) -> tuple[str, int]:
        """Écrit un flux (upload) sans le charger en mémoire ; renvoie (sha256, taille)."""
        h = hashlib.sha256()
        size = 0
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as out:
                while True:
                    buf = stream.read(chunk)
                    if not buf:
                        break
                    size += len(buf)
                    if max_bytes is not None and size > max_bytes:
                        raise ValueError("fichier trop volumineux")
                    h.update(buf)
                    out.write(buf)
            sha = h.hexdigest()
            target = self.path_for(sha)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                os.unlink(tmp)
            else:
                os.replace(tmp, target)
            return sha, size
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def read_bytes(self, sha256: str) -> bytes:
        return self.path_for(sha256).read_bytes()

    def open(self, sha256: str) -> BinaryIO:
        return self.path_for(sha256).open("rb")

    def size(self, sha256: str) -> int:
        return self.path_for(sha256).stat().st_size

    def verify(self, sha256: str) -> bool:
        p = self.path_for(sha256)
        if not p.is_file():
            return False
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for buf in iter(lambda: fh.read(1 << 20), b""):
                h.update(buf)
        return h.hexdigest() == sha256
