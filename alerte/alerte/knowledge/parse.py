"""Turn a file into plain text. This is a thin wrapper over alerte.knowledge.extract, which handles digital and scanned PDFs
(with OCR), tables, pictures that contain text, images, Word, PowerPoint, Excel, OpenDocument, RTF, HTML, CSV and text."""

from __future__ import annotations

import logging
from pathlib import Path

from alerte.knowledge.extract import SUPPORTED, extract_file  # noqa: F401  (SUPPORTED re-exported)
from alerte.textutil import normalize_ws

log = logging.getLogger(__name__)


def parse_file(path: Path, language: str | None = None) -> str:
    """Text of the file, or "" with a logged reason. Use extract_file for the per-page quality report."""
    res = extract_file(path, language)
    if res.failed:
        log.warning("%s: %s", Path(path).name, res.failed)
    return normalize_ws(res.text)
