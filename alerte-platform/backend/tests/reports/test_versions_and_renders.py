"""Génération (job), versions immuables, comparaison, rendus MD/JSON/CSV/XLSX/PDF — API de bout en bout."""
from __future__ import annotations

import csv
import hashlib
import io
import json

import pypdfium2 as pdfium
import pytest
from openpyxl import load_workbook
from sqlalchemy import text

from app.core.db import session_scope
from tests.evaluation.fakes import make_gap
from tests.reports.conftest import API, generate, version


def artifact(rep, vid, fmt):
    r = rep.client.get(f"{API}/report-versions/{vid}/artifacts/{fmt}", headers=rep.h)
    assert r.status_code == 200, r.text
    return r


def test_generate_builds_structured_content_with_ledger_head(rep):
    res = generate(rep, title="Rapport crue")
    v = version(rep, res["version_id"])
    c = v["content"]
    assert v["status"] == "draft" and res["version_no"] == 1 and v["parent_version_id"] is None
    assert c["title"] == "Rapport crue" and c["cover"]["exercise"]["code"] == "EX-001"
    led = c["cover"]["ledger"]
    assert led["verify"]["ok"] is True and led["head_seq"] == v["ledger_head_seq"] and led["head_hash"] == v["ledger_head_hash"]
    assert led["head_seq"] and len(led["head_hash"]) == 64 and c["cover"]["snapshot_sha256"] == "a" * 64
    assert [f["id"] for f in c["findings"]] == ["gap-a", "gap-b"] and [h["id"] for h in c["hypotheses"]] == ["gap-h"]
    assert c["executive_summary"]["citations_text"] == "19 / 20 citations vérifiées" and c["executive_summary"]["decisions_count"] == 1
    assert c["context"]["models"] == ["p/m"] and c["context"]["institutions"][0]["code"] == "MET"
    assert c["annexes"]["kb_inventory"][0]["documents"][0]["code"] == "CM-S01" and c["annexes"]["kb_coverage"]["ratio"] == 0.75
    assert c["scorecard"]["dimensions_total"] == 13 and c["scorecard"]["overall_score"] is None  # « non évalué »
    assert c["metrics"]["T2"]["status"] == "not_computed"  # non exécuté : jamais 0
    assert len(v["content_sha256"]) == 64


def test_metrics_and_scorecard_flow_into_the_report(rep):
    rep.client.post(f"{API}/evaluation/exercises/EX1/run", params={"metric": "T2"}, headers=rep.h)
    c = version(rep, generate(rep)["version_id"])["content"]
    assert c["metrics"]["T2"]["status"] == "computed" and c["metrics"]["T2"]["value"] == 0.95


def test_published_versions_are_immutable_and_new_version_links_parent(rep):
    r1 = generate(rep, title="R")
    vid = r1["version_id"]
    content = version(rep, vid)["content"]
    content["title"] = "Titre corrigé"
    assert rep.client.put(f"{API}/report-versions/{vid}/content", json={"content": content}, headers=rep.h).status_code == 200
    assert version(rep, vid)["content"]["title"] == "Titre corrigé"  # brouillon modifiable
    pub = rep.client.post(f"{API}/report-versions/{vid}/publish", headers=rep.h)
    assert pub.status_code == 200 and pub.json()["status"] == "published" and pub.json()["published_at"]
    assert rep.client.post(f"{API}/report-versions/{vid}/publish", headers=rep.h).status_code == 409
    assert rep.client.put(f"{API}/report-versions/{vid}/content", json={"content": content}, headers=rep.h).status_code == 409
    for sql in ("UPDATE report_version SET content_sha256 = 'x' WHERE id = :i", "DELETE FROM report_version WHERE id = :i",
                "UPDATE report_version SET status = 'draft' WHERE id = :i"):  # triggers : défense en profondeur
        with pytest.raises(Exception, match="immuable"), session_scope(rep.ctx.session_factory) as s:
            s.execute(text(sql), {"i": vid})
    # nouvelle revue de lacune -> nouvelle version liée à la précédente
    rep.gaps.put(rep.ws, "EX1", rep.gaps.list_gaps(None, rep.ws, "EX1") + [make_gap("n", severity=3)])
    r2 = generate(rep, report_id=r1["report_id"])
    assert r2["version_no"] == 2 and r2["report_id"] == r1["report_id"]
    v2 = version(rep, r2["version_id"])
    assert v2["parent_version_id"] == vid and v2["content"]["cover"]["parent_version_no"] == 1
    assert version(rep, vid)["status"] == "published"  # la v1 n'a pas bougé
    detail = rep.client.get(f"{API}/reports/{r1['report_id']}", headers=rep.h).json()
    assert [x["version_no"] for x in detail["version_list"]] == [1, 2] and detail["origin"] == "généré par l'exercice"


def test_compare_versions_and_exercises(rep):
    r1 = generate(rep)
    rep.gaps.put(rep.ws, "EX1", [make_gap("a", severity=2, status="confirmed"), make_gap("n", severity=3)])  # a modifié, b disparu, n nouveau
    r2 = generate(rep, report_id=r1["report_id"])
    d = rep.client.get(f"{API}/reports/{r1['report_id']}/compare", params={"a": "1", "b": str(2)}, headers=rep.h).json()
    f = d["diff"]["findings"]
    assert [x["title"] for x in f["added"]] == ["Lacune n"] and [x["title"] for x in f["removed"]] == ["Lacune b"]
    assert f["changed"][0]["changes"]["severity"] == [3, 2] and d["diff"]["identical"] is False
    assert "findings" in d["diff"]["sections_changed"] and "hypotheses" in d["diff"]["sections_changed"]
    same = rep.client.get(f"{API}/reports/{r1['report_id']}/compare", params={"a": r2["version_id"], "b": r2["version_id"]}, headers=rep.h).json()
    assert same["diff"]["identical"] is True and same["diff"]["findings"]["changed"] == []
    # comparaison de deux exercices (par fingerprint)
    rep.exercise("EX2")
    rep.gaps.put(rep.ws, "EX2", [make_gap("a", severity=3), make_gap("z")])
    cmp = rep.client.get(f"{API}/reports/compare-exercises", params={"a": "EX1", "b": "EX2"}, headers=rep.h).json()
    assert cmp["basis"] == "fingerprint" and cmp["counts"] == {"new": 1, "resolved": 1, "persistent": 1, "severity_changed": 1, "status_changed": 1}
    assert rep.client.get(f"{API}/reports/{r1['report_id']}/compare", params={"a": "1", "b": "9"}, headers=rep.h).status_code == 404


def test_markdown_json_csv_xlsx_renders_and_hashes(rep):
    vid = generate(rep, title="Rapport crue")["version_id"]
    v = version(rep, vid)
    md = artifact(rep, vid, "md")
    text_ = md.text
    assert md.headers["x-content-sha256"] == hashlib.sha256(md.content).hexdigest()
    for needle in ("## 0. Page de garde et intégrité", v["ledger_head_hash"], f"seq {v['ledger_head_seq']}", "## 4. Constats", "## 5. Hypothèses non confirmées",
                   "## 7. Plan d'amélioration", "## 9. Scorecard", "non évalué", "## 11. Limites de l'analyse",
                   "non trouvée dans le corpus K", "non calculé"):
        assert needle in text_, needle
    assert text_.index("## 4. Constats") < text_.index("### 4.1 Lacune a") < text_.index("## 5. Hypothèses") < text_.index("### 5.1 Lacune h") < text_.index("## 7.")
    assert artifact(rep, vid, "md").content == md.content  # déterministe / mis en cache
    js = artifact(rep, vid, "json")
    assert json.loads(js.content) == v["content"]
    rows = list(csv.DictReader(io.StringIO(artifact(rep, vid, "csv").content.decode("utf-8-sig"))))
    assert [r["gap_id"] for r in rows] == ["gap-a", "gap-b", "gap-h"] and [r["section"] for r in rows] == ["constat", "constat", "hypothese"]
    assert rows[0]["severity"] == "3" and rows[0]["fingerprint"] == v["content"]["findings"][0]["fingerprint"]
    wb = load_workbook(io.BytesIO(artifact(rep, vid, "xlsx").content))
    assert wb.sheetnames == ["Intégrité", "Lacunes", "Preuves", "Références", "Plan", "Revues"]
    assert wb["Lacunes"].max_row == 4 and wb["Plan"].max_row >= 2 and wb["Revues"].max_row == 3  # revue de a + rejet de rej (historique conservé)
    assert v["ledger_head_hash"] in [c.value for row in wb["Intégrité"].iter_rows() for c in row]
    arts = {a["format"]: a for a in version(rep, vid)["artifacts"]}
    assert set(arts) == {"md", "json", "csv", "xlsx"} and arts["md"]["bytes"] == len(md.content)
    assert rep.client.get(f"{API}/report-versions/{vid}/artifacts/docx", headers=rep.h).status_code == 404


def test_csv_and_xlsx_neutralise_formula_injection(rep):
    rep.gaps.put(rep.ws, "EX1", [make_gap("a", title="=HYPERLINK(\"http://x\")", description="+cmd|' /C calc'!A0")])
    vid = generate(rep)["version_id"]
    rows = list(csv.DictReader(io.StringIO(artifact(rep, vid, "csv").content.decode("utf-8-sig"))))
    assert rows[0]["title"].startswith("'=") and rows[0]["description"].startswith("'+")
    ws = load_workbook(io.BytesIO(artifact(rep, vid, "xlsx").content))["Lacunes"]
    cell = ws.cell(2, 6)
    assert cell.data_type == "s" and str(cell.value).startswith("'=")


def pdf_text(data: bytes) -> tuple[int, str]:
    pdf = pdfium.PdfDocument(data)
    return len(pdf), "\n".join(pdf[i].get_textpage().get_text_range() for i in range(len(pdf)))


def test_pdf_is_real_with_expected_fields_and_recorded_hash(rep):
    rep.ctx.services["snapshot_loader"] = lambda s, e: (__import__("tests.reports.conftest", fromlist=["SNAPSHOT"]).SNAPSHOT, "a" * 64)
    vid = generate(rep, title="Rapport crue")["version_id"]
    r = artifact(rep, vid, "pdf")
    assert r.content.startswith(b"%PDF") and r.headers["content-type"] == "application/pdf"
    pages, txt = pdf_text(r.content)
    assert pages > 0
    v = version(rep, vid)
    flat = " ".join(txt.split())
    for needle in ("Rapport crue", "Page de garde", "EX-001", "Constats", "Hypothèses non confirmées", "Limites de l'analyse",
                   "Scorecard", "non évalué", "non calculé", v["ledger_head_hash"][:16], "Page 1 /", "Lacune a"):
        assert needle in flat, needle
    assert r.headers["x-content-sha256"] == hashlib.sha256(r.content).hexdigest()
    art = next(a for a in version(rep, vid)["artifacts"] if a["format"] == "pdf")
    assert art["sha256"] == hashlib.sha256(r.content).hexdigest() and art["bytes"] == len(r.content) and art["renderer"] == "weasyprint"
    assert artifact(rep, vid, "pdf").content == r.content  # cache par hash du contenu


def test_pdf_banner_sans_ia(rep):
    from tests.evaluation.fakes import seed_ledger
    rep.exercise("EX9")
    seed_ledger(rep.ctx, "EX9", ai_mode="scripted")
    rep.gaps.put(rep.ws, "EX9", [make_gap("a")])
    vid = generate(rep, "EX9")["version_id"]
    _, txt = pdf_text(artifact(rep, vid, "pdf").content)
    assert "SANS IA" in txt and "SANS IA" in artifact(rep, vid, "md").text.splitlines()[0]


def test_pdf_renders_arabic_without_crash_and_marks_rtl(rep):
    ar_title = "غياب المسؤولية عن إصدار الإنذار العام للسكان"
    rep.gaps.put(rep.ws, "EX1", [make_gap("ar", title=ar_title, description="لا توجد مؤسسة مكلفة بإصدار الإنذار العام. Alert duty missing.")])
    vid = generate(rep, title="تقرير الثغرات")["version_id"]
    from app.reports.render.pdf import render_html
    html = render_html(version(rep, vid)["content"])
    assert 'dir="rtl"' in html and 'lang="ar"' in html and ar_title in html
    pages, txt = pdf_text(artifact(rep, vid, "pdf").content)
    assert pages > 0 and "Constats" in txt
    assert any("؀" <= ch <= "ۿ" or "ﭐ" <= ch <= "﻿" for ch in txt)  # glyphes arabes présents dans le texte extrait


def test_pdf_uses_only_embedded_fonts():
    from pathlib import Path

    from app.reports.render import pdf
    fonts = {p.name for p in (pdf.RENDER_DIR / "fonts").glob("*.ttf")}
    assert {"NotoSans-Regular.ttf", "NotoSans-Bold.ttf", "NotoSansArabic-Regular.ttf"} <= fonts
    assert (pdf.RENDER_DIR / "fonts" / "LICENSE-OFL-Noto.txt").is_file()
    css = (pdf.RENDER_DIR / "print.css").read_text(encoding="utf-8")
    assert css.count("@font-face") == 5 and all(Path(pdf.RENDER_DIR / m).is_file() for m in
                                              __import__("re").findall(r'url\("([^"]+)"\)', css))
    assert pdf.get_pdf_renderer().name == "weasyprint" and pdf.Xhtml2PdfRenderer().name == "xhtml2pdf"
    assert pdf.is_rtl("مرحبا بالعالم") and not pdf.is_rtl("Hello مرحبا world and more latin") and not pdf.is_rtl("")
