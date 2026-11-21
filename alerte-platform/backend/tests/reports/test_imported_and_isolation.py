"""Rapports importés (séparés des générés, provenance, constats, liens) et isolation inter-espaces."""
from __future__ import annotations

import hashlib

from tests.reports import demo_prior_findings as demo
from tests.reports.conftest import API, generate, version

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def upload(rep, name="rapport_v2.pdf", data=PDF, headers=None, **form):
    return rep.client.post(f"{API}/reports/import", files={"file": (name, data, "application/octet-stream")},
                           data={"title": "Rapport technique v2", "original_date": "2026-11-10", "source_note": "équipe", **form},
                           headers=rep.h if headers is None else headers)


def test_import_keeps_original_blob_with_provenance(rep):
    r = upload(rep)
    assert r.status_code == 201, r.text
    j = r.json()
    sha = hashlib.sha256(PDF).hexdigest()
    assert j["kind"] == "imported" and j["origin"] == "analyse antérieure" and j["document"]["sha256"] == sha
    assert j["document"]["provenance"]["original_date"] == "2026-11-10" and j["document"]["provenance"]["origin"] == "analyse antérieure"
    assert rep.ctx.blobs.verify(sha)
    dl = rep.client.get(f"{API}/reports/{j['id']}/document", headers=rep.h)
    assert dl.content == PDF and dl.headers["x-content-sha256"] == sha and dl.headers["content-type"] == "application/pdf"
    md = upload(rep, "notes.md", "# Notes\nlacune é".encode())
    assert md.status_code == 201 and md.json()["document"]["media_type"] == "text/markdown"
    assert upload(rep, "x.docx", b"PK\x03\x04docx").status_code == 201


def test_import_rejects_bad_files(rep):
    assert upload(rep, "x.exe", b"MZ").status_code == 422
    assert upload(rep, "x.pdf", b"not a pdf").status_code == 422
    assert upload(rep, "x.pdf", b"").status_code == 422
    assert upload(rep, "x.md", b"\xff\xfe\x00bad").status_code == 422
    assert upload(rep, "x.docx", b"%PDF-1").status_code == 422
    assert upload(rep, headers={}).status_code == 401


def test_eleven_demo_findings_entered_and_kept_apart_from_generated(rep):
    rid = upload(rep).json()["id"]
    created = demo.seed(rep.client, rep.h, rid)
    assert len(created) == 11 and all(c["origin"] == "analyse antérieure" for c in created)
    detail = rep.client.get(f"{API}/reports/{rid}", headers=rep.h).json()
    assert len(detail["findings"]) == 11 and detail["findings"][0]["source_page"] == 3
    one = rep.client.post(f"{API}/reports/{rid}/findings", json={"title": "Supplément", "body": "b"}, headers=rep.h)
    assert one.status_code == 201 and len(one.json()) == 1
    assert rep.client.post(f"{API}/reports/{rid}/findings", json=[{"title": "x", "severity_hint": 9}], headers=rep.h).status_code == 422
    # un rapport généré n'accepte pas de constats saisis ; les constats importés ne sont jamais dans les constats générés
    gen = generate(rep)
    assert rep.client.post(f"{API}/reports/{gen['report_id']}/findings", json=[{"title": "x"}], headers=rep.h).status_code == 409
    c = version(rep, gen["version_id"])["content"]
    titles = {f["title"] for f in c["findings"] + c["hypotheses"]}
    assert not titles & {f["title"] for f in demo.findings()}
    assert c["prior_analyses"]["origin"] == "analyse antérieure" and c["prior_analyses"]["links"] == []
    kinds = {r["kind"] for r in rep.client.get(f"{API}/reports", headers=rep.h).json()}
    assert kinds == {"imported", "generated"}
    assert [r["id"] for r in rep.client.get(f"{API}/reports", params={"kind": "imported"}, headers=rep.h).json()] == [rid]


def test_prior_links_appear_separately_in_next_report(rep):
    rid = upload(rep).json()["id"]
    f = demo.seed(rep.client, rep.h, rid)
    ok = rep.client.post(f"{API}/imported-findings/{f[0]['id']}/links", headers=rep.h,
                         json={"gap_id": "gap-a", "exercise_id": "EX1", "relation": "previously_identified", "note": "même lacune"})
    assert ok.status_code == 201 and ok.json()["origin"] == "analyse antérieure"
    assert rep.client.post(f"{API}/imported-findings/{f[0]['id']}/links", headers=rep.h,
                           json={"gap_id": "gap-a", "exercise_id": "EX1", "relation": "contradicts"}).status_code == 409
    assert rep.client.post(f"{API}/imported-findings/{f[1]['id']}/links", headers=rep.h,
                           json={"gap_id": "gap-b", "exercise_id": "EX1", "relation": "newly_emerged"}).status_code == 201
    assert rep.client.post(f"{API}/imported-findings/{f[2]['id']}/links", headers=rep.h,
                           json={"gap_id": "nope", "exercise_id": "EX1", "relation": "contradicts"}).status_code == 404
    assert rep.client.post(f"{API}/imported-findings/{f[2]['id']}/links", headers=rep.h,
                           json={"gap_id": "gap-a", "exercise_id": "EX1", "relation": "bogus"}).status_code == 422
    links = rep.client.get(f"{API}/reports/{rid}/links", headers=rep.h).json()
    assert {x["relation"] for x in links} == {"previously_identified", "newly_emerged"}
    vid = generate(rep)["version_id"]
    prior = version(rep, vid)["content"]["prior_analyses"]["links"]
    assert len(prior) == 2 and prior[0]["origin"] == "analyse antérieure" and prior[0]["report_title"] == "Rapport technique v2"
    assert "analyse antérieure" in rep.client.get(f"{API}/report-versions/{vid}/artifacts/md", headers=rep.h).text
    assert not any(x["id"] in {"gap-a"} for x in version(rep, vid)["content"]["hypotheses"])


def test_isolation_between_workspaces(rep):
    gen = generate(rep)
    rid = upload(rep).json()["id"]
    f = demo.seed(rep.client, rep.h, rid)
    v = gen["version_id"]
    h2 = rep.h2
    for method, url, kw in (
        ("get", f"/reports/{gen['report_id']}", {}), ("get", f"/reports/{rid}", {}), ("get", f"/reports/{rid}/document", {}),
        ("get", f"/reports/{rid}/findings", {}), ("get", f"/reports/{rid}/links", {}),
        ("post", f"/reports/{rid}/findings", {"json": [{"title": "x"}]}),
        ("get", f"/report-versions/{v}", {}), ("post", f"/report-versions/{v}/publish", {}),
        ("get", f"/report-versions/{v}/artifacts/md", {}), ("get", f"/report-versions/{v}/artifacts/pdf", {}),
        ("put", f"/report-versions/{v}/content", {"json": {"content": {}}}),
        ("get", f"/reports/{gen['report_id']}/compare", {"params": {"a": "1", "b": "1"}}),
        ("post", "/exercises/EX1/reports", {"json": {}}), ("get", "/reports/compare-exercises", {"params": {"a": "EX1", "b": "EX1"}}),
        ("post", f"/imported-findings/{f[0]['id']}/links", {"json": {"gap_id": "gap-a", "exercise_id": "EX1", "relation": "contradicts"}}),
        ("post", "/reports", {"json": {"title": "t", "exercise_id": "EX1"}}),
    ):
        r = getattr(rep.client, method)(API + url, headers=h2, **kw)
        assert r.status_code == 404, (method, url, r.status_code, r.text)
    assert rep.client.get(f"{API}/reports", headers=h2).json() == []
    # un rapport d'un autre espace ne peut pas servir de support à une nouvelle version
    rep.exercise("EXB", rep.ws2)
    assert rep.client.post(f"{API}/exercises/EXB/reports", json={"report_id": gen["report_id"]}, headers=h2).status_code == 404
    assert rep.client.get(f"{API}/report-versions/{v}", headers=rep.h).status_code == 200
