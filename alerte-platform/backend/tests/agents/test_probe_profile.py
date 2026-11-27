"""Sonde réelle du modèle pour la readiness (mode ai) : AgentsService.probe_profile."""
from __future__ import annotations

from types import SimpleNamespace

from app.agents.providers import ProviderUnavailable
from app.agents.setup import AgentsService
from app.core.config import Settings


class _Boom:
    def complete(self, *a, **k):  # noqa: ANN002, ANN003, ANN201
        raise ProviderUnavailable("connexion refusée http://10.1.2.3:8000/v1 : secret-token")


class _Ok:
    calls = 0

    def complete(self, *a, **k):  # noqa: ANN002, ANN003, ANN201
        _Ok.calls += 1
        return object()


def _svc(provider=None, **settings):  # noqa: ANN001, ANN202
    services = {"probe_provider": provider} if provider else {}
    ctx = SimpleNamespace(settings=Settings(_env_file=None, **settings), blobs=None, services=services, session_factory=None)
    return AgentsService(ctx)


def test_unreachable_model_is_reported_without_leaking_the_url():
    r = _svc(_Boom()).probe_profile({"provider": "openai_compat", "model": "m", "endpoint_ref": "ALERTE_LLM_BASE_URL"})
    assert r["ok"] is False and "<url>" in r["error"] and "10.1.2.3" not in r["error"]


def test_missing_endpoint_is_an_explicit_failure_not_a_silent_success(monkeypatch, tmp_path):  # noqa: ANN001
    monkeypatch.chdir(tmp_path)  # aucun .env lisible : le test ne dépend pas de la configuration locale
    monkeypatch.delenv("ALERTE_LLM_BASE_URL", raising=False)
    r = _svc().probe_profile({"provider": "openai_compat", "model": "m", "endpoint_ref": "ALERTE_LLM_BASE_URL"})
    assert r["ok"] is False and "ALERTE_LLM_BASE_URL" in r["error"]


def test_probe_result_is_cached_briefly():
    svc, prof = _svc(_Ok()), {"provider": "openai_compat", "model": "m", "endpoint_ref": "ALERTE_LLM_BASE_URL"}
    _Ok.calls = 0
    assert svc.probe_profile(prof)["ok"] and svc.probe_profile(prof)["ok"] and _Ok.calls == 1


# --- paramètres de requête (désactiver la réflexion des modèles qui la pratiquent par défaut) --------------
def test_request_body_is_sent_but_only_whitelisted_fields():
    from app.agents.providers import OpenAICompatProvider, validate_request_body
    p = OpenAICompatProvider("http://h:8000/v1", "m", extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    body = p._payload("plain", [], None, 0.0, 16)
    assert body["chat_template_kwargs"] == {"enable_thinking": False} and body["model"] == "m"
    assert "chat_template_kwargs" not in OpenAICompatProvider("http://h:8000/v1", "m")._payload("plain", [], None, 0.0, 16)
    import pytest
    with pytest.raises(ValueError, match="non autorisé"):
        validate_request_body({"model": "autre", "stream": True})  # jamais de champ arbitraire (le nom du modèle ne se change pas ici)
    with pytest.raises(ValueError, match="type attendu"):
        validate_request_body({"chat_template_kwargs": "x"})
    assert validate_request_body(None) == {}



def test_api_key_ref_can_only_name_an_alerte_variable(monkeypatch):
    """Un profil ne peut pas désigner une variable arbitraire (AWS_*, etc.) comme clé d'API envoyée au serveur configuré."""
    import pytest

    from app.agents.providers import ProviderUnavailable, provider_for
    monkeypatch.setenv("ALERTE_LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "do-not-leak")
    s = Settings(_env_file=None)
    with pytest.raises(ProviderUnavailable, match="ALERTE_"):
        provider_for({"provider": "openai_compat", "model": "m", "extra": {"api_key_ref": "AWS_SECRET_ACCESS_KEY"}}, s)
    monkeypatch.setenv("ALERTE_LLM_AWS_API_KEY", "k")
    assert provider_for({"provider": "openai_compat", "model": "m", "extra": {"api_key_ref": "ALERTE_LLM_AWS_API_KEY"}}, s).api_key == "k"
