"""Synthetic documents with known ground truth, used to MEASURE extraction accuracy (python -m alerte ocr-eval).

The cases cover: digital PDF, scanned PDF (skewed, noisy, uneven light), scanned ruled table, digital table, text mixed with a
picture of text, two columns, a rotated photo, a scan carrying a garbage hidden text layer, a Word file with table and picture,
and (when an Arabic font is installed) an Arabic scan.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FR = [
    "Article 12. Les opérateurs de communications électroniques doivent relayer sans délai",
    "les alertes publiques émises par l'autorité compétente, conformément à la loi n° 2010/013.",
    "Article 13. Toute alerte est validée par un agent désigné avant sa diffusion à la population.",
    "L'Agence de régulation peut sanctionner l'opérateur qui ne respecte pas ces obligations.",
]
EN = [
    "Section 4. Mobile network operators shall transmit public warnings received from the",
    "national alerting authority to all handsets in the affected area within two minutes.",
    "The authority must publish a correction message when an alert is found to be false.",
]
AR = ["يجب على المشغلين نقل التنبيهات العامة فورا", "إلى جميع الهواتف في المنطقة المتأثرة بالخطر"]
TABLE = [["Institution", "Rôle", "Délai (min)"], ["Météo nationale", "Émettre l'avis", "10"],
         ["Protection civile", "Décider l'alerte", "5"], ["Opérateur", "Diffuser le message", "2"]]
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "C:\\Windows\\Fonts\\arial.ttf", "/Library/Fonts/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
]


@dataclass
class Case:
    name: str
    path: Path
    truth: str
    kind: str          # what it stresses
    target: float      # minimum character accuracy expected (0-1)


def _font(size: int):
    from PIL import ImageFont
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


def _arabic_font_ok() -> bool:
    return any(Path(p).exists() for p in FONT_CANDIDATES[:2])


def page_image(lines: list[str], size=(1654, 1000), font_px=34, rtl=False) -> "Image.Image":
    from PIL import Image, ImageDraw
    img = Image.new("L", size, 255)
    d = ImageDraw.Draw(img)
    f = _font(font_px)
    y = 70
    for ln in lines:
        if rtl:
            w = d.textlength(ln, font=f, direction="rtl", language="ar")
            d.text((size[0] - 80 - w, y), ln, font=f, fill=15, direction="rtl", language="ar")
        else:
            d.text((80, y), ln, font=f, fill=15)
        y += int(font_px * 1.9)
    return img


def table_image(rows: list[list[str]], font_px=34) -> "Image.Image":
    from PIL import Image, ImageDraw
    cw, rh = 460, 86
    img = Image.new("L", (cw * len(rows[0]) + 160, rh * len(rows) + 160), 255)
    d = ImageDraw.Draw(img)
    f = _font(font_px)
    x0, y0 = 80, 80
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            d.rectangle([x0 + c * cw, y0 + r * rh, x0 + (c + 1) * cw, y0 + (r + 1) * rh], outline=0, width=3)
            d.text((x0 + c * cw + 18, y0 + r * rh + 24), cell, font=f, fill=10)
    return img


def scanify(img, angle=1.8, noise=14, blur=0.6, shade=True, seed=7):
    """Make a clean render look like a photocopy: tilt, uneven light, noise, slight blur."""
    from PIL import ImageFilter
    rng = np.random.default_rng(seed)
    img = img.rotate(angle, expand=True, fillcolor=255, resample=2)
    a = np.array(img).astype(np.float32)
    if shade:
        h, w = a.shape
        gx = np.linspace(0.78, 1.0, w)[None, :]
        gy = np.linspace(0.9, 1.0, h)[:, None]
        a = a * gx * gy
    a += rng.normal(0, noise, a.shape)
    from PIL import Image
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return out.filter(ImageFilter.GaussianBlur(blur)) if blur else out


def _pdf_from_text(path: Path, lines: list[str], two_col=False):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    if two_col:
        half = len(lines) // 2
        for col, chunk in enumerate((lines[:half], lines[half:])):
            rect = pymupdf.Rect(40 + col * 280, 60, 300 + col * 280, 700)
            page.insert_textbox(rect, "\n".join(chunk), fontsize=10, fontname="helv")
    else:
        y = 70
        for ln in lines:
            page.insert_text((50, y), ln, fontsize=11, fontname="helv")
            y += 22
    doc.save(str(path))
    doc.close()


def _pdf_from_image(path: Path, img, hidden_text: str | None = None):
    import io
    import pymupdf
    doc = pymupdf.open()
    w, h = img.size
    page = doc.new_page(width=w * 72 / 200, height=h * 72 / 200)
    buf = io.BytesIO()
    img.convert("L").save(buf, format="PNG")
    page.insert_image(page.rect, stream=buf.getvalue())
    if hidden_text:
        page.insert_text((40, 60), hidden_text, fontsize=12, render_mode=3)
    doc.save(str(path))
    doc.close()


def build_corpus(out: Path) -> list[Case]:
    import pymupdf
    out.mkdir(parents=True, exist_ok=True)
    cases: list[Case] = []
    fr_truth, en_truth = "\n".join(FR), "\n".join(EN)
    table_truth = " ".join(c for r in TABLE for c in r)

    # 1 digital PDF: exact characters expected
    p = out / "digital_fr.pdf"
    _pdf_from_text(p, FR)
    cases.append(Case("digital PDF (French)", p, fr_truth, "text layer", 0.999))

    # 2 two columns
    p = out / "two_columns.pdf"
    _pdf_from_text(p, FR + EN, two_col=True)
    cases.append(Case("digital PDF, two columns", p, "\n".join(FR + EN), "reading order", 0.99))

    # 3 digital table
    p = out / "digital_table.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 60), "Tableau des délais", fontsize=12, fontname="helv")
    for r, row in enumerate(TABLE):
        for c, cell in enumerate(row):
            rect = pymupdf.Rect(50 + c * 150, 80 + r * 30, 200 + c * 150, 110 + r * 30)
            page.draw_rect(rect, color=(0, 0, 0), width=0.8)
            page.insert_text((rect.x0 + 5, rect.y0 + 20), cell, fontsize=10, fontname="helv")
    doc.save(str(p))
    doc.close()
    cases.append(Case("digital PDF with ruled table", p, "Tableau des délais " + table_truth, "table (text layer)", 0.98))

    # 4 scanned French page, tilted + noisy + uneven light
    scan = scanify(page_image(FR))
    p = out / "scan_fr.pdf"
    _pdf_from_image(p, scan)
    cases.append(Case("scanned PDF (French, tilted, noisy)", p, fr_truth, "OCR", 0.985))

    # 5 scanned English
    p = out / "scan_en.pdf"
    _pdf_from_image(p, scanify(page_image(EN), angle=-1.2, seed=3))
    cases.append(Case("scanned PDF (English)", p, en_truth, "OCR", 0.985))

    # 6 scanned ruled table
    p = out / "scan_table.pdf"
    _pdf_from_image(p, scanify(table_image(TABLE), angle=0.9, noise=10))
    cases.append(Case("scanned PDF with ruled table", p, table_truth, "table (OCR cells)", 0.97))

    # 7 rotated photo as PNG (sideways, low resolution)
    from PIL import Image
    small = page_image(FR, size=(1500, 700), font_px=24)
    small = scanify(small.rotate(90, expand=True, fillcolor=255), angle=0.7, noise=9)
    p = out / "photo_sideways.png"
    small.save(p)
    cases.append(Case("sideways low-resolution image", p, fr_truth, "rotation + low resolution", 0.97))

    # 8 text + a picture that contains text
    p = out / "mixed_text_image.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 70), "Rapport de situation du 12 mars", fontsize=12, fontname="helv")
    import io
    pic = page_image(["Zone inondée: quartier Bonamoussadi", "Évacuation avant 18 h"], size=(900, 260), font_px=40)
    buf = io.BytesIO()
    pic.save(buf, format="PNG")
    page.insert_image(pymupdf.Rect(50, 100, 450, 215), stream=buf.getvalue())
    page.insert_text((50, 260), "Contact: centre des opérations, poste 4412", fontsize=11, fontname="helv")
    doc.save(str(p))
    doc.close()
    cases.append(Case("text mixed with a picture of text", p,
                      "Rapport de situation du 12 mars Zone inondée: quartier Bonamoussadi Évacuation avant 18 h "
                      "Contact: centre des opérations, poste 4412", "mixed content", 0.97))

    # 9 scan with a garbage hidden text layer (a bad earlier OCR)
    p = out / "scan_bad_layer.pdf"
    _pdf_from_image(p, scanify(page_image(FR), seed=11), hidden_text="xqzv wkrt bvnm plkj hgfd qwrt zxcv bnmk vbnm tgbn ynhu mjik")
    cases.append(Case("scan with a corrupt hidden text layer", p, fr_truth, "layer vs OCR", 0.985))

    # 10 Word with table and picture
    try:
        import docx
        from docx.shared import Inches
        p = out / "report.docx"
        d = docx.Document()
        d.add_heading("Note de service", 1)
        d.add_paragraph(FR[0] + " " + FR[1])
        t = d.add_table(rows=len(TABLE), cols=3)
        for r, row in enumerate(TABLE):
            for c, cell in enumerate(row):
                t.cell(r, c).text = cell
        pic_path = out / "_pic.png"
        page_image(["Alerte rouge: Douala, 06 h 20"], size=(900, 160), font_px=44).save(pic_path)
        d.add_picture(str(pic_path), width=Inches(4))
        d.save(str(p))
        cases.append(Case("Word with heading, table and picture", p,
                          "Note de service " + FR[0] + " " + FR[1] + " " + table_truth + " Alerte rouge: Douala, 06 h 20", "office", 0.97))
    except ImportError:
        pass

    # 11 Arabic scan
    if _arabic_font_ok():
        p = out / "scan_ar.pdf"
        _pdf_from_image(p, scanify(page_image(AR, rtl=True, font_px=44), angle=1.0, noise=8))
        cases.append(Case("scanned PDF (Arabic)", p, "\n".join(AR), "Arabic OCR", 0.93))
    return cases


def flatten(text: str) -> str:
    """Make Markdown tables and section marks comparable to plain ground truth."""
    import re
    text = re.sub(r"\[Text in image\]", " ", text)
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.M)
    text = re.sub(r"\|\s*-{3,}\s*", " ", text)
    text = text.replace("|", " ")
    return text


def evaluate(cases: list[Case], thorough: bool = False) -> list[dict]:
    import time

    from alerte.knowledge.extract import extract_file
    from alerte.knowledge.extract.quality import cer
    rows = []
    for c in cases:
        t0 = time.time()
        r = extract_file(c.path, "fr" if "English" not in c.name and "Arabic" not in c.name else ("en" if "English" in c.name else "ar"),
                         use_cache=False, thorough=thorough)
        got = flatten(r.text)
        err = cer(c.truth, got) if got.strip() else 1.0
        rows.append({"case": c.name, "stress": c.kind, "method": r.method, "ocr_conf": r.mean_confidence,
                     "accuracy": round(1 - min(err, 1.0), 4), "target": c.target, "ok": (1 - err) >= c.target and not r.failed,
                     "flagged": bool(r.review_pages), "failed": r.failed, "seconds": round(time.time() - t0, 1)})
    return rows
