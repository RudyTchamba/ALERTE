"""Text extraction from every kind of document: exact text layers, OCR of scans, tables, mixed pages, Office files,
nothing skipped silently, and the human proofreading loop."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from alerte import config
from alerte.knowledge.extract import extract_file, ocr, synth
from alerte.knowledge.extract.quality import cer, similarity, text_layer_trust

needs_ocr = pytest.mark.skipif(not ocr.status().tesseract, reason="Tesseract is not installed (python -m alerte ocr-setup)")


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    d = tmp_path_factory.mktemp("corpus")
    return {c.path.name: c for c in synth.build_corpus(d)}


def test_quality_helpers():
    assert cer("alerte rouge", "alerte rouge") == 0
    assert 0 < cer("alerte rouge", "alerte rouqe") < 0.1
    assert similarity("Les opérateurs", "les  opérateurs") == 1.0
    assert text_layer_trust("Les opérateurs de communications doivent relayer les alertes publiques. " * 5)[0]
    ok, why = text_layer_trust("\ufffd\ufffd\ue001\ue002 " * 80)
    assert not ok and "bad-encoding" in why
    ok, why = text_layer_trust("xqzv wkrt bvnm plkj hgfd qwrt zxcv bnmk vbnm tgbn ynhu mjik " * 4)
    assert not ok and "garbled" in why


def test_digital_pdf_text_is_exact(corpus):
    for name in ("digital_fr.pdf", "two_columns.pdf"):
        c = corpus[name]
        r = extract_file(c.path, "fr", use_cache=False)
        assert r.ocr_pages == 0 and not r.review_pages
        assert cer(c.truth, r.text) < 0.001, (name, r.text)


def test_digital_table_keeps_cells_and_spaces(corpus):
    r = extract_file(corpus["digital_table.pdf"].path, "fr", use_cache=False)
    assert r.tables == 1
    assert "| Météo nationale | Émettre l'avis | 10 |" in r.text
    assert "| --- |" in r.text


def test_word_file_text_table_and_picture(corpus):
    r = extract_file(corpus["report.docx"].path, "fr", use_cache=False)
    assert r.tables == 1 and "| Protection civile | Décider l'alerte | 5 |" in r.text
    assert "Note de service" in r.text
    if ocr.status().available:
        assert "[Text in image]" in r.text and "Douala" in r.text


@needs_ocr
@pytest.mark.parametrize("name", ["scan_fr.pdf", "scan_en.pdf", "scan_table.pdf", "scan_bad_layer.pdf", "photo_sideways.png",
                                  "mixed_text_image.pdf", "scan_ar.pdf"])
def test_scans_reach_their_accuracy_target(corpus, name):
    if name not in corpus:
        pytest.skip("no Arabic font on this machine")
    c = corpus[name]
    lang = "en" if "_en" in name else ("ar" if "_ar" in name else "fr")
    r = extract_file(c.path, lang, use_cache=False)
    assert not r.failed
    acc = 1 - cer(c.truth, synth.flatten(r.text))
    assert acc >= c.target, f"{c.name}: {acc:.4f} < {c.target}\n{r.text}"


@needs_ocr
def test_scan_with_corrupt_text_layer_ignores_the_layer(corpus):
    r = extract_file(corpus["scan_bad_layer.pdf"].path, "fr", use_cache=False)
    assert "xqzv" not in r.text and r.pages[0].method.startswith("ocr")
    assert "text layer ignored" in r.pages[0].method                  # the decision is recorded


@needs_ocr
def test_scanned_table_is_read_cell_by_cell(corpus):
    r = extract_file(corpus["scan_table.pdf"].path, "fr", use_cache=False)
    assert r.tables == 1
    assert "| Opérateur | Diffuser le message | 2 |" in r.text


@needs_ocr
def test_hard_page_is_flagged_not_trusted(tmp_path):
    img = synth.scanify(synth.page_image(synth.FR, size=(520, 300), font_px=10), angle=3, noise=45, blur=1.4)
    p = tmp_path / "hard.png"
    img.save(p)
    r = extract_file(p, "fr", use_cache=False)
    assert r.review_pages or r.failed, "an unreadable page must be flagged for proofreading"


@needs_ocr
def test_proofreading_loop(tmp_path, monkeypatch):
    """flagged page -> review pack -> human sidecar -> next extraction uses it and is no longer flagged"""
    img = synth.scanify(synth.page_image(synth.FR, size=(520, 300), font_px=10), angle=3, noise=45, blur=1.4)
    src = tmp_path / "docs" / "hard.png"
    src.parent.mkdir()
    img.save(src)
    first = extract_file(src, "fr", use_cache=False)
    assert first.needs_review
    (tmp_path / "hard.png.corrected.md").write_text("x")  # wrong place on purpose: must NOT be used
    assert not extract_file(src, "fr", use_cache=False).corrected
    side = src.parent / "hard.png.corrected.md"
    side.write_text("<!-- proofread by hand -->\nArticle 12. Texte corrigé à la main.", encoding="utf-8")
    again = extract_file(src, "fr", use_cache=False)
    assert again.corrected and again.method == "human-corrected" and not again.needs_review
    assert again.text == "Article 12. Texte corrigé à la main."


def test_missing_ocr_engine_is_reported_never_silent(corpus, monkeypatch):
    monkeypatch.setattr(ocr, "_status", ocr.OcrStatus())
    monkeypatch.setattr(ocr, "status", lambda refresh=False: ocr._status)
    r = extract_file(corpus["scan_fr.pdf"].path, "fr", use_cache=False)
    assert r.failed and any("NEEDS-OCR-ENGINE" in f for p in r.pages for f in p.flags)


def test_unreadable_binary_is_reported(tmp_path):
    p = tmp_path / "mystery.xyz"
    p.write_bytes(b"\x00\x01\x02\xff\xfe binary")
    r = extract_file(p, use_cache=False)
    assert r.failed and "unsupported" in r.failed


def test_wrong_extension_is_sniffed(tmp_path, corpus):
    p = tmp_path / "no_extension"
    shutil.copy(corpus["digital_fr.pdf"].path, p)
    r = extract_file(p, "fr", use_cache=False)
    assert not r.failed and "Article 12" in r.text and any("read as .pdf" in w for w in r.warnings)


# ------------------------------------------------------------------------------------------ ingestion
@pytest.fixture()
def data_tree(tmp_path, corpus, monkeypatch):
    """A data folder with a manifest row, an unlisted file in a sub-sub-folder, a duplicate, and mixed formats."""
    import openpyxl
    from pptx import Presentation
    root = tmp_path / "data"
    (root / "docs" / "CM" / "official").mkdir(parents=True)
    (root / "docs" / "inbox" / "deep" / "deeper").mkdir(parents=True)
    hdr = open(config.settings.manifest_path, encoding="utf-8-sig").readline().strip().split(",")
    row = {h: "" for h in hdr}
    row.update(doc_id="CM-02", title="Law 2010/013", country="CM", doc_type="law", language="fr", reliability="official",
               collection="CM", file="CM/official/CM-02_Law.pdf", institutions="ART", topics="alerting")
    with (root / "manifest.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=hdr, lineterminator="\n")
        w.writeheader()
        w.writerow(row)
    shutil.copy(corpus["digital_fr.pdf"].path, root / "docs/CM/official/CM-02_Law.pdf")
    shutil.copy(corpus["digital_fr.pdf"].path, root / "docs/inbox/copy_of_the_law.pdf")            # identical
    shutil.copy(corpus["digital_table.pdf"].path, root / "docs/inbox/deep/deeper/table.pdf")
    shutil.copy(corpus["report.docx"].path, root / "docs/inbox/note.docx")
    (root / "docs/inbox/plain.txt").write_text("Texte brut: alerte rouge à Douala.", encoding="utf-8")
    (root / "docs/inbox/page.html").write_text("<html><body><h1>Titre</h1><p>Le centre des opérations.</p>"
                                               "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table></body></html>", encoding="utf-8")
    wb = openpyxl.Workbook()
    wb.active.append(["Zone", "Population"])
    wb.active.append(["Douala", 3000000])
    wb.save(root / "docs/inbox/zones.xlsx")
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Plan d'évacuation"
    s.placeholders[1].text = "Point de rassemblement: stade omnisports"
    prs.save(root / "docs/inbox/plan.pptx")
    (root / "docs/inbox/broken.bin").write_bytes(b"\x00\x00\x00\x01")
    monkeypatch.setenv("ALERTE_DATA_DIR", str(root))
    monkeypatch.setenv("ALERTE_INDEX_DIR", str(tmp_path / "idx"))
    config.reload()
    yield root
    monkeypatch.undo()
    config.reload()


def test_every_file_in_every_folder_is_accounted_for(data_tree, tmp_path):
    from alerte.knowledge.ingest import build_index
    from alerte.knowledge.store import KnowledgeStore
    rep = build_index(include_itu=False, embed_provider="none", progress=lambda m: None)
    store = KnowledgeStore.load(tmp_path / "idx")
    texts = {d: " ".join(f"{c.article} {c.text}" for c in store.chunks if c.doc_id == d) for d in {c.doc_id for c in store.chunks}}
    names = {Path(r["file"]).name: r for r in rep.extraction}
    assert len(names) == 9, sorted(names)                                  # every file was attempted
    assert "CM-02" in texts and "Article 12" in texts["CM-02"]            # the listed one, by its manifest name
    assert "Douala" in texts["AUTO-plain"]                                 # unlisted, found automatically
    assert "| Météo nationale |" in texts["AUTO-table"]                    # three folders deep
    assert "Zone | Population" in texts["AUTO-zones"] and "stade omnisports" in texts["AUTO-plan"]
    assert "| A | B |" in texts["AUTO-page"] and "Douala" in texts["AUTO-note"]
    assert rep.duplicates == {"AUTO-copy-of-the-law": "CM-02"}             # indexed once, reported
    assert list(rep.failed) == ["AUTO-broken"] and "unsupported" in rep.failed["AUTO-broken"]
    assert len(rep.auto) == 8
    report = json.loads((tmp_path / "idx" / "extraction_report.json").read_text(encoding="utf-8"))
    assert "AUTO-broken" in report["failed"]
    assert "AUTO-broken" in (tmp_path / "idx" / "review_queue.md").read_text(encoding="utf-8")


def test_chunks_record_how_their_text_was_obtained(data_tree, tmp_path):
    from alerte.knowledge.ingest import build_index
    from alerte.knowledge.store import KnowledgeStore
    build_index(include_itu=False, embed_provider="none", progress=lambda m: None)
    store = KnowledgeStore.load(tmp_path / "idx")
    by_doc = {c.doc_id: c for c in store.chunks}
    assert by_doc["CM-02"].extraction == "text-layer"
    assert by_doc["AUTO-plain"].extraction == "native"


def test_strict_cli_fails_on_unreadable_file(data_tree, tmp_path):
    from alerte.cli import main
    assert main(["ingest", "--itu", "no", "--embed", "none", "--quiet", "--strict"]) == 1
    (data_tree / "docs/inbox/broken.bin").unlink()
    assert main(["ingest", "--itu", "no", "--embed", "none", "--quiet", "--strict"]) == 0


@needs_ocr
def test_ingest_reads_scanned_files_in_any_folder(data_tree, corpus, tmp_path):
    from alerte.knowledge.ingest import build_index
    shutil.copy(corpus["scan_fr.pdf"].path, data_tree / "docs/inbox/deep/scanned.pdf")
    rep = build_index(include_itu=False, embed_provider="none", progress=lambda m: None)
    row = next(r for r in rep.extraction if r["file"].endswith("scanned.pdf"))
    assert row["ocr_pages"] == 1 and row["mean_ocr_confidence"] > 85
    assert rep.ocr_pages >= 1
