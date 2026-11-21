"""L'`ai_mode` d'un exercice prime sur le profil de l'agent et sur `ALERTE_LLM_MODE` (régression : une démo `scripted` lancée
avec `.env` en `openai_compat` retombait en « fallback » faute d'endpoint)."""
from __future__ import annotations

from types import SimpleNamespace

from app.simulation.snapshot import effective_profile


def _ctx(mode="openai_compat", model="m"):
    return SimpleNamespace(settings=SimpleNamespace(llm_mode=mode, llm_model=model))


def _ex(ai_mode, settings=None):
    return SimpleNamespace(ai_mode=ai_mode, settings=settings or {})


def test_scripted_mode_overrides_everything():
    p = effective_profile(_ctx(), _ex("scripted"), {"provider": "openai_compat", "model": "x"})
    assert p["provider"] == "scripted"


def test_cassette_mode_uses_named_cassette():
    p = effective_profile(_ctx(), _ex("cassette", {"cassette": "run1"}), None)
    assert p["provider"] == "cassette" and p["extra"]["cassette"] == "run1"


def test_ai_mode_keeps_agent_profile_then_falls_back_to_default_server():
    own = {"provider": "openai_compat", "model": "mine", "endpoint_ref": "X"}
    assert effective_profile(_ctx(), _ex("ai"), own) == own
    d = effective_profile(_ctx(model="qwen"), _ex("ai"), None)
    assert d["provider"] == "openai_compat" and d["model"] == "qwen" and d["endpoint_ref"] == "ALERTE_LLM_BASE_URL"


def test_ai_mode_never_silently_becomes_scripted():
    assert effective_profile(_ctx(mode="scripted"), _ex("ai"), None) is None
