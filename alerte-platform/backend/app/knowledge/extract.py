"""Extraction de texte : PDF (pdfplumber + OCR Tesseract des pages pauvres), DOCX, MD, TXT, CSV.

Aucun échec silencieux : une page non lisible (OCR indisponible, langue manquante, confiance basse) est marquée « à relire »
avec sa raison. PyMuPDF n'est jamais utilisé (AGPL).
"""
from __future__ import annotations

import csv
import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("alerte.knowledge.extract")

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt", ".csv"}
MIN_PAGE_CHARS = 80
MAX_PDF_PAGES = 3000
MAX_CSV_ROWS = 200_000
OCR_MIN_CONFIDENCE = 60.0
OCR_DPI = 250


class ExtractionError(Exception):
    """Fichier refusé ou illisible (message destiné à l'utilisateur)."""

    def __init__(self, message: str, code: str = "kb.document.unreadable") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class Page:
    number: int | None
    text: str
    method: str = "text"            # text|ocr|none
    ocr_confidence: float | None = None
    review_reason: str | None = None


@dataclass
class Extraction:
    pages: list[Page]
    method: str                     # pdf-text|pdf-ocr|pdf-mixed|docx|markdown|text|csv
    paged: bool = True
    rows: list[str] = field(default_factory=list)   # CSV : une ligne = un chunk
    warnings: list[str] = field(default_factory=list)


def sniff_kind(ext: str, head: bytes, path: Path) -> str:
    """Vérifie le type réel (signature) ; renvoie pdf|docx|md|txt|csv ou lève ExtractionError."""
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ExtractionError(f"extension non autorisée : {ext or '(aucune)'}", "kb.document.bad_type")
    if ext == ".pdf":
        if not head.startswith(b"%PDF-"):
            raise ExtractionError("le fichier n'est pas un PDF (signature absente)", "kb.document.bad_type")
        return "pdf"
    if ext == ".docx":
        if not head.startswith(b"PK"):
            raise ExtractionError("le fichier n'est pas un DOCX (signature absente)", "kb.document.bad_type")
        try:
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                if "word/document.xml" not in names:
                    raise ExtractionError("DOCX invalide (word/document.xml absent)", "kb.document.bad_type")
                total = sum(i.file_size for i in z.infolist())
                if total > 500 * 1024 * 1024 or len(names) > 10_000:
                    raise ExtractionError("DOCX refusé (taille décompressée excessive)", "kb.document.bad_type")
        except zipfile.BadZipFile as exc:
            raise ExtractionError("DOCX corrompu", "kb.document.bad_type") from exc
        return "docx"
    if b"\x00" in head and not head.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ExtractionError("fichier binaire refusé pour une extension texte", "kb.document.bad_type")
    return {".md": "md", ".markdown": "md", ".txt": "txt", ".csv": "csv"}[ext]


def decode_text(data: bytes) -> tuple[str, list[str]]:
    for enc in ("utf-8-sig",):
        try:
            return data.decode(enc), []
        except UnicodeDecodeError:
            pass
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), []
    return data.decode("cp1252", errors="replace"), ["encodage non UTF-8 : décodé en cp1252 (à vérifier)"]


# --------------------------------------------------------------------------- OCR
class OcrEngine:
    """Enveloppe Tesseract ; `status` explique pourquoi l'OCR est indisponible ou partiel."""

    def __init__(self, langs: str, tessdata_dir: Path | None) -> None:
        self.requested = [x for x in (langs or "eng").split("+") if x]
        self.tessdata = Path(tessdata_dir) if tessdata_dir else None
        self.available: list[str] = []
        self.missing: list[str] = list(self.requested)
        self.error: str | None = None
        try:
            import pytesseract
            self._tess = pytesseract
            have = set(pytesseract.get_languages(config=self._config()))
            self.available = [x for x in self.requested if x in have]
            self.missing = [x for x in self.requested if x not in have]
            if not self.available:
                self.error = f"langues OCR absentes : {', '.join(self.requested)}"
        except Exception as exc:  # noqa: BLE001 - Tesseract absent, chemin invalide…
            self._tess = None
            self.error = f"Tesseract indisponible : {str(exc)[:120]}"

    def _config(self) -> str:
        return f'--tessdata-dir "{self.tessdata}"' if self.tessdata else ""

    @property
    def usable(self) -> bool:
        return self._tess is not None and bool(self.available)

    def read(self, image) -> tuple[str, float]:  # noqa: ANN001
        data = self._tess.image_to_data(image, lang="+".join(self.available), config=self._config(),
                                        output_type=self._tess.Output.DICT)
        words, confs, last_line = [], [], None
        for txt, conf, key in zip(data["text"], data["conf"], zip(data["block_num"], data["par_num"], data["line_num"],
                                                                 strict=False), strict=False):
            if not str(txt).strip():
                continue
            if last_line is not None and key != last_line:
                words.append("\n")
            last_line = key
            words.append(str(txt) + " ")
            try:
                if float(conf) >= 0:
                    confs.append(float(conf))
            except ValueError:
                pass
        text = "".join(words).replace(" \n", "\n").strip()
        return text, (sum(confs) / len(confs) if confs else 0.0)



# --------------------------------------------------------------------------- arabe : ordre visuel → logique
_AR_LETTER = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_AR_COMMON = {"في", "من", "على", "أو", "أن", "إلى", "عن", "هذا", "هذه", "التي", "الذي", "يجب", "كل", "مع", "لا", "ما", "أي",
              "قانون", "المادة", "الى", "او", "ان", "تم", "هو", "كما", "بعد", "عند", "ذلك", "جميع"}
_LTR_RUN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9.,:/%\-]*[A-Za-z0-9])?")


def _ar_ratio(line: str) -> float:
    letters = [c for c in line if c.isalpha()]
    return sum(1 for c in letters if _AR_LETTER.match(c)) / len(letters) if letters else 0.0


def _reverse_visual(line: str) -> str:
    rev = line[::-1]
    return _LTR_RUN.sub(lambda m: m.group(0)[::-1], rev)


def _ar_score(lines: list[str]) -> int:
    return sum(1 for ln in lines for w in re.findall(r"[\u0600-\u06FF]+", ln) if w in _AR_COMMON)


def fix_arabic_visual_order(text: str) -> str:
    """pdfplumber restitue souvent l'arabe dans l'ordre VISUEL (inversé). On inverse les lignes arabes si — et seulement si —
    le texte inversé contient nettement plus de mots arabes courants (décision par page, jamais à l'aveugle)."""
    if not _AR_LETTER.search(text):
        return text
    import unicodedata
    lines = text.split("\n")
    idx = [i for i, ln in enumerate(lines) if _ar_ratio(ln) > 0.5]
    if not idx:
        return text
    as_is = [unicodedata.normalize("NFKC", lines[i]) for i in idx]
    flipped = [unicodedata.normalize("NFKC", _reverse_visual(lines[i])) for i in idx]
    if _ar_score(flipped) > _ar_score(as_is):
        for i, f in zip(idx, flipped, strict=True):
            lines[i] = f
    else:
        for i, a in zip(idx, as_is, strict=True):
            lines[i] = a
    return "\n".join(lines)

# --------------------------------------------------------------------------- formats
def extract_pdf(path: Path, ocr: OcrEngine | None) -> Extraction:
    import pdfplumber
    import pypdfium2 as pdfium

    pages: list[Page] = []
    warnings: list[str] = []
    try:
        pdf = pdfplumber.open(path)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "password" in msg or "encrypt" in msg:
            raise ExtractionError("PDF chiffré : refusé", "kb.document.encrypted") from exc
        raise ExtractionError(f"PDF illisible : {str(exc)[:150]}") from exc
    with pdf:
        n = len(pdf.pages)
        if n > MAX_PDF_PAGES:
            raise ExtractionError(f"PDF trop volumineux ({n} pages, maximum {MAX_PDF_PAGES})", "kb.document.too_large")
        ocr_doc = None
        for i, page in enumerate(pdf.pages, start=1):
            try:
                txt = page.extract_text() or ""
            except Exception as exc:  # noqa: BLE001
                txt = ""
                warnings.append(f"page {i} : extraction du texte en échec ({str(exc)[:80]})")
            if len(txt.strip()) >= MIN_PAGE_CHARS:
                pages.append(Page(i, fix_arabic_visual_order(txt)))
                continue
            # page pauvre → OCR, ou marquage « à relire » explicite
            if ocr is None or not ocr.usable:
                reason = (ocr.error if ocr else "OCR désactivé") or "OCR indisponible"
                pages.append(Page(i, txt, "none", None, f"page pauvre ({len(txt.strip())} car.) ; {reason}"))
                continue
            try:
                if ocr_doc is None:
                    ocr_doc = pdfium.PdfDocument(str(path))
                image = ocr_doc[i - 1].render(scale=OCR_DPI / 72).to_pil()
                otext, conf = ocr.read(image)
            except Exception as exc:  # noqa: BLE001
                pages.append(Page(i, txt, "none", None, f"OCR en échec : {str(exc)[:100]}"))
                continue
            reasons = []
            if ocr.missing:
                reasons.append(f"langues OCR manquantes : {', '.join(ocr.missing)}")
            if conf < OCR_MIN_CONFIDENCE:
                reasons.append(f"confiance OCR basse ({conf:.0f})")
            if len(otext) < 20:
                reasons.append("quasi aucun texte reconnu")
            pages.append(Page(i, otext if len(otext) >= len(txt) else txt, "ocr", conf, "; ".join(reasons) or None))
        if ocr_doc is not None:
            ocr_doc.close()
    kinds = {p.method for p in pages}
    method = "pdf-text" if kinds <= {"text"} else ("pdf-ocr" if "text" not in kinds else "pdf-mixed")
    return Extraction(pages, method, True, warnings=warnings)


def extract_docx(path: Path) -> Extraction:
    import docx

    try:
        d = docx.Document(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"DOCX illisible : {str(exc)[:150]}") from exc
    lines: list[str] = []
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(child, d)
            txt = para.text.strip()
            if not txt:
                lines.append("")
                continue
            style = (para.style.name if para.style is not None else "") or ""
            m = re.match(r"Heading (\d)", style) or re.match(r"Titre (\d)", style)
            lines.append(f"{'#' * int(m.group(1))} {txt}" if m else txt)
        elif tag == "tbl":
            for row in Table(child, d).rows:
                cells = [c.text.strip().replace("\n", " ") for c in row.cells]
                lines.append("| " + " | ".join(cells) + " |")
    return Extraction([Page(None, "\n".join(lines))], "docx", paged=False)


def extract_text_file(path: Path, kind: str) -> Extraction:
    text, warns = decode_text(path.read_bytes())
    return Extraction([Page(None, text)], "markdown" if kind == "md" else "text", paged=False, warnings=warns)


def extract_csv(path: Path) -> Extraction:
    text, warns = decode_text(path.read_bytes())
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    csv.field_size_limit(1 << 20)
    reader = csv.reader(io.StringIO(text), dialect)
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration as exc:
        raise ExtractionError("CSV vide") from exc
    rows: list[str] = []
    for i, row in enumerate(reader):
        if i >= MAX_CSV_ROWS:
            warns.append(f"CSV tronqué à {MAX_CSV_ROWS} lignes")
            break
        parts = [f"{h or f'col{j + 1}'}: {v.strip()}" for j, (h, v) in enumerate(zip(header, row, strict=False))
                 if v.strip()]
        if parts:
            rows.append("; ".join(parts))
    return Extraction([Page(None, "\n".join(rows))], "csv", paged=False, rows=rows, warnings=warns)


def extract(path: Path, ext: str, ocr: OcrEngine | None) -> Extraction:
    with path.open("rb") as fh:
        head = fh.read(4096)
    kind = sniff_kind(ext, head, path)
    if kind == "pdf":
        return extract_pdf(path, ocr)
    if kind == "docx":
        return extract_docx(path)
    if kind == "csv":
        return extract_csv(path)
    return extract_text_file(path, kind)
