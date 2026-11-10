"""OCR engine: Tesseract 5 (best-quality models) with image clean-up, several passes, automatic rotation,
table-cell reading for ruled tables, and an optional pure-pip fallback (RapidOCR).

No OCR is perfect. This module therefore returns, with every reading, a confidence and an agreement score so that
pages that need a human look are flagged instead of silently trusted.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from alerte.knowledge.extract.quality import arabic_ratio, similarity

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LANG_FOR = {"fr": "fra+eng", "en": "eng+fra", "ar": "ara+eng"}
DEFAULT_LANGS = "fra+eng+ara"
CONF_ACCEPT = float(os.environ.get("ALERTE_OCR_CONF_OK", "88"))      # below this a page is flagged for review
AGREE_ACCEPT = float(os.environ.get("ALERTE_OCR_AGREE_OK", "0.97"))  # two passes should agree at least this much


# ----------------------------------------------------------------------------- discovery of the engine
@dataclass
class OcrStatus:
    tesseract: str = ""
    version: str = ""
    tessdata: str = ""
    langs: list[str] = field(default_factory=list)
    rapidocr: bool = False

    @property
    def available(self) -> bool:
        return bool(self.tesseract) or self.rapidocr

    def lang_string(self, wanted: str) -> str:
        have = set(self.langs)
        parts = [p for p in wanted.split("+") if p in have] if have else wanted.split("+")
        return "+".join(parts)

    def describe(self) -> str:
        if self.tesseract:
            return f"Tesseract {self.version}, languages: {', '.join(self.langs) or 'none'} ({self.tessdata or 'system data'})"
        if self.rapidocr:
            return "RapidOCR fallback only (no Tesseract: French accents and Arabic will be poor)"
        return "no OCR engine"


def _binary() -> str:
    env = os.environ.get("ALERTE_TESSERACT")
    if env and Path(env).exists():
        return env
    found = shutil.which("tesseract")
    if found:
        return found
    for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
              "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract", "/usr/bin/tesseract"):
        if Path(p).exists():
            return p
    return ""


def _tessdata() -> str:
    for cand in (os.environ.get("ALERTE_TESSDATA"), str(PROJECT_ROOT / "ocr" / "tessdata"), os.environ.get("TESSDATA_PREFIX")):
        if cand and any(Path(cand).glob("*.traineddata")):
            return str(Path(cand))
    return ""


_status: OcrStatus | None = None
_lock = threading.Lock()


def status(refresh: bool = False) -> OcrStatus:
    global _status
    with _lock:
        if _status is not None and not refresh:
            return _status
        st = OcrStatus()
        st.tesseract = _binary()
        st.tessdata = _tessdata()
        if st.tesseract:
            env = dict(os.environ)
            if st.tessdata:
                env["TESSDATA_PREFIX"] = st.tessdata
            try:
                out = subprocess.run([st.tesseract, "--version"], capture_output=True, text=True, timeout=20, env=env)
                m = re.search(r"tesseract\s+v?([\d.]+)", out.stdout + out.stderr)
                st.version = m.group(1) if m else "?"
                out = subprocess.run([st.tesseract, "--list-langs"], capture_output=True, text=True, timeout=20, env=env)
                st.langs = [x.strip() for x in out.stdout.splitlines()[1:] if x.strip() and x.strip() != "osd"]
            except Exception as e:  # pragma: no cover
                log.warning("Tesseract found but unusable: %s", e)
                st.tesseract = ""
        try:
            import rapidocr_onnxruntime  # noqa: F401
            st.rapidocr = True
        except Exception:
            st.rapidocr = False
        if st.tesseract and st.tessdata:
            os.environ["TESSDATA_PREFIX"] = st.tessdata
        if st.tesseract:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = st.tesseract
        _status = st
        return st


def langs_for(language: str | None, text_hint_arabic: bool = False) -> str:
    st = status()
    wanted = LANG_FOR.get((language or "").lower(), DEFAULT_LANGS)
    if text_hint_arabic and "ara" not in wanted:
        wanted = "ara+" + wanted
    return st.lang_string(wanted) or "eng"


# ----------------------------------------------------------------------------- image clean-up
def to_gray(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    if img.shape[2] == 4:
        alpha = img[:, :, 3:4].astype(np.float32) / 255.0
        img = (img[:, :, :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def scale_to_ocr_size(gray: np.ndarray) -> np.ndarray:
    """Tesseract works best near 300 dpi: scale small images up, huge ones down."""
    h, w = gray.shape[:2]
    longest = max(h, w)
    if longest < 2200:
        f = min(3.0, 2600 / longest)
        return cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    if longest > 5200:
        f = 4600 / longest
        return cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    return gray


def normalise_illumination(gray: np.ndarray) -> np.ndarray:
    """Remove shadows and uneven lighting (phone photos, yellowed paper)."""
    k = max(7, (min(gray.shape[:2]) // 80) | 1)
    bg = cv2.medianBlur(cv2.dilate(gray, np.ones((k, k), np.uint8)), k * 2 + 1 if (k * 2 + 1) % 2 else k * 2 + 2)
    diff = 255 - cv2.absdiff(gray, bg)
    return cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX)


def estimate_skew(gray: np.ndarray) -> float:
    """Skew angle in degrees (projection-profile search, coarse then fine)."""
    h, w = gray.shape[:2]
    f = 900 / max(h, w) if max(h, w) > 900 else 1.0
    small = cv2.resize(gray, None, fx=f, fy=f, interpolation=cv2.INTER_AREA) if f != 1.0 else gray
    _, bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if bw.sum() < 255 * 200:
        return 0.0
    hh, ww = bw.shape

    def score(angle: float) -> float:
        m = cv2.getRotationMatrix2D((ww / 2, hh / 2), angle, 1.0)
        r = cv2.warpAffine(bw, m, (ww, hh), flags=cv2.INTER_NEAREST)
        prof = r.sum(axis=1).astype(np.float64)
        return float(np.var(np.diff(prof)))

    best = max(np.arange(-8, 8.01, 1.0), key=score)
    best = max(np.arange(best - 1, best + 1.01, 0.2), key=score)
    return float(best)


def rotate(gray: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.15:
        return gray
    h, w = gray.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    cos, sin = abs(m[0, 0]), abs(m[0, 1])
    nw, nh = int(h * sin + w * cos), int(h * cos + w * sin)
    m[0, 2] += nw / 2 - w / 2
    m[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(gray, m, (nw, nh), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255)


def variant(gray: np.ndarray, kind: str) -> np.ndarray:
    g = scale_to_ocr_size(gray)
    if kind == "plain":
        out = g
    elif kind == "clean":
        out = cv2.fastNlMeansDenoising(normalise_illumination(g), None, 6, 7, 21)
    else:  # "binary"
        n = normalise_illumination(g)
        out = cv2.threshold(cv2.GaussianBlur(n, (3, 3), 0), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return cv2.copyMakeBorder(out, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)


# ----------------------------------------------------------------------------- reading one image
@dataclass
class Word:
    text: str
    conf: float
    x: int
    y: int
    w: int
    h: int
    line: tuple


@dataclass
class OcrReading:
    text: str = ""
    conf: float = 0.0
    lines: list[tuple[int, str, float]] = field(default_factory=list)   # (top, text, mean conf)
    words: int = 0
    engine: str = ""

    @property
    def score(self) -> float:
        return self.conf if self.words else 0.0


def _compose_lines(words: list[Word]) -> list[tuple[int, str, float]]:
    lines: dict[tuple, list[Word]] = {}
    order: list[tuple] = []
    for w in words:
        if w.line not in lines:
            lines[w.line] = []
            order.append(w.line)
        lines[w.line].append(w)
    out = []
    for key in order:
        ws = sorted(lines[key], key=lambda w: w.x)
        med_h = float(np.median([w.h for w in ws])) or 1.0
        if arabic_ratio(" ".join(w.text for w in ws)) > 0.5:
            ws = ws[::-1]                                            # right-to-left line: logical order starts at the right
        parts = [ws[0].text]
        for prev, cur in zip(ws, ws[1:]):
            gap = abs(cur.x - prev.x) - (prev.w if cur.x > prev.x else cur.w)
            parts.append(" | " if gap > 4.0 * med_h else " ")   # wide gaps = table columns without ruling
            parts.append(cur.text)
        conf = sum(w.conf * max(len(w.text), 1) for w in ws) / sum(max(len(w.text), 1) for w in ws)
        out.append((min(w.y for w in ws), "".join(parts), conf))
    return out


def _is_noise(text: str, conf: float) -> bool:
    """Lines made of rule fragments, specks or stains rather than writing."""
    alnum = sum(c.isalnum() for c in text)
    return alnum == 0 or (conf < 40 and alnum <= 3)


def _tesseract(img: np.ndarray, langs: str, psm: int) -> OcrReading:
    import pytesseract
    from PIL import Image
    st = status()
    cfg = f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
    d = pytesseract.image_to_data(Image.fromarray(img), lang=langs, config=cfg, output_type=pytesseract.Output.DICT, timeout=300)
    words = []
    for i, t in enumerate(d["text"]):
        t = (t or "").strip()
        try:
            conf = float(d["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if not t or conf < 0:
            continue
        words.append(Word(t, conf, d["left"][i], d["top"][i], d["width"][i], d["height"][i],
                          (d["block_num"][i], d["par_num"][i], d["line_num"][i])))
    lines = [ln for ln in _compose_lines(words) if not _is_noise(ln[1], ln[2])]
    keep = {t for _, t, _ in lines}
    words = [w for w in words if any(w.text in t for t in keep)]
    total = sum(max(len(w.text), 1) for w in words)
    conf = sum(w.conf * max(len(w.text), 1) for w in words) / total if total else 0.0
    return OcrReading("\n".join(t for _, t, _ in lines), conf, lines, len(words), f"tesseract {st.version} {langs} psm{psm}")


_rapid = None


def _rapidocr(img: np.ndarray) -> OcrReading:  # pragma: no cover - optional engine
    global _rapid
    from rapidocr_onnxruntime import RapidOCR
    if _rapid is None:
        _rapid = RapidOCR()
    res, _ = _rapid(img)
    lines, confs = [], []
    for box, text, score in (res or []):
        top = int(min(p[1] for p in box))
        lines.append((top, text, float(score) * 100))
        confs.append(float(score) * 100)
    lines.sort()
    return OcrReading("\n".join(t for _, t, _ in lines), sum(confs) / len(confs) if confs else 0.0, lines, len(lines), "rapidocr")


def read_image(gray: np.ndarray, langs: str, thorough: bool = False) -> OcrReading:
    """Best reading of one clean page image, from several passes. Also returns how well the passes agree."""
    st = status()
    if not st.tesseract:
        if st.rapidocr:
            r = _rapidocr(gray)
            r.engine = "rapidocr (fallback)"
            return r
        raise RuntimeError("no OCR engine installed")
    passes = [("clean", 3), ("binary", 6), ("plain", 4)]
    best = _tesseract(variant(gray, passes[0][0]), langs, passes[0][1])
    agreement = 1.0
    # sideways or upside-down scans: try the other orientations when the first reading is poor
    if best.conf < 60:
        for ang in (90, 270, 180):
            r = _tesseract(variant(np.rot90(gray, k={90: 3, 270: 1, 180: 2}[ang]).copy(), "clean"), langs, 3)
            if r.score > best.score + 15:
                best = r
                gray = np.rot90(gray, k={90: 3, 270: 1, 180: 2}[ang]).copy()
    runs = [best]
    if thorough or best.conf < 97:
        for kind, psm in passes[1:]:
            r = _tesseract(variant(gray, kind), langs, psm)
            runs.append(r)
            if not thorough and len(runs) >= 2 and r.conf >= best.conf:
                break
    runs.sort(key=lambda r: -r.score)
    best = runs[0]
    if len(runs) > 1:
        agreement = similarity(runs[0].text, runs[1].text)
    best.engine += f" (agreement {agreement:.3f} over {len(runs)} passes)"
    best.lines = list(best.lines)
    best.agreement = agreement  # type: ignore[attr-defined]
    return best


# ----------------------------------------------------------------------------- ruled tables in scans
@dataclass
class TableGrid:
    x0: int
    y0: int
    x1: int
    y1: int
    xs: list[int]
    ys: list[int]


def _cluster(idx: np.ndarray, gap: int = 4) -> list[int]:
    if len(idx) == 0:
        return []
    groups, cur = [], [int(idx[0])]
    for v in idx[1:]:
        if v - cur[-1] <= gap:
            cur.append(int(v))
        else:
            groups.append(cur)
            cur = [int(v)]
    groups.append(cur)
    return [int(sum(g) / len(g)) for g in groups]


def find_ruled_tables(gray: np.ndarray) -> list[TableGrid]:
    h, w = gray.shape[:2]
    inv = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 25, 12)
    horiz = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 25, 30), 1)))
    vert = cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 40, 25))))
    grid = cv2.dilate(cv2.add(horiz, vert), np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tables = []
    for c in cnts:
        x, y, cw, ch = cv2.boundingRect(c)
        if cw < w * 0.2 or ch < 40:
            continue
        hr, vr = horiz[y:y + ch, x:x + cw] > 0, vert[y:y + ch, x:x + cw] > 0
        xs = _cluster(np.where(vr.sum(axis=0) > 0.6 * ch)[0])
        ys = _cluster(np.where(hr.sum(axis=1) > 0.6 * cw)[0])
        if len(xs) < 2 or len(ys) < 2 or (len(xs) - 1) * (len(ys) - 1) < 4:
            continue
        if cw * ch > 0.92 * w * h and len(xs) <= 2:
            continue
        tables.append(TableGrid(x, y, x + cw, y + ch, [x + v for v in xs], [y + v for v in ys]))
    return sorted(tables, key=lambda t: t.y0)


def _erase_rules(cell: np.ndarray) -> np.ndarray:
    """Whiten ruling lines that survive inside a cell crop, which Tesseract would read as '|' or '_'."""
    inv = cv2.adaptiveThreshold(cell, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    h, w = cell.shape[:2]
    lines = cv2.add(cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(int(w * 0.6), 20), 1))),
                    cv2.morphologyEx(inv, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(int(h * 0.6), 12)))))
    out = cell.copy()
    out[cv2.dilate(lines, np.ones((5, 5), np.uint8)) > 0] = 255
    return out


def read_table(gray: np.ndarray, t: TableGrid, langs: str) -> tuple[str, float]:
    """OCR each cell of a ruled table separately; return a Markdown table and its mean confidence."""
    rows, confs = [], []
    for r in range(len(t.ys) - 1):
        row = []
        for c in range(len(t.xs) - 1):
            x0, x1, y0, y1 = t.xs[c] + 9, t.xs[c + 1] - 8, t.ys[r] + 9, t.ys[r + 1] - 8
            if x1 - x0 < 8 or y1 - y0 < 8:
                row.append("")
                continue
            cell = gray[y0:y1, x0:x1]
            if cell.size == 0 or float(cell.std()) < 6:
                row.append("")
                continue
            cell = _erase_rules(cell)
            if cell.shape[0] < 140:
                cell = cv2.resize(cell, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            cell = cv2.copyMakeBorder(cell, 24, 24, 24, 24, cv2.BORDER_CONSTANT, value=255)
            rd = OcrReading()
            for psm in (7, 6):                      # single line first, then block; keep the better reading
                try:
                    cand = _tesseract(cell, langs, psm)
                except Exception:
                    continue
                if cand.score > rd.score:
                    rd = cand
                if rd.words and rd.conf >= 90:
                    break
            row.append(" ".join(rd.text.split()).replace("|", "\\|"))
            if rd.words:
                confs.append(rd.conf)
        rows.append(row)
    rows = [r for r in rows if any(r)]
    if not rows:
        return "", 0.0
    n = max(len(r) for r in rows)
    lines = ["| " + " | ".join(rows[0] + [""] * (n - len(rows[0]))) + " |", "|" + "|".join([" --- "] * n) + "|"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r + [""] * (n - len(r))) + " |")
    return "\n".join(lines), (sum(confs) / len(confs) if confs else 0.0)


# ----------------------------------------------------------------------------- a whole page image
@dataclass
class PageOcr:
    text: str
    confidence: float
    agreement: float
    tables: int
    engine: str
    flags: list[str] = field(default_factory=list)


def ocr_page_image(img: np.ndarray, langs: str, thorough: bool = False, tables: bool = True) -> PageOcr:
    gray = to_gray(img)
    gray = scale_to_ocr_size(gray)
    skew = estimate_skew(gray)
    if abs(skew) >= 0.15:
        gray = rotate(gray, skew)
    found = find_ruled_tables(gray) if tables else []
    table_blocks: list[tuple[int, str]] = []
    tconf: list[float] = []
    masked = gray.copy()
    for t in found:
        md, c = read_table(gray, t, langs)
        if md:
            table_blocks.append((t.y0, md))
            tconf.append(c)
            cv2.rectangle(masked, (t.x0 - 14, t.y0 - 14), (t.x1 + 14, t.y1 + 14), 255, -1)
    rd = read_image(masked, langs, thorough)
    items: list[tuple[int, str]] = [(top, txt) for top, txt, _ in rd.lines] if rd.lines else []
    if table_blocks:
        # lines come from a rescaled copy of the same image, so tops share one coordinate system
        merged = sorted(items + table_blocks, key=lambda it: it[0])
        text = "\n".join(t for _, t in merged)
    else:
        text = rd.text
    conf = rd.conf if rd.words else 0.0
    if tconf:
        wn, tn = max(rd.words, 1), len(tconf)
        conf = (conf * wn + sum(tconf) * 1.0) / (wn + tn) if rd.words else sum(tconf) / tn
    agreement = float(getattr(rd, "agreement", 1.0))
    flags: list[str] = []
    if not text.strip():
        flags.append("no-text-found")
    elif conf < CONF_ACCEPT:
        flags.append(f"low-confidence ({conf:.0f})")
    if agreement < AGREE_ACCEPT and text.strip():
        flags.append(f"passes-disagree ({agreement:.2f})")
    return PageOcr(text, conf, agreement, len(table_blocks), rd.engine, flags)
