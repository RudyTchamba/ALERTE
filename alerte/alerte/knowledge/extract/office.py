"""Word, PowerPoint, Excel, OpenDocument, RTF, EPUB, HTML, CSV and plain-text files.

Text and tables come out in document order; tables become Markdown; pictures that contain text are read by OCR.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np

from alerte.knowledge.extract import ocr
from alerte.knowledge.extract.pdf import _md_table
from alerte.knowledge.extract.result import ExtractionResult, PageResult

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def _ocr_bytes(data: bytes, language: str | None) -> tuple[str, float] | None:
    """Text inside an embedded picture, or None when it has none worth keeping."""
    st = ocr.status()
    if not st.available:
        return None
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)).convert("RGB")
        if min(im.size) < 60 or im.size[0] * im.size[1] < 20000:
            return None
        arr = np.array(im)[:, :, ::-1].copy()
        r = ocr.ocr_page_image(arr, ocr.langs_for(language), False)
        if len(r.text.split()) >= 3 and r.confidence >= 65:
            return r.text.replace("\n", " "), r.confidence
    except Exception:
        return None
    return None


# ----------------------------------------------------------------------------------------------- docx
def extract_docx(path: Path, language: str | None = None) -> ExtractionResult:
    res = ExtractionResult(path=str(path))
    try:
        import docx
    except ImportError:
        res.failed = "python-docx is not installed (pip install python-docx)"
        return res
    try:
        d = docx.Document(str(path))
    except Exception as e:
        res.failed = f"cannot open Word file: {e}"
        return res
    parts: list[str] = []
    flags: list[str] = []
    n_img = 0
    rels = d.part.related_parts

    def para_text(p) -> str:
        t = "".join(x.text or "" for x in p.iter(W + "t") if not any(a.tag.endswith("Fallback") for a in x.iterancestors()))
        return t.strip()

    def table_md(tbl) -> str:
        rows = []
        for tr in tbl.iter(W + "tr"):
            cells = []
            for tc in tr.findall(W + "tc"):
                cells.append(" ".join(para_text(p) for p in tc.iter(W + "p") if para_text(p)))
            rows.append(cells)
        return _md_table(rows) or "\n".join(" | ".join(r) for r in rows)

    body = d.element.body
    for el in body.iterchildren():
        if el.tag == W + "p":
            t = para_text(el)
            style = el.find(f"{W}pPr/{W}pStyle")
            if t and style is not None and (style.get(W + "val") or "").lower().startswith("heading"):
                t = "## " + t
            if t:
                parts.append(t)
            for blip in el.iter(A + "blip"):
                rid = blip.get(R + "embed")
                if rid in rels:
                    got = _ocr_bytes(rels[rid].blob, language)
                    if got:
                        parts.append("[Text in image] " + got[0])
                        n_img += 1
                        if got[1] < ocr.CONF_ACCEPT:
                            flags.append(f"image-text-low-confidence ({got[1]:.0f})")
        elif el.tag == W + "tbl":
            parts.append(table_md(el))
    for sec in d.sections:   # headers and footers often carry the law's title or the issuing body
        for part in (sec.header, sec.footer):
            try:
                t = " ".join(p.text.strip() for p in part.paragraphs if p.text.strip())
                if t and t not in parts:
                    parts.append(t)
            except Exception:
                pass
    res.pages.append(PageResult(1, "\n\n".join(parts), "native" if not n_img else "native+image-ocr", None, None,
                                len(d.tables), n_img, flags))
    if not res.text.strip():
        res.failed = "the Word file contains no text"
    return res


# ------------------------------------------------------------------------------------------------ pptx
def extract_pptx(path: Path, language: str | None = None) -> ExtractionResult:
    res = ExtractionResult(path=str(path))
    try:
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
    except ImportError:
        res.failed = "python-pptx is not installed (pip install python-pptx)"
        return res
    try:
        prs = Presentation(str(path))
    except Exception as e:
        res.failed = f"cannot open PowerPoint file: {e}"
        return res

    def walk(shapes, out, flags, counter):
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                walk(sh.shapes, out, flags, counter)
            elif getattr(sh, "has_table", False) and sh.has_table:
                out.append(_md_table([[c.text for c in r.cells] for r in sh.table.rows]))
                counter[0] += 1
            elif sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                got = _ocr_bytes(sh.image.blob, language)
                if got:
                    out.append("[Text in image] " + got[0])
                    counter[1] += 1
                    if got[1] < ocr.CONF_ACCEPT:
                        flags.append(f"image-text-low-confidence ({got[1]:.0f})")
            elif getattr(sh, "has_text_frame", False) and sh.has_text_frame and sh.text_frame.text.strip():
                out.append(sh.text_frame.text.strip())

    for n, slide in enumerate(prs.slides, 1):
        out, flags, counter = [], [], [0, 0]
        walk(slide.shapes, out, flags, counter)
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            nt = slide.notes_slide.notes_text_frame.text.strip()
            if nt:
                out.append("Notes: " + nt)
        res.pages.append(PageResult(n, "\n".join(out), "native", None, None, counter[0], counter[1], flags))
    if not res.text.strip():
        res.failed = "the presentation contains no text"
    return res


# ----------------------------------------------------------------------------------------- xlsx / xls
def extract_xlsx(path: Path) -> ExtractionResult:
    res = ExtractionResult(path=str(path))
    try:
        import openpyxl
        wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    except Exception as e:
        res.failed = f"cannot open Excel file: {e}"
        return res
    for n, ws in enumerate(wb.worksheets, 1):
        rows = [["" if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]
        res.pages.append(PageResult(n, f"## Sheet: {ws.title}\n" + (_md_table(rows) or "\n".join(" | ".join(r) for r in rows)), "native", None, None, 1))
    if not res.text.strip():
        res.failed = "the workbook contains no data"
    return res


def extract_xls(path: Path) -> ExtractionResult:
    res = ExtractionResult(path=str(path))
    try:
        import xlrd
        wb = xlrd.open_workbook(str(path))
    except ImportError:
        res.failed = "xlrd is not installed (pip install xlrd) for legacy .xls files"
        return res
    except Exception as e:
        res.failed = f"cannot open Excel file: {e}"
        return res
    for n, sh in enumerate(wb.sheets(), 1):
        rows = [[str(c.value) for c in sh.row(i)] for i in range(sh.nrows)]
        res.pages.append(PageResult(n, f"## Sheet: {sh.name}\n" + (_md_table(rows) or ""), "native", None, None, 1))
    if not res.text.strip():
        res.failed = "the workbook contains no data"
    return res


# --------------------------------------------------------------------------------------------- odf
def extract_odf(path: Path) -> ExtractionResult:
    res = ExtractionResult(path=str(path))
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("content.xml"))
    except Exception as e:
        res.failed = f"cannot open OpenDocument file: {e}"
        return res
    ns_text = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    ns_table = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
    out: list[str] = []
    for el in root.iter():
        if el.tag in (ns_text + "p", ns_text + "h"):
            t = "".join(el.itertext()).strip()
            if t:
                out.append(t)
        elif el.tag == ns_table + "table":
            rows = []
            for tr in el.iter(ns_table + "table-row"):
                rows.append(["".join(c.itertext()).strip() for c in tr.findall(ns_table + "table-cell")])
            md = _md_table(rows)
            if md:
                out.append(md)
    res.pages.append(PageResult(1, "\n".join(out), "native", None, None, 0))
    if not res.text.strip():
        res.failed = "the document contains no text"
    return res


# ------------------------------------------------------------------------------------- plain family
def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            txt = raw.decode(enc)
            if enc == "utf-16" and not raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return txt
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text_family(path: Path) -> ExtractionResult:
    res = ExtractionResult(path=str(path))
    suffix = path.suffix.lower()
    try:
        raw = path.read_bytes()
    except Exception as e:
        res.failed = f"cannot read file: {e}"
        return res
    if suffix == ".epub":
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                names = sorted(n for n in z.namelist() if n.lower().endswith((".xhtml", ".html", ".htm")))
                text = "\n\n".join(_html_to_text(_decode(z.read(n))) for n in names)
        except Exception as e:
            res.failed = f"cannot open EPUB: {e}"
            return res
    else:
        text = _decode(raw)
        if suffix in (".html", ".htm", ".xhtml"):
            text = _html_to_text(text)
        elif suffix == ".rtf":
            text = _rtf_to_text(text)
        elif suffix in (".csv", ".tsv"):
            try:
                rows = list(csv.reader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else csv.Sniffer().sniff(text[:4096]).delimiter))
                text = _md_table(rows) or text
            except Exception:
                pass
        elif suffix == ".md":
            text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
            lines = text.lstrip().split("\n")
            i = 0
            while i < len(lines) and (lines[i].startswith(">") or not lines[i].strip()):
                i += 1
            text = "\n".join(lines[i:])
    res.pages.append(PageResult(1, text.replace("\r", "").strip(), "native"))
    if not res.text.strip():
        res.failed = "the file is empty"
    return res


def _html_to_text(raw: str) -> str:
    import html
    raw = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", raw)
    # tables to Markdown-like rows before tags are stripped
    def tbl(m):
        rows = re.findall(r"(?is)<tr.*?>(.*?)</tr>", m.group(0))
        cells = [[html.unescape(re.sub(r"<[^>]+>", " ", c)).strip() for c in re.findall(r"(?is)<t[hd].*?>(.*?)</t[hd]>", r)] for r in rows]
        return "\n" + (_md_table([[" ".join(c.split()) for c in r] for r in cells]) or "") + "\n"
    raw = re.sub(r"(?is)<table.*?</table>", tbl, raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</div>|</tr>", "\n", raw)
    raw = re.sub(r"(?is)<h(\d)[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", raw)
    raw = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", raw)).strip()


def _rtf_to_text(raw: str) -> str:
    try:
        from striprtf.striprtf import rtf_to_text
        return rtf_to_text(raw)
    except ImportError:
        raw = re.sub(r"\\'([0-9a-f]{2})", lambda m: bytes.fromhex(m.group(1)).decode("cp1252", "replace"), raw)
        raw = re.sub(r"\\par[d]?", "\n", raw)
        raw = re.sub(r"\{\\\*[^{}]*\}|\\[a-z]+-?\d* ?|[{}]", "", raw)
        return raw
