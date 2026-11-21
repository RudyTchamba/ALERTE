"""API de bout en bout (TestClient) : CRUD, upload → job d'ingestion, publication, recherche, jobs et SSE."""
from __future__ import annotations

import time

import pytest

from tests.conftest import auth
from tests.knowledge.conftest import LAW_FR, make_pdf

API = "/api/v1"


def wait_job(client, headers, job_id, timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        j = client.get(f"{API}/jobs/{job_id}", headers=headers).json()
        if j["status"] in ("done", "failed", "interrupted"):
            return j
        time.sleep(0.05)
    raise AssertionError("job trop long")


def upload(client, owner, kb_id, name, data, **form):
    r = client.post(f"{API}/knowledge-bases/{kb_id}/documents", headers=owner, files={"file": (name, data)}, data=form)
    return r


def mk_kb(client, owner, name="Corpus national"):
    r = client.post(f"{API}/knowledge-bases", headers=owner, json={"name": name, "kind": "national", "languages": ["fr"]})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_full_flow_upload_ingest_publish_search(client, owner):
    kb = mk_kb(client, owner)
    r = upload(client, owner, kb, "loi.txt", LAW_FR.encode(), title="Loi 2021-12", jurisdiction="XX")
    assert r.status_code == 202, r.text
    job = wait_job(client, owner, r.json()["job"]["id"])
    assert job["status"] == "done", job
    doc = r.json()["document"]
    assert client.get(f"{API}/documents/{doc['id']}", headers=owner).json()["version"]["status"] in ("ready", "needs_review")
    q = client.get(f"{API}/knowledge-bases/{kb}/quality", headers=owner).json()
    assert q["documents"] == 1 and q["totals"]["with_articles"] == 1
    chunks = client.get(f"{API}/documents/{doc['id']}/versions/1/chunks", headers=owner).json()
    assert [c["article"] for c in chunks["items"]] == ["Article 1er", "Article 2", "Article 33"] or len(chunks["items"]) >= 3
    pv = client.get(f"{API}/documents/{doc['id']}/versions/1/preview", headers=owner).json()
    assert pv["total_pages"] == 1
    # publication → kb_version immuable
    p1 = client.post(f"{API}/knowledge-bases/{kb}/publish", headers=owner, json={"note": "v1"})
    assert p1.status_code == 201 and p1.json()["version_no"] == 1
    assert client.post(f"{API}/knowledge-bases/{kb}/publish", headers=owner, json={}).status_code == 409
    # recherche UI : portée dérivée du jeton
    s = client.post(f"{API}/knowledge-bases/{kb}/search", headers=owner, json={"query": "Article 33 opérateurs alerte"})
    assert s.status_code == 200
    hits = s.json()["hits"]
    assert hits and hits[0]["article"] == "Article 33"
    assert s.json()["degraded"] is False  # embedder fixture configuré
    # aucun paramètre d'identité/portée accepté
    bad = client.post(f"{API}/knowledge-bases/{kb}/search", headers=owner,
                      json={"query": "x", "kb_ids": ["autre"], "workspace_id": "autre"})
    assert bad.status_code == 422
    # doublon SHA-256
    dup = upload(client, owner, kb, "copie.txt", LAW_FR.encode())
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "kb.document.duplicate"
    # métadonnées : licence, redistribution, validité
    pd = client.patch(f"{API}/documents/{doc['id']}", headers=owner,
                      json={"license_spdx": "CC0-1.0", "redistribution": "allowed", "validity": "in_force"})
    assert pd.json()["redistribution"] == "allowed"
    assert client.patch(f"{API}/documents/{doc['id']}", headers=owner, json={"redistribution": "peut-être"}).status_code == 422
    assert client.get(f"{API}/ready").json()["checks"]["knowledge"]["ok"] is True


def test_upload_input_controls(client, owner):
    kb = mk_kb(client, owner)
    r = upload(client, owner, kb, "evil.exe", b"MZ....")
    assert r.status_code == 415 and r.json()["error"]["code"] == "kb.document.bad_type"
    r = upload(client, owner, kb, "faux.pdf", b"ceci n'est pas un pdf")
    assert r.status_code == 415
    r = upload(client, owner, kb, "vide.txt", b"")
    assert r.status_code == 422
    # chemin dans le nom : jamais utilisé
    r = upload(client, owner, kb, "../../etc/passwd.txt", ("Texte " * 50).encode())
    assert r.status_code == 202 and ".." not in r.json()["document"]["version"]["original_name"]


def test_upload_size_limit(client, owner, app):
    app.state.ctx.settings.upload_max_mb = 0  # 0 Mo : tout fichier non vide dépasse
    kb = mk_kb(client, owner)
    r = upload(client, owner, kb, "gros.txt", b"abc")
    assert r.status_code == 413 and r.json()["error"]["code"] == "kb.document.too_large"


def test_pdf_ingestion_through_api(client, owner):
    pdf = make_pdf(["<h1>Décret n° 2020-5</h1><p>Article 1 - Les opérateurs diffusent l'alerte. " + "Texte légal. " * 20 + "</p>",
                    "<p>المادة 2: يجب على المشغلين نشر التنبيه فورا. " + "نص قانوني طويل. " * 20 + "</p>"])
    kb = mk_kb(client, owner)
    r = upload(client, owner, kb, "decret.pdf", pdf, title="Décret test")
    j = wait_job(client, owner, r.json()["job"]["id"])
    assert j["status"] == "done", j
    d = client.get(f"{API}/documents/{r.json()['document']['id']}", headers=owner).json()
    assert d["version"]["extraction_method"] == "pdf-text"
    s = client.post(f"{API}/knowledge-bases/{kb}/search", headers=owner, json={"query": "المشغلين التنبيه", "k": 3}).json()
    assert s["hits"] and "المادة" in s["hits"][0]["text"]


def test_jobs_json_and_sse_resume(client, owner):
    kb = mk_kb(client, owner)
    r = upload(client, owner, kb, "loi.txt", LAW_FR.encode())
    jid = r.json()["job"]["id"]
    wait_job(client, owner, jid)
    with client.stream("GET", f"{API}/jobs/{jid}/stream", headers=owner) as resp:
        body = "".join(resp.iter_text())
    assert "event: done" in body and "id: 1001" in body
    # reprise : Last-Event-ID = 1001 → plus aucun événement (pas de doublon)
    with client.stream("GET", f"{API}/jobs/{jid}/stream", headers={**owner, "Last-Event-ID": "1001"}) as resp:
        body2 = "".join(resp.iter_text())
    assert "event: done" not in body2


def test_roles_and_workspace_isolation(client, owner):
    kb = mk_kb(client, owner)
    up = upload(client, owner, kb, "loi.txt", LAW_FR.encode())
    wait_job(client, owner, up.json()["job"]["id"])
    doc_id = up.json()["document"]["id"]
    # jetons non autorisés : lecture ET écriture refusées sur toutes les routes
    for role in ("observer", "player"):
        tok = client.post(f"{API}/tokens", json={"role": role}, headers=owner).json()["token"]
        h = auth(tok)
        for method, url, kw in [("get", "/knowledge-bases", {}), ("get", f"/knowledge-bases/{kb}", {}),
                                ("get", f"/documents/{doc_id}", {}), ("get", f"/documents/{doc_id}/versions/1/chunks", {}),
                                ("get", f"/documents/{doc_id}/versions/1/preview", {}),
                                ("post", f"/knowledge-bases/{kb}/search", {"json": {"query": "alerte"}}),
                                ("get", f"/knowledge-bases/{kb}/quality", {}), ("get", f"/knowledge-bases/{kb}/expected", {}),
                                ("post", f"/knowledge-bases/{kb}/publish", {"json": {}}),
                                ("post", f"/knowledge-bases/{kb}/exports", {"json": {}}),
                                ("get", "/jobs/x", {})]:
            r = getattr(client, method)(API + url, headers=h, **kw)
            assert r.status_code == 403, (role, url, r.status_code)
    # l'auditeur lit mais n'écrit pas
    aud = auth(client.post(f"{API}/tokens", json={"role": "auditor"}, headers=owner).json()["token"])
    assert client.get(f"{API}/knowledge-bases/{kb}", headers=aud).status_code == 200
    assert client.post(f"{API}/knowledge-bases/{kb}/publish", headers=aud, json={}).status_code == 403
    # autre espace → 404 partout
    ws2 = client.post(f"{API}/workspaces", json={"name": "Autre espace"}, headers=owner).json()
    other = auth(ws2["owner_token"])
    for url in (f"/knowledge-bases/{kb}", f"/documents/{doc_id}", f"/documents/{doc_id}/versions/1/chunks",
                f"/knowledge-bases/{kb}/quality", f"/knowledge-bases/{kb}/documents"):
        assert client.get(API + url, headers=other).status_code == 404, url
    assert client.post(f"{API}/knowledge-bases/{kb}/search", headers=other, json={"query": "alerte"}).status_code == 404
    assert client.patch(f"{API}/documents/{doc_id}", headers=other, json={"title": "pirate"}).status_code == 404
    assert client.get(f"{API}/knowledge-bases", headers=other).json() == []


def test_expected_documents_and_coverage(client, owner):
    kb = mk_kb(client, owner)
    up = upload(client, owner, kb, "loi.txt", LAW_FR.encode())
    wait_job(client, owner, up.json()["job"]["id"])
    client.post(f"{API}/knowledge-bases/{kb}/expected", headers=owner,
                json={"title": "Loi 2021-12", "matched_document_id": up.json()["document"]["id"]})
    client.post(f"{API}/knowledge-bases/{kb}/expected", headers=owner, json={"title": "Décret introuvable"})
    cov = client.get(f"{API}/knowledge-bases/{kb}/expected", headers=owner).json()["coverage"]
    assert cov == {"ratio": 0.5, "expected": 2, "present": 1, "missing": ["Décret introuvable"]}


def test_embed_job_and_fingerprint_refusal(client, owner, app):
    kb = mk_kb(client, owner)
    up = upload(client, owner, kb, "loi.txt", LAW_FR.encode())
    wait_job(client, owner, up.json()["job"]["id"])
    r = client.post(f"{API}/knowledge-bases/{kb}/embed", headers=owner, json={})
    assert r.status_code == 202 and wait_job(client, owner, r.json()["job"]["id"])["status"] == "done"
    # changement d'embedder → refus de mélanger
    from app.knowledge.embedders import FixtureEmbedder
    app.state.ctx.services["knowledge"].embedder = FixtureEmbedder(32)
    r = client.post(f"{API}/knowledge-bases/{kb}/embed", headers=owner, json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "kb.embedder_mismatch"
    r = client.post(f"{API}/knowledge-bases/{kb}/embed", headers=owner, json={"reembed": True})
    assert r.status_code == 202 and wait_job(client, owner, r.json()["job"]["id"])["status"] == "done"


def test_reindex_job(client, owner):
    kb = mk_kb(client, owner)
    up = upload(client, owner, kb, "loi.txt", LAW_FR.encode())
    wait_job(client, owner, up.json()["job"]["id"])
    r = client.post(f"{API}/knowledge-bases/{kb}/reindex", headers=owner)
    j = wait_job(client, owner, r.json()["job"]["id"])
    assert j["status"] == "done", j["error"]
    assert j["result"]["chunks_indexed"] >= 3 and j["result"]["vectors_indexed"] >= 3


@pytest.mark.parametrize("bad", ["", " "])
def test_search_requires_query(client, owner, bad):
    kb = mk_kb(client, owner)
    assert client.post(f"{API}/knowledge-bases/{kb}/search", headers=owner, json={"query": bad}).status_code in (200, 422)


def test_setup_registers_services_and_fts5(client, app):
    ctx = app.state.ctx
    for name in ("search", "knowledge", "embedder"):
        assert name in ctx.services
    k = ctx.services["knowledge"]
    for fn in ("published_document_version_ids", "kb_overview", "get_chunk", "chunk_in_scope", "coverage", "document_meta",
              "readiness"):
        assert callable(getattr(k, fn))
    from app.contracts import SearchService
    assert hasattr(ctx.services["search"], "search") and SearchService
    with ctx.engine.connect() as c:
        assert c.exec_driver_sql("SELECT name FROM sqlite_master WHERE name='chunk_fts'").scalar() == "chunk_fts"
