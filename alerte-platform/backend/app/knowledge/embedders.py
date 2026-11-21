"""Embedders (port `contracts.Embedder`) : client OpenAI-compatible `/v1/embeddings`, FixtureEmbedder (tests), indisponible."""
from __future__ import annotations

import hashlib
import math
import re
import time
from collections.abc import Sequence

import httpx
import numpy as np

from ..contracts import EmbedderFingerprint


class EmbedderError(Exception):
    """Erreur explicite du serveur d'embeddings (jamais de clé d'API dans le message)."""


class EmbedderUnavailable(EmbedderError):
    """Serveur injoignable / expiré / non configuré → recherche en mode dégradé."""


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


class FixtureEmbedder:
    """Embedder DÉTERMINISTE pour les tests (sac de mots haché, signé, normalisé). Ce n'est PAS un modèle : jamais une preuve IA."""

    def __init__(self, dim: int = 128) -> None:
        self.fingerprint = EmbedderFingerprint(model="fixture-hashed-bow", revision="1", runtime="python",
                                               quantization="none", normalized=True, dimension=dim)
        self.calls = 0

    def ensure_fingerprint(self) -> EmbedderFingerprint:
        return self.fingerprint

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls += 1
        dim = self.fingerprint.dimension
        out = []
        for t in texts:
            v = np.zeros(dim, dtype=np.float32)
            for tok in re.findall(r"\w+", t.casefold()):
                h = hashlib.sha256(tok.encode("utf-8")).digest()
                v[int.from_bytes(h[:4], "big") % dim] += 1.0 if h[4] & 1 else -1.0
            if not v.any():
                v[0] = 1.0
            out.append(_normalize(v).tolist())
        return out


class UnavailableEmbedder:
    """Enregistré quand aucun serveur d'embeddings n'est configuré : toute requête échoue explicitement."""

    def __init__(self, reason: str = "serveur d'embeddings non configuré") -> None:
        self.reason = reason
        self.fingerprint = EmbedderFingerprint(model="unconfigured", normalized=False, dimension=0)

    def ensure_fingerprint(self) -> EmbedderFingerprint:
        raise EmbedderUnavailable(self.reason)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbedderUnavailable(self.reason)


class OpenAICompatEmbedder:
    """Client `POST {base}/v1/embeddings` (Ollama, TEI, vLLM, OpenAI…). La dimension est apprise au premier appel."""

    def __init__(self, base_url: str, model: str, api_key: str | None = None, *, batch_size: int = 16,
                 timeout_s: float = 60.0, retries: int = 2, revision: str = "", runtime: str = "openai-compat",
                 quantization: str = "", transport: httpx.BaseTransport | None = None) -> None:
        base = base_url.rstrip("/")
        self.url = base + ("/embeddings" if base.endswith("/v1") else "/v1/embeddings")
        self.model, self.batch_size, self.retries = model, max(1, batch_size), retries
        self._extra = (revision, runtime, quantization)
        self._dim = 0
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(timeout=httpx.Timeout(timeout_s, connect=5.0), headers=headers, transport=transport)

    @property
    def fingerprint(self) -> EmbedderFingerprint:
        rev, rt, q = self._extra
        return EmbedderFingerprint(model=self.model, revision=rev, runtime=rt, quantization=q, normalized=True,
                                   dimension=self._dim)

    def ensure_fingerprint(self) -> EmbedderFingerprint:
        if not self._dim:
            self.embed(["dimension probe"])
        return self.fingerprint

    def _post(self, batch: list[str]) -> list[list[float]]:
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                r = self._client.post(self.url, json={"model": self.model, "input": batch})
            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
                last = EmbedderUnavailable(f"serveur d'embeddings injoignable ({type(exc).__name__})")
            else:
                if r.status_code >= 500 or r.status_code == 429:
                    last = EmbedderUnavailable(f"serveur d'embeddings indisponible (HTTP {r.status_code})")
                elif r.status_code != 200:
                    raise EmbedderError(f"embeddings refusés (HTTP {r.status_code}) : {r.text[:200]}")
                else:
                    return self._parse(r, len(batch))
            if attempt < self.retries:
                time.sleep(0.2 * (attempt + 1))
        assert last is not None
        raise last

    def _parse(self, r: httpx.Response, n: int) -> list[list[float]]:
        try:
            items = sorted(r.json()["data"], key=lambda d: d["index"])
            vecs = [np.asarray(d["embedding"], dtype=np.float32) for d in items]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbedderError("réponse d'embeddings malformée") from exc
        if len(vecs) != n:
            raise EmbedderError(f"{len(vecs)} vecteurs reçus pour {n} textes")
        dims = {v.shape[0] for v in vecs}
        if len(dims) != 1 or 0 in dims:
            raise EmbedderError("dimensions incohérentes dans la réponse")
        dim = dims.pop()
        if self._dim and dim != self._dim:
            raise EmbedderError(f"dimension {dim} ≠ {self._dim} attendue : empreinte modifiée, refus de mélanger")
        if any(not math.isfinite(float(x)) for v in vecs for x in v):
            raise EmbedderError("vecteur non fini reçu")
        self._dim = dim
        return [_normalize(v).tolist() for v in vecs]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            out.extend(self._post([t if t.strip() else " " for t in texts[i:i + self.batch_size]]))
        return out


def build_embedder(settings, *, revision: str = "", runtime: str = "", quantization: str = ""):  # noqa: ANN001, ANN201
    if settings.embed_provider == "fixture":
        return FixtureEmbedder()
    if settings.embed_base_url and settings.embed_model:
        return OpenAICompatEmbedder(settings.embed_base_url, settings.embed_model, settings.embed_api_key,
                                    batch_size=settings.embed_batch_size, revision=revision,
                                    runtime=runtime or "openai-compat", quantization=quantization)
    return UnavailableEmbedder("ALERTE_EMBED_BASE_URL / ALERTE_EMBED_MODEL non définis")


def vec_to_blob(v: Sequence[float]) -> bytes:
    return np.asarray(v, dtype="<f4").tobytes()


def blob_to_vec(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype="<f4")
