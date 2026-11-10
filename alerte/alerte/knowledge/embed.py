"""Embedding providers (turn text into vectors for meaning-based search).

none      : no vectors; keyword search (BM25) only. Default; works everywhere.
ollama    : local Ollama server, e.g. `ollama pull bge-m3` (multilingual) or
            `nomic-embed-text` (the ITU reference model).
openai    : any OpenAI-compatible /v1/embeddings endpoint (vLLM, LM Studio, sandbox, Ollama /v1).
fastembed : CPU-only ONNX models, no server (pip install fastembed); good for sandboxes.
hash      : deterministic hashing vectors; for tests only.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Sequence

import numpy as np

from alerte import config
from alerte.net import post_json
from alerte.textutil import tokenize

log = logging.getLogger(__name__)


class Embedder:
    name = "none"
    model = ""

    def embed(self, texts: Sequence[str]) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (m / norms).astype(np.float32)


class HashEmbedder(Embedder):
    name = "hash"

    def __init__(self, dim: int = 512):
        self.dim = dim
        self.model = f"hash-{dim}"

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in tokenize(t):
                h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
                out[i, h % self.dim] += 1.0 if (h >> 1) & 1 else -1.0
        return _normalize(out)


class OllamaEmbedder(Embedder):
    name = "ollama"

    def __init__(self, model: str, base_url: str, batch: int = 16):
        self.model, self.base_url, self.batch = model, base_url.rstrip("/"), batch

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        vecs: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            batch = [t[:2000] for t in texts[i:i + self.batch]]
            resp = post_json(f"{self.base_url}/api/embed", {"model": self.model, "input": batch}, timeout=300)
            vecs.extend(resp["embeddings"])
        return _normalize(np.array(vecs, dtype=np.float32))


class OpenAIEmbedder(Embedder):
    name = "openai"

    def __init__(self, model: str, base_url: str, api_key: str, batch: int = 32):
        self.model, self.base_url, self.api_key, self.batch = model, base_url.rstrip("/"), api_key, batch

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        vecs: list[list[float]] = []
        for i in range(0, len(texts), self.batch):
            batch = [t[:2000] for t in texts[i:i + self.batch]]
            resp = post_json(f"{self.base_url}/embeddings", {"model": self.model, "input": batch},
                             headers={"Authorization": f"Bearer {self.api_key}"}, timeout=300)
            vecs.extend(d["embedding"] for d in sorted(resp["data"], key=lambda d: d.get("index", 0)))
        return _normalize(np.array(vecs, dtype=np.float32))


class FastEmbedder(Embedder):
    name = "fastembed"

    def __init__(self, model: str):
        from fastembed import TextEmbedding  # optional dependency
        self.model = model
        try:
            self._m = TextEmbedding(model_name=model)
        except Exception as e:
            supported = [m["model"] for m in TextEmbedding.list_supported_models()]
            raise RuntimeError(f"fastembed cannot load '{model}': {e}. Supported: {supported}") from e

    def embed(self, texts: Sequence[str]) -> np.ndarray:
        return _normalize(np.array(list(self._m.embed(list(texts))), dtype=np.float32))


def get_embedder(provider: str | None = None, model: str | None = None) -> Embedder | None:
    s = config.settings
    provider = (provider or s.embed_provider or "none").lower()
    model = model or s.embed_model
    if provider in ("", "none", "off", "bm25"):
        return None
    if provider == "hash":
        return HashEmbedder()
    if provider == "ollama":
        return OllamaEmbedder(model, s.embed_base_url)
    if provider == "openai":
        base = s.embed_base_url if s.embed_base_url.rstrip("/").endswith("/v1") else s.llm_base_url
        return OpenAIEmbedder(model, base, s.llm_api_key)
    if provider == "fastembed":
        fe_model = model if "/" in model else "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        return FastEmbedder(fe_model)
    raise ValueError(f"Unknown embedding provider '{provider}' (use none, ollama, openai, fastembed)")
