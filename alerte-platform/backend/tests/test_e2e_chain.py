"""Chaîne complète avec les VRAIS modules (aucun faux service) : espace → institutions → KB (upload, ingestion, indexation
FTS5+Chroma, publication) → actions/mandats validés → agents + droits KB → scénario → exercice → préparation → simulation →
ledger vérifié → lacunes → rapport (MD/JSON/CSV/XLSX/PDF) → export de KB.

Fournisseurs : `scripted` (agents) et `fixture` (embeddings) = outils de test SANS IA ; ce test prouve l'INTÉGRATION des
modules, jamais la qualité d'un modèle (cf. `pytest -m model`)."""
from __future__ import annotations

import time

from tests.conftest import auth
from tests.knowledge.conftest import LAW_FR

API = "/api/v1"


def wait_job(client, h, job_id, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        j = client.get(f"{API}/jobs/{job_id}", headers=h).json()
        if j["status"] in ("done", "failed", "interrupted"):
            return j
        time.sleep(0.05)
    raise AssertionError("job trop long")


def ok(r, code=(200, 201, 202)):
    assert r.status_code in code, f"{r.request.method} {r.request.url} -> {r.status_code} {r.text[:600]}"
    return r.json()


def test_full_chain_with_real_modules(client, app, owner):
    h = owner
    ctx = app.state.ctx

    # 1. rôles
    fac = auth(ok(client.post(f"{API}/tokens", json={"role": "facilitator"}, headers=h))["token"])
    aud = auth(ok(client.post(f"{API}/tokens", json={"role": "auditor"}, headers=h))["token"])

    # 2. pays + institutions
    country = ok(client.post(f"{API}/countries", json={"code": "XX", "name": "Pays test"}, headers=h))["id"]
    inst = {}
    for code in ("MET", "DPC"):
        inst[code] = ok(client.post(f"{API}/institutions", json={"code": code, "name": f"Institution {code}",
                                                                  "kind": "agency", "country_id": country}, headers=h))["id"]

    # 3. base de connaissances : upload → ingestion → publication
    kb = ok(client.post(f"{API}/knowledge-bases", headers=h,
                        json={"name": "Corpus national", "kind": "national", "languages": ["fr"]}))["id"]
    up = ok(client.post(f"{API}/knowledge-bases/{kb}/documents", headers=h, files={"file": ("loi.txt", LAW_FR.encode())},
                        data={"title": "Loi 2021-12", "jurisdiction": "XX"}))
    assert wait_job(client, h, up["job"]["id"])["status"] == "done"
    doc = up["document"]
    emb = ok(client.post(f"{API}/knowledge-bases/{kb}/embed", headers=h, json={}))  # embeddings (fixture) + index vectoriel
    if isinstance(emb, dict) and emb.get("job"):
        assert wait_job(client, h, emb["job"]["id"])["status"] == "done"
    chunks = ok(client.get(f"{API}/documents/{doc['id']}/versions/1/chunks", headers=h))["items"]
    art33 = next(c for c in chunks if c["article"] and "33" in c["article"])
    ok(client.post(f"{API}/knowledge-bases/{kb}/publish", headers=h, json={"note": "v1"}))

    # 4. actions + mandats validés avec source résolue
    ok(client.post(f"{API}/actions", headers=h, json={"code": "issue_alert", "label": "Diffuser l'alerte", "domain": "alerte",
                                                       "derivation": "referential", "reference_note": "loi"}))
    m = ok(client.post(f"{API}/mandates", headers=h, json={
        "institution_id": inst["MET"], "kind": "duty", "action_code": "issue_alert", "procedure_status": "specific",
        "has_deadline": True, "sources": [{"document_version_id": art33["document_version_id"], "chunk_id": art33["id"]}]}))
    ok(client.post(f"{API}/mandates/{m['id']}/validate", headers=h))

    # 5. agents + droits KB
    agents = {}
    for code in ("MET", "DPC"):
        agents[code] = ok(client.post(f"{API}/agents", headers=h, json={
            "institution_id": inst[code], "code": f"AG-{code}", "name": f"Agent {code}", "mission": "Appliquer son mandat"}))["id"]
        ok(client.put(f"{API}/agents/{agents[code]}/kb-grants", headers=h, json={"kb_ids": [kb]}))
    assert ok(client.get(f"{API}/access-matrix", headers=h))

    # 6. scénario
    sc = ok(client.post(f"{API}/scenarios", headers=h, json={"code": "SC1", "title": "Crue", "country_id": country,
                                                              "language": "fr"}))["id"]
    inj = ok(client.post(f"{API}/scenarios/{sc}/injects", headers=h, json={
        "title": "Alerte de crue", "body": "Les pluies provoquent une crue.", "sim_time": "D1 06:00", "from_actor": "CAPTEURS",
        "recipients": [inst["MET"], inst["DPC"]], "tags": ["life_risk"]}))
    ok(client.put(f"{API}/injects/{inj['id']}/demands", headers=h, json={"demands": [
        {"action_code": "issue_alert", "derivation": "referential", "justification": "loi"}]}))
    ok(client.get(f"{API}/scenarios/{sc}/lint", headers=h))

    # 7. exercice + sièges + préparation
    ex = ok(client.post(f"{API}/exercises", headers=fac, json={"scenario_id": sc, "title": "Ex e2e", "ai_mode": "scripted"}))["id"]
    ok(client.put(f"{API}/exercises/{ex}/seats", headers=fac, json={"seats": [
        {"code": c, "institution_id": inst[c], "agent_id": agents[c], "controller": "agent"} for c in ("MET", "DPC")]}))
    ok(client.get(f"{API}/exercises/{ex}/readiness", headers=fac))
    ok(client.post(f"{API}/exercises/{ex}/ready", headers=fac))

    # 8. simulation
    ok(client.post(f"{API}/exercises/{ex}/commands", headers=fac, json={"kind": "start", "args": {}}))
    mgr = ctx.service("simulation")
    state = mgr.wait_until(ex, lambda e: e.state in {"completed", "stopped", "paused", "interrupted", "failed"}, 60).state
    mgr.join(ex, 15)
    assert state == "completed", state

    # 9. ledger vérifié + décisions
    v = ok(client.get(f"{API}/exercises/{ex}/ledger/verify", headers=aud))
    assert v.get("ok", v.get("valid")) is True, v
    events = ok(client.get(f"{API}/exercises/{ex}/ledger?limit=5000", headers=aud))
    types = {e["type"] for e in events}
    assert not [e for e in events if e["type"] in ("ERROR", "SCOPE_VIOLATION")], "erreur ou violation de portée"
    checks = [c for e in events if e["type"] == "CITATION_CHECK" for c in e["payload"]["citations"]]
    assert checks and all(c["pass"] for c in checks), checks  # citations vérifiées contre les VRAIS chunks
    assert {"SNAPSHOT", "INJECT", "DECISION", "RETRIEVAL"} <= types, types
    assert ok(client.get(f"{API}/exercises/{ex}/decisions", headers=aud))

    # 10. lacunes
    ok(client.post(f"{API}/exercises/{ex}/detect-gaps", headers=fac))
    gaps = ok(client.get(f"{API}/gaps?exercise_id={ex}", headers=fac))
    assert isinstance(gaps["items"] if isinstance(gaps, dict) else gaps, list)

    # 11. rapport + rendus
    rep = ok(client.post(f"{API}/exercises/{ex}/reports", headers=fac, json={"title": "Rapport e2e", "language": "fr"}))
    j = wait_job(client, fac, (rep.get("job") or rep)["id"])
    assert j["status"] == "done", j
    vid = (j.get("result") or {})["version_id"]
    for fmt, magic in (("md", None), ("json", None), ("csv", None), ("xlsx", b"PK"), ("pdf", b"%PDF")):
        r = client.get(f"{API}/report-versions/{vid}/artifacts/{fmt}", headers=fac)
        assert r.status_code == 200, (fmt, r.status_code, r.text[:300])
        if magic:
            assert r.content.startswith(magic), fmt

    # 12. export de la KB
    exp = ok(client.post(f"{API}/knowledge-bases/{kb}/exports", headers=h, json={}))
    job = (exp.get("job") or {}).get("id")
    if job:
        assert wait_job(client, h, job)["status"] == "done"
