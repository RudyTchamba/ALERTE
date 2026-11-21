from __future__ import annotations

from fastapi.testclient import TestClient

from app.workspaces import service as ws_service
from tests.conftest import auth

API = "/api/v1"


def test_health_and_ready(client: TestClient):
    assert client.get(f"{API}/health").json() == {"status": "ok"}
    r = client.get(f"{API}/ready")
    assert r.status_code == 200 and r.json()["checks"]["database"]["ok"] is True


def test_authentication_required_and_token_validated(client: TestClient, owner):
    assert client.get(f"{API}/countries").status_code == 401
    assert client.get(f"{API}/countries", headers=auth("faux")).status_code == 401
    r = client.get(f"{API}/countries")
    assert r.json()["error"]["code"] == "auth.missing_token"
    assert client.get(f"{API}/countries", headers=owner).status_code == 200


def test_second_workspace_requires_owner_token(client: TestClient, owner):
    assert client.post(f"{API}/workspaces", json={"name": "Autre"}).status_code == 403
    r = client.post(f"{API}/workspaces", json={"name": "Autre"}, headers=owner)
    assert r.status_code == 201


def test_token_lifecycle_roles_and_revocation(client: TestClient, owner):
    r = client.post(f"{API}/tokens", json={"role": "observer", "label": "juge"}, headers=owner)
    assert r.status_code == 201
    obs = auth(r.json()["token"])
    # un observateur lit mais n'écrit pas
    assert client.get(f"{API}/countries", headers=obs).status_code == 200
    w = client.post(f"{API}/countries", json={"name": "X"}, headers=obs)
    assert w.status_code == 403 and w.json()["error"]["code"] == "workspace.forbidden"
    # le hash seul est stocké : la liste ne révèle jamais le jeton
    listing = client.get(f"{API}/tokens", headers=owner).json()
    assert all("token" not in t and "token_hash" not in t for t in listing)
    # révocation immédiate
    tid = r.json()["info"]["id"]
    assert client.delete(f"{API}/tokens/{tid}", headers=owner).status_code == 204
    assert client.get(f"{API}/countries", headers=obs).status_code == 401


def test_expired_token_is_rejected(client: TestClient, owner, app):
    r = client.post(f"{API}/tokens", json={"role": "auditor", "expires_in_hours": 1}, headers=owner)
    tok = r.json()["token"]
    assert client.get(f"{API}/countries", headers=auth(tok)).status_code == 200
    import datetime as dt

    from sqlalchemy import update

    from app.core.db import session_scope, utcnow
    from app.workspaces.models import AccessToken
    with session_scope(app.state.ctx.session_factory) as s:
        s.execute(update(AccessToken).where(AccessToken.id == r.json()["info"]["id"])
                  .values(expires_at=utcnow() - dt.timedelta(minutes=1)))
    assert client.get(f"{API}/countries", headers=auth(tok)).status_code == 401


def test_country_and_institution_crud(client: TestClient, owner):
    c = client.post(f"{API}/countries", json={"name": "Pays A", "iso2": "pa", "languages": ["fr", "en"]}, headers=owner)
    assert c.status_code == 201 and c.json()["iso2"] == "PA"
    cid = c.json()["id"]
    assert client.post(f"{API}/countries", json={"name": "Pays A"}, headers=owner).status_code == 409
    i = client.post(f"{API}/institutions", headers=owner, json={
        "code": "MET", "name": "Service météo", "country_id": cid, "kind": "agency", "domains": ["alerting"]})
    assert i.status_code == 201
    iid = i.json()["id"]
    assert client.post(f"{API}/institutions", headers=owner, json={"code": "MET", "name": "dup"}).status_code == 409
    up = client.patch(f"{API}/institutions/{iid}", headers=owner, json={"name": "Service national de météorologie"})
    assert up.json()["name"] == "Service national de météorologie"
    assert [x["code"] for x in client.get(f"{API}/institutions?country_id={cid}", headers=owner).json()] == ["MET"]
    # suppression refusée tant que le pays est utilisé → archivage
    assert client.delete(f"{API}/countries/{cid}", headers=owner).status_code == 409
    assert client.post(f"{API}/countries/{cid}/archive", headers=owner).json()["archived_at"] is not None
    assert client.get(f"{API}/countries", headers=owner).json() == []
    assert len(client.get(f"{API}/countries?include_archived=true", headers=owner).json()) == 1
    assert client.delete(f"{API}/institutions/{iid}", headers=owner).status_code == 204


def test_validation_errors_use_the_standard_error_format(client: TestClient, owner):
    r = client.post(f"{API}/institutions", headers=owner, json={"code": "bad code!", "name": ""})
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "validation.failed" and body["details"]["errors"] and body["request_id"]


def test_workspace_isolation_between_two_workspaces(client: TestClient, owner):
    other = auth(client.post(f"{API}/workspaces", json={"name": "Autre espace"}, headers=owner).json()["owner_token"])
    c = client.post(f"{API}/countries", json={"name": "Secret"}, headers=owner).json()
    i = client.post(f"{API}/institutions", json={"code": "S1", "name": "Institution secrète", "country_id": c["id"]}, headers=owner).json()
    # l'autre espace ne voit, ne lit, ne modifie ni ne supprime rien
    assert client.get(f"{API}/countries", headers=other).json() == []
    assert client.get(f"{API}/countries/{c['id']}", headers=other).status_code == 404
    assert client.get(f"{API}/institutions/{i['id']}", headers=other).status_code == 404
    assert client.patch(f"{API}/institutions/{i['id']}", json={"name": "piraté"}, headers=other).status_code == 404
    assert client.delete(f"{API}/institutions/{i['id']}", headers=other).status_code == 404
    # et ne peut pas rattacher une institution à un pays d'un autre espace
    r = client.post(f"{API}/institutions", json={"code": "Z", "name": "z", "country_id": c["id"]}, headers=other)
    assert r.status_code == 404
    assert client.get(f"{API}/institutions/{i['id']}", headers=owner).json()["name"] == "Institution secrète"


def test_reference_guard_blocks_deletion_of_used_objects(client: TestClient, owner):
    i = client.post(f"{API}/institutions", json={"code": "G1", "name": "Gardée"}, headers=owner).json()
    ws_service.register_reference_guard(lambda session, kind, obj_id: kind == "institution" and obj_id == i["id"])
    try:
        r = client.delete(f"{API}/institutions/{i['id']}", headers=owner)
        assert r.status_code == 409 and r.json()["error"]["code"] == "institution.in_use"
    finally:
        ws_service._guards.clear()
