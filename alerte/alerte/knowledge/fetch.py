"""Download the official texts listed in the manifest (rows with a URL and a file path).

Run on your own computer: `python -m alerte fetch`. Files that already exist are
skipped. Some government sites block scripts; download those by hand into the
path shown and re-run `python -m alerte ingest`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alerte import config
from alerte.knowledge.ingest import read_manifest
from alerte.net import download

log = logging.getLogger(__name__)


def fetch_all(only: list[str] | None = None, dry_run: bool = False) -> list[tuple[str, str]]:
    results = []
    for doc in read_manifest():
        if only and doc.doc_id not in only:
            continue
        if not doc.url or not doc.file or doc.reliability.value != "official":
            continue
        dest = config.settings.docs_dir / doc.file
        if dest.exists():
            results.append((doc.doc_id, "already present"))
            continue
        if dry_run:
            results.append((doc.doc_id, f"would download {doc.url} -> {dest}"))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(dest) + ".part")
        try:
            n = download(doc.url, str(tmp))
            head = tmp.read_bytes()[:5]
            if dest.suffix.lower() == ".pdf" and head != b"%PDF-":
                tmp.unlink(missing_ok=True)
                results.append((doc.doc_id, f"FAILED: the link did not return a PDF; download by hand from {doc.url}"))
                continue
            tmp.replace(dest)
            results.append((doc.doc_id, f"downloaded {n // 1024} KB"))
        except Exception as e:
            tmp.unlink(missing_ok=True)
            results.append((doc.doc_id, f"FAILED ({e}); download by hand from {doc.url} into {dest}"))
    return results
