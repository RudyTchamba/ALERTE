"""One entry point: extract_file(path) -> ExtractionResult, for any file.

Order of events: human-corrected sidecar (if any) -> cache -> format handler -> flags -> cache.
A file is never skipped silently: when no text can be obtained the result carries a reason in `failed`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from alerte.knowledge.extract import ocr
from alerte.knowledge.extract.images import IMAGE_SUFFIXES, extract_image
from alerte.knowledge.extract.office import (extract_docx, extract_odf, extract_pptx, extract_text_family, extract_xls,
                                             extract_xlsx)
from alerte.knowledge.extract.pdf import extract_pdf
from alerte.knowledge.extract.result import EXTRACTOR_VERSION, ExtractionResult, PageResult

log = logging.getLogger(__name__)

TEXT_SUFFIXES = {".txt", ".md", ".html", ".htm", ".xhtml", ".csv", ".tsv", ".rtf", ".epub", ".json", ".xml", ".yaml", ".yml", ".log", ".rst"}
OFFICE_SUFFIXES = {".docx", ".docm", ".dotx", ".pptx", ".xlsx", ".xlsm", ".xls", ".odt", ".ods", ".odp"}
LEGACY_SUFFIXES = {".doc": "docx", ".ppt": "pptx", ".dot": "docx", ".pps": "pptx"}
SUPPORTED = {".pdf"} | IMAGE_SUFFIXES | TEXT_SUFFIXES | OFFICE_SUFFIXES | set(LEGACY_SUFFIXES)
SIDECAR_SUFFIXES = (".corrected.md", ".corrected.txt")


def is_sidecar(p: Path) -> bool:
    return p.name.lower().endswith(SIDECAR_SUFFIXES)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_for(path: Path) -> Path | None:
    for suf in SIDECAR_SUFFIXES:
        cand = path.with_name(path.name + suf)
        if cand.exists():
            return cand
    return None


def _cache_dir() -> Path:
    from alerte import config
    d = config.settings.index_dir / "extract_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _convert_legacy(path: Path, target: str) -> Path | None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    out = Path(tempfile.mkdtemp(prefix="alerte-conv-"))
    try:
        subprocess.run([soffice, "--headless", "--convert-to", target, "--outdir", str(out), str(path)],
                       capture_output=True, timeout=180, check=True)
    except Exception as e:
        log.warning("LibreOffice conversion failed for %s: %s", path.name, e)
        return None
    found = list(out.glob(f"*.{target}"))
    return found[0] if found else None


def _sniff(path: Path) -> str:
    """File type from its first bytes, for files with a missing or wrong extension."""
    try:
        head = path.read_bytes()[:16]
    except Exception:
        return ""
    if head.startswith(b"%PDF"):
        return ".pdf"
    if head.startswith(b"\x89PNG"):
        return ".png"
    if head[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if head[:4] in (b"II*\x00", b"MM\x00*"):
        return ".tiff"
    if head.startswith(b"PK"):
        try:
            import zipfile
            names = zipfile.ZipFile(path).namelist()
            if any(n.startswith("word/") for n in names):
                return ".docx"
            if any(n.startswith("ppt/") for n in names):
                return ".pptx"
            if any(n.startswith("xl/") for n in names):
                return ".xlsx"
        except Exception:
            return ""
    try:
        raw = path.read_bytes()[:4000]
        if b"\x00" in raw or sum(1 for b in raw if b < 9 or 13 < b < 32) > len(raw) * 0.02:
            return ""                       # binary data, not text
        raw.decode("utf-8")
        return ".txt"
    except Exception:
        return ""


def _dispatch(path: Path, language: str | None, thorough: bool, suffix: str) -> ExtractionResult:
    if suffix == ".pdf":
        return extract_pdf(path, language, thorough)
    if suffix in IMAGE_SUFFIXES:
        return extract_image(path, language, thorough)
    if suffix in (".docx", ".docm", ".dotx"):
        return extract_docx(path, language)
    if suffix == ".pptx":
        return extract_pptx(path, language)
    if suffix in (".xlsx", ".xlsm"):
        return extract_xlsx(path)
    if suffix == ".xls":
        return extract_xls(path)
    if suffix in (".odt", ".ods", ".odp"):
        return extract_odf(path)
    if suffix in LEGACY_SUFFIXES:
        conv = _convert_legacy(path, LEGACY_SUFFIXES[suffix])
        if conv is None:
            r = ExtractionResult(path=str(path))
            r.failed = (f"legacy {suffix} file: install LibreOffice (soffice) so it can be converted, "
                        f"or save the file as .{LEGACY_SUFFIXES[suffix]} / PDF and re-run")
            return r
        r = _dispatch(conv, language, thorough, "." + LEGACY_SUFFIXES[suffix])
        r.path = str(path)
        return r
    if suffix in TEXT_SUFFIXES:
        return extract_text_family(path)
    sniffed = _sniff(path)
    if sniffed and sniffed != suffix:
        r = _dispatch(path, language, thorough, sniffed)
        r.warnings.append(f"unknown extension '{suffix}', read as {sniffed}")
        return r
    r = ExtractionResult(path=str(path))
    r.failed = f"unsupported file type '{suffix or 'none'}': convert it to PDF, Word, an image or text"
    return r


def _read_sidecar(side: Path, path: Path, digest: str) -> ExtractionResult:
    text = side.read_text(encoding="utf-8-sig", errors="replace")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S).strip()
    res = ExtractionResult(path=str(path), sha256=digest, corrected=True)
    res.pages.append(PageResult(1, text, "human-corrected"))
    if not text:
        res.failed = f"the corrected file {side.name} is empty"
    return res


def extract_file(path: Path | str, language: str | None = None, use_cache: bool = True, thorough: bool | None = None) -> ExtractionResult:
    path = Path(path)
    digest = sha256(path)
    side = sidecar_for(path)
    if side is not None:
        res = _read_sidecar(side, path, digest)
        res.warnings.append(f"text taken from {side.name} (human-verified); the machine reading is ignored")
        return res
    if thorough is None:
        thorough = os.environ.get("ALERTE_OCR_THOROUGH", "0") == "1"
    key = f"{digest[:20]}-{(language or 'auto')}-{int(thorough)}-v{EXTRACTOR_VERSION}-{ocr.status().tesseract and 't' or 'n'}"
    cache = _cache_dir() / (key + ".json") if use_cache and os.environ.get("ALERTE_NO_OCR_CACHE") != "1" else None
    if cache and cache.exists():
        try:
            res = ExtractionResult.from_json(json.loads(cache.read_text(encoding="utf-8")))
            res.path, res.cached = str(path), True
            return res
        except Exception:
            pass
    suffix = path.suffix.lower()
    try:
        res = _dispatch(path, language, bool(thorough), suffix)
    except Exception as e:  # a bad file must never stop the whole ingestion
        log.exception("extraction crashed on %s", path)
        res = ExtractionResult(path=str(path))
        res.failed = f"extraction crashed: {e}"
    res.sha256 = digest
    res.path = str(path)
    if cache and not res.failed:
        try:
            cache.write_text(json.dumps(res.to_json(), ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    return res


def discover_files(*roots: Path) -> list[Path]:
    """Every file under the given folders (recursively), except hidden files, temp files and correction sidecars."""
    seen: dict[str, Path] = {}
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.name.startswith((".", "~$")) or is_sidecar(p):
                continue
            if p.name.lower() in ("thumbs.db", "desktop.ini", ".ds_store"):
                continue
            if any(part in ("__pycache__", ".git") for part in p.parts):
                continue
            seen[str(p.resolve())] = p
    return list(seen.values())
