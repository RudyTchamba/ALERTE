"""Configuration de l'application (12-Factor : tout passe par des variables d'environnement ALERTE_*).

Le même code tourne sur n'importe quelle machine : seule la configuration change
(URL du serveur de modèles/embeddings, dossier de données…).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALERTE_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Données -------------------------------------------------------------
    data_dir: Path = Field(default=Path("./data"), description="Racine des données (DB, blobs, index, ancres, exports)")
    db_url: str | None = Field(default=None, description="URL SQLAlchemy ; défaut : SQLite dans data_dir")
    upload_max_mb: int = 100

    # --- Serveur de modèles de génération (n'importe quelle machine) ---------
    llm_mode: Literal["openai_compat", "scripted", "cassette"] = "openai_compat"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout_s: float = 120.0
    max_llm_calls: int = 199  # T6 : < 200 appels par exercice

    # --- Serveur d'embeddings (indépendant du serveur de génération) ---------
    embed_base_url: str | None = None
    embed_api_key: str | None = None
    embed_model: str | None = None  # ex. bge-m3
    embed_provider: Literal["openai_compat", "fixture"] = "openai_compat"
    embed_batch_size: int = 16

    # --- Exécution ------------------------------------------------------------
    max_concurrent_exercises: int = 2
    job_workers: int = 2
    log_level: str = "INFO"
    log_json: bool = True

    # --- Sécurité / web ---------------------------------------------------------
    cors_origins: str = "http://localhost:5173"
    bootstrap_enabled: bool = False  # POST /workspaces : libre au premier démarrage (aucun espace) ; sinon jeton propriétaire
    signing_key_path: Path | None = None  # Ed25519 des ancres (P1)

    # --- OCR ------------------------------------------------------------------
    tessdata_dir: Path | None = None
    ocr_langs: str = "ara+fra+eng"

    @field_validator("data_dir", mode="before")
    @classmethod
    def _expand(cls, v):  # noqa: ANN001
        return Path(v).expanduser()

    # chemins dérivés -----------------------------------------------------------
    @property
    def resolved_data_dir(self) -> Path:
        return self.data_dir.resolve()

    @property
    def database_url(self) -> str:
        if self.db_url:
            return self.db_url
        return f"sqlite:///{(self.resolved_data_dir / 'db' / 'alerte.sqlite').as_posix()}"

    @property
    def blobs_dir(self) -> Path:
        return self.resolved_data_dir / "blobs"

    @property
    def vector_dir(self) -> Path:
        return self.resolved_data_dir / "vector"

    @property
    def anchors_dir(self) -> Path:
        return self.resolved_data_dir / "anchors"

    @property
    def exports_dir(self) -> Path:
        return self.resolved_data_dir / "exports"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for d in (self.resolved_data_dir, self.resolved_data_dir / "db", self.blobs_dir, self.vector_dir,
                  self.anchors_dir, self.exports_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
