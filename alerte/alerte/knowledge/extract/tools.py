"""Command-line helpers around extraction: OCR setup, accuracy benchmark, and the human proofreading pack."""

from __future__ import annotations

import json
import platform
from pathlib import Path

from alerte import config
from alerte.knowledge.extract import extract_file, ocr
from alerte.knowledge.extract.ocr import PROJECT_ROOT

TESSDATA_URL = "https://raw.githubusercontent.com/tesseract-ocr/tessdata_{kind}/main/{lang}.traineddata"


def install_hint() -> str:
    sysname = platform.system()
    if sysname == "Windows":
        return "winget install --id UB-Mannheim.TesseractOCR -e   (or download the installer from https://github.com/UB-Mannheim/tesseract/wiki)"
    if sysname == "Darwin":
        return "brew install tesseract"
    return "sudo apt install tesseract-ocr   (Fedora: sudo dnf install tesseract)"


def setup_ocr(langs: list[str], kind: str = "best") -> int:
    """Check the Tesseract program and download the language models into ocr/tessdata."""
    from alerte.net import download
    st = ocr.status(refresh=True)
    if st.tesseract:
        print(f"[ok] Tesseract {st.version} at {st.tesseract}")
    else:
        print("[!!] The Tesseract program is not installed. Install it once, then run this command again:")
        print("     " + install_hint())
    dest = PROJECT_ROOT / "ocr" / "tessdata"
    dest.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        f = dest / f"{lang}.traineddata"
        if f.exists() and f.stat().st_size > 100_000:
            print(f"[ok] {lang}: already in {dest}")
            continue
        url = TESSDATA_URL.format(kind=kind, lang=lang)
        try:
            n = download(url, str(f), timeout=300)
            print(f"[ok] {lang}: downloaded {n // 1024} KB ({kind} model)")
        except Exception as e:
            print(f"[!!] {lang}: download failed ({e}). Get {url} and place it in {dest}")
    st = ocr.status(refresh=True)
    print("[..] " + st.describe())
    missing = [l for l in langs if l not in st.langs]
    if missing and st.tesseract:
        print(f"[!!] languages not usable yet: {', '.join(missing)}")
    return 0 if st.tesseract and not missing else 1


def run_eval(thorough: bool = False, keep: Path | None = None) -> int:
    import tempfile

    from alerte.knowledge.extract import synth
    st = ocr.status()
    print("OCR engine: " + st.describe())
    work = keep or Path(tempfile.mkdtemp(prefix="alerte-ocr-eval-"))
    cases = synth.build_corpus(work)
    rows = synth.evaluate(cases, thorough)
    w = max(len(r["case"]) for r in rows)
    print(f"{'case':{w}}  {'method':28} {'OCR conf':>8} {'accuracy':>9} {'target':>7}  result")
    bad = 0
    for r in rows:
        status = "PASS" if r["ok"] else "FAIL"
        bad += not r["ok"]
        print(f"{r['case']:{w}}  {r['method'][:28]:28} {str(r['ocr_conf'] or '-'):>8} {r['accuracy'] * 100:8.2f}% {r['target'] * 100:6.1f}%  {status}"
              + ("  (flagged for review)" if r["flagged"] else "") + (f"  {r['failed']}" if r["failed"] else ""))
    out = config.settings.runs_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "ocr-eval.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(rows) - bad}/{len(rows)} cases reached their target. Synthetic documents are cleaner than many real scans: "
          "real files can score lower, which is why uncertain pages are flagged for proofreading (python -m alerte review).")
    return 1 if bad else 0


def review_pack(target: str) -> int:
    """Write page images and an editable draft for a document whose pages need a human look."""
    rep_path = config.settings.index_dir / "extraction_report.json"
    if not rep_path.exists():
        print("No extraction report yet: run `python -m alerte ingest` first.")
        return 1
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    rows = [r for r in rep["documents"] if target in (r["doc_id"], r["file"]) or target.lower() in Path(r["file"]).name.lower()]
    if not rows:
        print(f"No document matches '{target}'. Documents that need review: {', '.join(rep['review']) or 'none'}")
        return 1
    row = rows[0]
    path = Path(row["file"])
    res = extract_file(path)
    out = PROJECT_ROOT / "review" / row["doc_id"]
    out.mkdir(parents=True, exist_ok=True)
    flagged = {p.page: p.flags for p in res.pages if p.flags}
    parts = [f"<!-- Proofreading draft for {path.name}. Compare each CHECK page with its image in this folder, correct the text,",
             f"     then save the whole file as: {path.parent / (path.name + '.corrected.md')}",
             "     and run `python -m alerte ingest`. HTML comments like this one are ignored. -->", ""]
    for p in res.pages:
        tag = f"CHECK: {'; '.join(p.flags)}" if p.flags else "ok"
        parts.append(f"<!-- PAGE {p.page}: {tag} -->")
        parts.append(p.text)
        parts.append("")
    (out / "draft.md").write_text("\n".join(parts), encoding="utf-8")
    images = 0
    try:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            import pymupdf
            with pymupdf.open(str(path)) as doc:
                for n in flagged:
                    doc[n - 1].get_pixmap(dpi=130).save(str(out / f"page-{n:03d}.png"))
                    images += 1
        elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp", ".gif"}:
            from PIL import Image, ImageSequence
            for n, fr in enumerate(ImageSequence.Iterator(Image.open(path)), 1):
                if n in flagged:
                    fr.convert("RGB").save(out / f"page-{n:03d}.png")
                    images += 1
    except Exception as e:
        print(f"(could not write page images: {e})")
    print(f"Review pack: {out}")
    print(f"  draft.md  ({len(res.pages)} pages, {len(flagged)} to check: {sorted(flagged)})")
    print(f"  {images} page image(s)")
    print(f"After proofreading, save the corrected text as:\n  {path.parent / (path.name + '.corrected.md')}\nthen run: python -m alerte ingest")
    return 0
