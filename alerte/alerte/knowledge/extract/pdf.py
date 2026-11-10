"""PDF extraction, page by page, choosing the most reliable source for each page.

    digital page            exact characters from the text layer (no OCR error possible), tables rebuilt as Markdown,
                            text inside large embedded images read by OCR
    scanned page            full OCR (clean-up, several passes, ruled tables read cell by cell)
    scan with a text layer  both are read and compared; disagreement is flagged
    Arabic pages            always cross-checked with OCR (text-layer order and shaping are unreliable)
"""

from __future__ import annotations

import logging
import os
import re
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from alerte.knowledge.extract import ocr
from alerte.knowledge.extract.quality import arabic_ratio, norm, similarity, text_layer_trust
from alerte.knowledge.extract.result import ExtractionResult, PageResult

log = logging.getLogger(__name__)
DPI = int(os.environ.get("ALERTE_OCR_DPI", "300"))
WORKERS = int(os.environ.get("ALERTE_OCR_WORKERS", str(max(1, min(4, (os.cpu_count() or 2) - 1)))))
MIN_LAYER_CHARS = 80


def _pymupdf():
    try:
        import pymupdf
        return pymupdf
    except ImportError:  # pragma: no cover
        import fitz  # type: ignore
        return fitz


def _render(page, clip=None, dpi: int = DPI) -> np.ndarray:
    pix = page.get_pixmap(dpi=dpi, clip=clip, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return img[:, :, ::-1].copy() if pix.n == 3 else img[:, :, 0].copy()


def _md_table(rows: list[list[str | None]]) -> str:
    rows = [[" ".join((c or "").split()).replace("|", "\\|") for c in r] for r in rows]
    rows = [r for r in rows if any(r)]
    if len(rows) < 1 or max(len(r) for r in rows) < 2:
        return ""
    n = max(len(r) for r in rows)
    out = ["| " + " | ".join(rows[0] + [""] * (n - len(rows[0]))) + " |", "|" + "|".join([" --- "] * n) + "|"]
    out += ["| " + " | ".join(r + [""] * (n - len(r))) + " |" for r in rows[1:]]
    return "\n".join(out)


def pymupdf_rect(bbox):
    return _pymupdf().Rect(bbox)


def _block_text(block: dict) -> str:
    lines = []
    for ln in block.get("lines", []):
        t = "".join(sp["text"] for sp in ln.get("spans", []))
        if t.strip():
            lines.append(t.rstrip())
    return "\n".join(lines)


def _overlap(a, b) -> float:
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    inter = (x1 - x0) * (y1 - y0)
    area = max((a[2] - a[0]) * (a[3] - a[1]), 1e-6)
    return inter / area


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text) if arabic_ratio(text) > 0.2 else text
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text.replace(" ", " ").replace("\r", "")


def _layer(page) -> tuple[list[tuple[float, str]], list[tuple[float, str]], list[str]]:
    """(text blocks with y, tables with y, flags) in stream order, tables removed from the text."""
    flags: list[str] = []
    tables: list[tuple[float, str, tuple]] = []
    try:
        for t in page.find_tables().tables:
            rows = []
            try:   # read each cell from its own rectangle: keeps spaces, accents and line breaks exact
                for row in t.rows:
                    rows.append([" ".join(page.get_text("text", clip=pymupdf_rect(c)).split()) if c else "" for c in row.cells])
            except Exception:
                rows = t.extract()
            md = _md_table(rows)
            if md:
                tables.append((t.bbox[1], md, tuple(t.bbox)))
    except Exception as e:  # table finder is best-effort
        log.debug("find_tables failed: %s", e)
    blocks = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        if any(_overlap(b["bbox"], t[2]) > 0.5 for t in tables):
            continue
        txt = _block_text(b)
        if txt.strip():
            blocks.append((b["bbox"][1], txt))
    return blocks, [(y, md) for y, md, _ in tables], flags


def _image_rects(page) -> list:
    pm = _pymupdf()
    rects = []
    try:
        for info in page.get_image_info():
            r = pm.Rect(info["bbox"]) & page.rect
            if not r.is_empty:
                rects.append(r)
    except Exception:
        pass
    return rects


def _coverage(page, rects) -> float:
    if not rects:
        return 0.0
    # union area by rasterising rectangles at low resolution
    w, h = max(int(page.rect.width // 4), 1), max(int(page.rect.height // 4), 1)
    m = np.zeros((h, w), bool)
    for r in rects:
        m[int(r.y0 // 4):int(np.ceil(r.y1 / 4)), int(r.x0 // 4):int(np.ceil(r.x1 / 4))] = True
    mask_area = m.sum() / m.size
    return float(mask_area)


def _process_page(doc, i: int, language: str | None, thorough: bool) -> PageResult:
    page = doc[i]
    num = i + 1
    blocks, tables, flags = _layer(page)
    ordered = [t for _, t in blocks]
    layer_text = _clean("\n".join(ordered))
    table_text = [md for _, md in tables]
    layer_chars = len(re.sub(r"\s", "", layer_text + "".join(table_text)))
    trusted, why = text_layer_trust(layer_text)
    rects = _image_rects(page)
    cover = _coverage(page, rects)
    arabic = arabic_ratio(layer_text) > 0.25
    langs = ocr.langs_for(language, arabic)
    st = ocr.status()

    def merge_layer(extra: list[tuple[float, str]] | None = None) -> str:
        items = list(blocks)
        # keep stream order, insert tables and image text near their vertical position
        out: list[str] = []
        pending = sorted([(y, md) for y, md in tables] + (extra or []), key=lambda x: x[0])
        for y, txt in items:
            while pending and pending[0][0] <= y:
                out.append(pending.pop(0)[1])
            out.append(txt)
        out += [p[1] for p in pending]
        return _clean("\n".join(out))

    try:
        drawings = len(page.get_drawings()) if layer_chars < MIN_LAYER_CHARS else 0
    except Exception:
        drawings = 0
    # a page with a short but real text layer (title page, signature page) keeps its exact characters
    need_ocr = (layer_chars == 0 or not trusted
                or (layer_chars < MIN_LAYER_CHARS and (cover >= 0.6 or drawings > 30)))
    verify = (not need_ocr) and (cover >= 0.6 or arabic)

    if need_ocr or verify:
        if not st.available:
            if need_ocr:
                return PageResult(num, merge_layer() if layer_chars else "", "text-layer" if layer_chars else "none", None, None, len(tables), 0,
                                  ["NEEDS-OCR-ENGINE: this page is an image or its text layer is broken; install Tesseract (python -m alerte ocr-setup)"] + [f"text-layer-untrusted ({', '.join(why)})"] * bool(why))
            return PageResult(num, merge_layer(), "text-layer", None, None, len(tables), 0, ["not cross-checked: no OCR engine"] if arabic else [])
        try:
            res = ocr.ocr_page_image(_render(page), langs, thorough)
        except Exception as e:
            log.warning("OCR failed on page %d of %s: %s", num, doc.name, e)
            if layer_chars and not need_ocr:
                return PageResult(num, merge_layer(), "text-layer", None, None, len(tables), 0, [f"cross-check failed: {e}"])
            return PageResult(num, merge_layer() if layer_chars else "", "none", None, None, 0, 0, [f"OCR-FAILED: {e}"])
        if need_ocr:
            note = (f" (text layer ignored: {', '.join(why)})" if why else " (text layer too short for a page that is an image)") if layer_chars else ""
            return PageResult(num, res.text, "ocr" + note, round(res.confidence, 1), round(res.agreement, 3), res.tables, 0, list(res.flags))
        agree = similarity(layer_text + "\n" + "\n".join(table_text), res.text)
        if agree >= 0.90:
            return PageResult(num, merge_layer(), "text-layer (verified by OCR)", None, round(agree, 3), len(tables), 0, [])
        fl = [f"text-layer-and-OCR-disagree ({agree:.2f})"]
        if res.confidence >= ocr.CONF_ACCEPT and (agree < 0.75 or arabic):
            fl.append("used OCR reading")
            return PageResult(num, res.text, "ocr", round(res.confidence, 1), round(agree, 3), res.tables, 0, fl)
        fl.append("kept text layer")
        return PageResult(num, merge_layer(), "text-layer", None, round(agree, 3), len(tables), 0, fl)

    # digital page: add the text found inside meaningful embedded images (charts, stamps, pasted screenshots)
    extra: list[tuple[float, str]] = []
    imgs_done, fl = 0, []
    if st.available:
        page_area = page.rect.width * page.rect.height
        for r in rects:
            if r.width * r.height < 0.03 * page_area or min(r.width, r.height) < 36:
                continue
            try:
                res = ocr.ocr_page_image(_render(page, clip=r), langs, False, tables=True)
            except Exception:
                continue
            words = len(res.text.split())
            if words >= 3 and res.confidence >= 65:
                extra.append((r.y0, "[Text in image] " + res.text.replace("\n", " ")))
                imgs_done += 1
                if res.confidence < ocr.CONF_ACCEPT:
                    fl.append(f"image-text-low-confidence ({res.confidence:.0f})")
    method = "text-layer+image-ocr" if imgs_done else "text-layer"
    return PageResult(num, merge_layer(extra), method, None, None, len(tables), imgs_done, fl)


def extract_pdf(path: Path, language: str | None = None, thorough: bool = False) -> ExtractionResult:
    pm = _pymupdf()
    res = ExtractionResult(path=str(path))
    try:
        doc = pm.open(str(path))
    except Exception as e:
        res.failed = f"cannot open PDF: {e}"
        return res
    if doc.needs_pass and not doc.authenticate(""):
        res.failed = "PDF is password protected: remove the password and retry"
        return res
    n = doc.page_count
    doc.close()
    local = threading.local()

    def worker(i: int) -> PageResult:
        if not hasattr(local, "doc"):
            local.doc = pm.open(str(path))
            if local.doc.needs_pass:
                local.doc.authenticate("")
        try:
            return _process_page(local.doc, i, language, thorough)
        except Exception as e:
            log.exception("page %d of %s failed", i + 1, path.name)
            return PageResult(i + 1, "", "none", None, None, 0, 0, [f"PAGE-FAILED: {e}"])

    if n <= 1 or WORKERS <= 1:
        res.pages = [worker(i) for i in range(n)]
    else:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            res.pages = list(ex.map(worker, range(n)))
    if not res.text.strip():
        res.failed = res.failed or "no text could be extracted from any page"
    return res
