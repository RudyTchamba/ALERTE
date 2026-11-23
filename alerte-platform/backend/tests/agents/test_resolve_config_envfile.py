"""Les profils de modèle peuvent désigner un serveur déclaré seulement dans backend/.env (ex. préréglage AWS)."""
from __future__ import annotations

import os

from app.agents import providers
from app.core.config import Settings


def test_profile_endpoint_name_resolves_from_env_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ALERTE_LLM_AWS_BASE_URL=http://localhost:8001/v1  \nOTHER_SECRET=x\n", encoding="utf-8")
    providers._ENV_CACHE.clear()
    st = Settings(data_dir=tmp_path / "d", llm_mode="scripted")
    assert providers.resolve_config("ALERTE_LLM_AWS_BASE_URL", st) == "http://localhost:8001/v1"
    assert providers.resolve_config("OTHER_SECRET", st) is None  # seuls les noms ALERTE_* sont résolus
    monkeypatch.setitem(os.environ, "ALERTE_LLM_AWS_BASE_URL", "http://env-wins/v1")
    assert providers.resolve_config("ALERTE_LLM_AWS_BASE_URL", st) == "http://env-wins/v1"
