"""Settings, read from environment variables and an optional `.env` file.

Every setting has a safe default so ALERTE runs with zero configuration,
fully offline, on Windows, macOS and Linux.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency). Existing env vars win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    if not value:
        return default
    p = Path(value).expanduser()
    return p if p.is_absolute() else (PROJECT_ROOT / p).resolve()


def _detect_itu_root() -> Path | None:
    """The ITU reference repo is expected one level up (ALERTE lives inside the fork)."""
    explicit = os.environ.get("ALERTE_ITU_ROOT")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        return p if p.exists() else None
    candidate = PROJECT_ROOT.parent
    if (candidate / "simulation" / "server" / "knowledge").is_dir():
        return candidate
    return None


@dataclass
class Settings:
    # Paths
    data_dir: Path = field(default_factory=lambda: _env_path("ALERTE_DATA_DIR", PROJECT_ROOT / "data"))
    index_dir: Path = field(default_factory=lambda: _env_path("ALERTE_INDEX_DIR", PROJECT_ROOT / "index"))
    runs_dir: Path = field(default_factory=lambda: _env_path("ALERTE_RUNS_DIR", PROJECT_ROOT / "runs"))
    itu_root: Path | None = field(default_factory=_detect_itu_root)
    # Extra folders whose every file is added to the knowledge base (separate several with ;)
    extra_doc_dirs: list[Path] = field(default_factory=lambda: [
        Path(x).expanduser() for x in os.environ.get("ALERTE_EXTRA_DOC_DIRS", "").split(";") if x.strip()])

    # Brain (the AI model behind the agents)
    #   offline : deterministic rule-based brain, no AI model needed (default, always works)
    #   llm     : any OpenAI-compatible endpoint (Ollama, vLLM, llama.cpp, LM Studio, sandbox)
    brain: str = field(default_factory=lambda: _env("ALERTE_BRAIN", "offline").lower())
    llm_base_url: str = field(default_factory=lambda: _env("ALERTE_LLM_BASE_URL", "http://localhost:11434/v1"))
    llm_model: str = field(default_factory=lambda: _env("ALERTE_LLM_MODEL", "qwen2.5:7b-instruct"))
    llm_api_key: str = field(default_factory=lambda: _env("ALERTE_LLM_API_KEY", "ollama"))
    llm_timeout: float = field(default_factory=lambda: float(_env("ALERTE_LLM_TIMEOUT", "180")))
    llm_temperature: float = field(default_factory=lambda: float(_env("ALERTE_LLM_TEMPERATURE", "0.2")))
    llm_max_tokens: int = field(default_factory=lambda: int(_env("ALERTE_LLM_MAX_TOKENS", "900")))

    # Embeddings (meaning-based search). "none" = keyword search only (BM25), always works.
    #   none | ollama | openai | fastembed | hash (tests only)
    embed_provider: str = field(default_factory=lambda: _env("ALERTE_EMBED", "none").lower())
    embed_model: str = field(default_factory=lambda: _env("ALERTE_EMBED_MODEL", "bge-m3"))
    embed_base_url: str = field(default_factory=lambda: _env("ALERTE_EMBED_BASE_URL", "http://localhost:11434"))

    # Simulation
    language: str = field(default_factory=lambda: _env("ALERTE_LANG", "en").lower())
    max_board_rounds: int = field(default_factory=lambda: int(_env("ALERTE_MAX_ROUNDS", "2")))
    top_k: int = field(default_factory=lambda: int(_env("ALERTE_TOP_K", "5")))
    # Seats consult the Legal Adviser agent when they find no legal basis (at most N times per drill)
    legal_consult_max: int = field(default_factory=lambda: int(_env("ALERTE_LEGAL_CONSULT_MAX", "14")))
    # Hard cap on AI model calls per drill (decisions come first, the discussion round uses what is left)
    llm_budget: int = field(default_factory=lambda: int(_env("ALERTE_LLM_BUDGET", "150")))

    # Optional Slack incoming-webhook URL for run summaries (team channel)
    slack_webhook_url: str = field(default_factory=lambda: _env("ALERTE_SLACK_WEBHOOK_URL", ""))

    @property
    def docs_dir(self) -> Path:
        return self.data_dir / "docs"

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifest.csv"

    @property
    def itu_docs_dir(self) -> Path | None:
        if self.itu_root is None:
            return None
        p = self.itu_root / "simulation" / "server" / "knowledge" / "InputDocs"
        return p if p.is_dir() else None


settings = Settings()


def reload() -> Settings:
    """Re-read settings (used by tests and the UI after changing env vars)."""
    global settings
    settings = Settings()
    return settings
