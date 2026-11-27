from __future__ import annotations

import pytest

from tests.agents.conftest import FakeKnowledge, FakeMandates
from tests.conftest import auth

API = "/api/v1"


@pytest.fixture
def env(client, owner, app):  # noqa: ANN001, ANN201
    ws = client.get(f"{API}/workspaces/current", headers=owner).json()["id"]
    k = FakeKnowledge()
    k.kbs = {ws: {"KB1": {"id": "KB1", "code": "NAT", "name": "National"}, "KB2": {"id": "KB2", "code": "INT", "name": "Intl"}}}
    app.state.ctx.services["knowledge"] = k
    app.state.ctx.services["mandates"] = FakeMandates()
    inst = client.post(f"{API}/institutions", json={"code": "DPC", "name": "Civil Protection"}, headers=owner).json()
    return {"ws": ws, "inst": inst["id"], "h": owner}


def mk_agent(client, env, code="DPC", **kw):  # noqa: ANN001, ANN201
    r = client.post(f"{API}/agents", json={"institution_id": env["inst"], "code": code, "name": f"Agent {code}",
                                           "mission": "Protect", **kw}, headers=env["h"])
    assert r.status_code == 201, r.text
    return r.json()


def test_model_profile_crud_and_endpoint_must_be_a_name(client, env):  # noqa: ANN001
    h = env["h"]
    r = client.post(f"{API}/model-profiles", json={"name": "local", "provider": "openai_compat",
                                                  "endpoint_ref": "ALERTE_LLM_BASE_URL", "model": "m1"}, headers=h)
    assert r.status_code == 201 and r.json()["temperature"] == 0.0
    bad = client.post(f"{API}/model-profiles", json={"name": "evil", "provider": "openai_compat",
                                                    "endpoint_ref": "http://169.254.169.254/"}, headers=h)
    assert bad.status_code == 422
    assert client.post(f"{API}/model-profiles", json={"name": "c", "provider": "cassette"}, headers=h).status_code == 422
    pid = r.json()["id"]
    assert client.patch(f"{API}/model-profiles/{pid}", json={"max_tokens": 256}, headers=h).json()["max_tokens"] == 256
    assert client.post(f"{API}/model-profiles", json={"name": "local", "provider": "scripted"}, headers=h).status_code == 409
    assert len(client.get(f"{API}/model-profiles", headers=h).json()) == 1


def test_model_profile_request_body_is_validated(client, env):  # noqa: ANN001
    h = env["h"]
    ok = client.post(f"{API}/model-profiles", headers=h, json={
        "name": "vllm-no-think", "provider": "openai_compat", "model": "m", "endpoint_ref": "ALERTE_LLM_BASE_URL",
        "extra": {"request_body": {"chat_template_kwargs": {"enable_thinking": False}}}})
    assert ok.status_code == 201, ok.text
    bad = client.post(f"{API}/model-profiles", headers=h, json={
        "name": "bad", "provider": "openai_compat", "model": "m", "endpoint_ref": "ALERTE_LLM_BASE_URL",
        "extra": {"request_body": {"model": "autre"}}})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "model_profile.request_body_invalid"


def test_model_profile_test_endpoint(client, env, monkeypatch):  # noqa: ANN001
    h = env["h"]
    s = client.post(f"{API}/model-profiles", json={"name": "s", "provider": "scripted"}, headers=h).json()
    t = client.post(f"{API}/model-profiles/{s['id']}/test", headers=h).json()
    assert t["ok"] is True and t["ai_involved"] is False and "SANS IA" in t["label"]
    monkeypatch.delenv("NOT_SET_VAR", raising=False)
    o = client.post(f"{API}/model-profiles", json={"name": "o", "provider": "openai_compat", "endpoint_ref": "NOT_SET_VAR",
                                                  "model": "m"}, headers=h).json()
    t = client.post(f"{API}/model-profiles/{o['id']}/test", headers=h).json()
    assert t["ok"] is False and "NOT_SET_VAR" in t["error"]


def test_agent_crud_validation_archive(client, env):  # noqa: ANN001
    h = env["h"]
    a = mk_agent(client, env)
    assert a["limits"] == {"max_steps": 4, "max_search_calls": 3, "max_legal_calls": 2}
    assert a["tools"] == ["search_kb", "ask_legal", "post", "decide"] and a["kb_ids"] == []
    assert client.post(f"{API}/agents", json={"institution_id": env["inst"], "code": "DPC", "name": "x"}, headers=h).status_code == 409
    assert client.post(f"{API}/agents", json={"institution_id": env["inst"], "code": "T", "name": "x", "tools": ["rm_rf"]},
                       headers=h).status_code == 422
    assert client.post(f"{API}/agents", json={"code": "NOINST", "name": "x"}, headers=h).status_code == 422
    assert client.post(f"{API}/agents", json={"code": "LEGAL", "name": "Adviser", "role_kind": "legal_adviser"},
                       headers=h).status_code == 201
    assert client.post(f"{API}/agents", json={"institution_id": "nope", "code": "Z", "name": "z"}, headers=h).status_code == 404
    up = client.patch(f"{API}/agents/{a['id']}", json={"tools": ["decide"], "limits": {"max_steps": 3}}, headers=h).json()
    assert up["tools"] == ["decide"] and up["limits"]["max_steps"] == 3 and up["limits"]["max_search_calls"] == 3
    assert client.patch(f"{API}/agents/{a['id']}", json={"limits": {"max_steps": 99}}, headers=h).status_code == 422
    assert client.post(f"{API}/agents/{a['id']}/archive", headers=h).json()["archived_at"]
    assert client.get(f"{API}/agents", headers=h).json() == [x for x in client.get(f"{API}/agents", headers=h).json()
                                                               if x["id"] != a["id"]]
    assert any(x["id"] == a["id"] for x in client.get(f"{API}/agents?include_archived=true", headers=h).json())
    assert client.patch(f"{API}/agents/{a['id']}", json={"name": "n"}, headers=h).status_code == 409


def test_kb_grants_and_access_matrix_and_clone(client, env):  # noqa: ANN001
    h = env["h"]
    a = mk_agent(client, env)
    r = client.put(f"{API}/agents/{a['id']}/kb-grants", json={"kb_ids": ["KB1", "KB2", "KB1"]}, headers=h)
    assert r.status_code == 200 and r.json()["kb_ids"] == ["KB1", "KB2"]
    assert client.put(f"{API}/agents/{a['id']}/kb-grants", json={"kb_ids": ["KB_OTHER_WORKSPACE"]}, headers=h).status_code == 404
    assert client.get(f"{API}/agents/{a['id']}", headers=h).json()["kb_ids"] == ["KB1", "KB2"]  # inchangé après l'échec
    m = client.get(f"{API}/access-matrix", headers=h).json()
    assert {(g["agent_id"], g["kb_id"]) for g in m["grants"]} == {(a["id"], "KB1"), (a["id"], "KB2")}
    assert {k["code"] for k in m["knowledge_bases"]} == {"NAT", "INT"} and m["agents"][0]["code"] == "DPC"
    c = client.post(f"{API}/agents/{a['id']}/clone", headers=h)
    assert c.status_code == 201
    cj = c.json()
    assert cj["code"] == "DPC-copy" and cj["cloned_from_id"] == a["id"] and cj["kb_ids"] == ["KB1", "KB2"] and cj["id"] != a["id"]
    c2 = client.post(f"{API}/agents/{a['id']}/clone", json={"code": "X1", "copy_grants": False}, headers=h).json()
    assert c2["code"] == "X1" and c2["kb_ids"] == []
    assert client.put(f"{API}/agents/{a['id']}/kb-grants", json={"kb_ids": []}, headers=h).json()["kb_ids"] == []


def test_grant_without_knowledge_service_is_503(client, env, app):  # noqa: ANN001
    del app.state.ctx.services["knowledge"]
    a = mk_agent(client, env)
    assert client.put(f"{API}/agents/{a['id']}/kb-grants", json={"kb_ids": ["KB1"]}, headers=env["h"]).status_code == 503


def test_isolation_between_workspaces(client, env):  # noqa: ANN001
    a = mk_agent(client, env)
    other = auth(client.post(f"{API}/workspaces", json={"name": "Autre"}, headers=env["h"]).json()["owner_token"])
    prof = client.post(f"{API}/model-profiles", json={"name": "s", "provider": "scripted"}, headers=env["h"]).json()
    assert client.get(f"{API}/agents/{a['id']}", headers=other).status_code == 404
    for method, path, body in [("patch", f"/agents/{a['id']}", {"name": "x"}), ("post", f"/agents/{a['id']}/archive", None),
                               ("post", f"/agents/{a['id']}/clone", None), ("get", f"/agents/{a['id']}/prompt-preview", None),
                               ("put", f"/agents/{a['id']}/kb-grants", {"kb_ids": []}), ("get", f"/model-profiles/{prof['id']}", None),
                               ("post", f"/model-profiles/{prof['id']}/test", None), ("delete", f"/agents/{a['id']}", None)]:
        r = getattr(client, method)(API + path, headers=other, **({"json": body} if body is not None else {}))
        assert r.status_code == 404, (method, path, r.status_code)
    assert client.get(f"{API}/agents", headers=other).json() == []
    assert client.get(f"{API}/access-matrix", headers=other).json()["agents"] == []
    # une institution d'un autre espace ne peut pas servir à créer un agent
    assert client.post(f"{API}/agents", json={"institution_id": env["inst"], "code": "Q", "name": "q"}, headers=other).status_code == 404


def test_roles_enforced(client, env):  # noqa: ANN001
    obs = auth(client.post(f"{API}/tokens", json={"role": "observer"}, headers=env["h"]).json()["token"])
    aud = auth(client.post(f"{API}/tokens", json={"role": "auditor"}, headers=env["h"]).json()["token"])
    assert client.get(f"{API}/agents", headers=obs).status_code == 403
    assert client.get(f"{API}/agents", headers=aud).status_code == 200
    assert client.post(f"{API}/agents", json={}, headers=aud).status_code == 403
    assert client.get(f"{API}/agents").status_code == 401


def test_prompt_preview_and_snapshot_have_no_secrets(client, env, app, monkeypatch):  # noqa: ANN001
    h = env["h"]
    monkeypatch.setenv("SECRET_ENDPOINT", "http://secret-host.internal:1234")
    p = client.post(f"{API}/model-profiles", json={"name": "p", "provider": "openai_compat", "endpoint_ref": "SECRET_ENDPOINT",
                                                  "model": "m"}, headers=h).json()
    a = mk_agent(client, env, model_profile_id=p["id"], instructions="Speak French")
    client.put(f"{API}/agents/{a['id']}/kb-grants", json={"kb_ids": ["KB1"]}, headers=h)
    pv = client.get(f"{API}/agents/{a['id']}/prompt-preview", headers=h).json()
    assert "## 1. Role" in pv["system_prompt"] and "Speak French" in pv["system_prompt"]
    assert "secret-host" not in pv["system_prompt"] and "SECRET_ENDPOINT" not in pv["system_prompt"]
    assert pv["approx_tokens"] < 4000 and pv["granted_kb_ids"] == ["KB1"]
    svc = app.state.ctx.services["agents"]
    from app.core.db import session_scope
    with session_scope(app.state.ctx.session_factory) as s:
        snap = svc.export_agent_snapshot(s, env["ws"], a["id"])
        assert svc.kb_grants(s, env["ws"], a["id"]) == ["KB1"]
    assert set(snap) >= {"id", "code", "role_kind", "mission", "instructions", "tools", "limits", "model_profile"}
    assert snap["model_profile"]["provider"] == "openai_compat" and snap["model_profile"]["model"] == "m"
    assert "secret-host" not in str(snap) and snap["limits"]["max_steps"] == 4
    assert svc.runtime().activate  # runtime() implémente AgentRuntimePort


def test_runtime_from_snapshot_scripted_end_to_end(client, env, app):  # noqa: ANN001
    """Agent créé par l'API → snapshot → activation scripted (étiquetée, non-IA) avec les faux services."""
    from app.contracts import SearchScope
    from app.core.db import session_scope
    from tests.agents.conftest import DV, FakeSearch, make_ctx
    h = env["h"]
    p = client.post(f"{API}/model-profiles", json={"name": "s", "provider": "scripted"}, headers=h).json()
    a = mk_agent(client, env, model_profile_id=p["id"])
    svc = app.state.ctx.services["agents"]
    app.state.ctx.services["search"] = FakeSearch(app.state.ctx.services["knowledge"])
    with session_scope(app.state.ctx.session_factory) as s:
        snap = svc.export_agent_snapshot(s, env["ws"], a["id"])
    kb = app.state.ctx.services["knowledge"]
    for c in kb.chunks.values():
        c["kb_id"] = "KB1"
    ctx = make_ctx(workspace_id=env["ws"], agent=snap, scope=SearchScope(env["ws"], frozenset({"KB1"}), frozenset({DV})))
    res = svc.runtime().activate(ctx)
    assert res.status == "ok" and res.decision["status"] == "recorded"
    assert next(e.payload for e in res.events if e.type == "LLM_CALL")["provider"] == "scripted"


def test_institution_with_agent_cannot_be_deleted(client, env):  # noqa: ANN001
    mk_agent(client, env)
    r = client.delete(f"{API}/institutions/{env['inst']}", headers=env["h"])
    assert r.status_code == 409
