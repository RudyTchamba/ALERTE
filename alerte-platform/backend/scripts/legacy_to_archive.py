#!/usr/bin/env python
"""Convertit l'index du prototype (`alerte/index/documents.json` + `chunks.jsonl`) en archives `alerte-kb-archive` 1.0.0.

Aucune ré-extraction : le texte déjà extrait est réutilisé tel quel (doc 07 §7.8). Les droits ne sont pas connus :
`redistribution = unknown` partout, `reliability` d'après `alerte/data/manifest.csv`. Les chemins absolus du prototype ne
sont jamais recopiés. Fonctionne sous Linux, Windows et macOS :

    python scripts/legacy_to_archive.py --out ./legacy-archives            # une archive par collection
    python scripts/legacy_to_archive.py --out ./legacy-all.zip --single     # une seule archive

Les archives s'importent ensuite par l'API (`POST /knowledge-bases/import`), ce qui teste aussi l'import.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.core.canonical_json import canonical_bytes  # noqa: E402
from app.knowledge import archive_format as af  # noqa: E402

REPO = BACKEND.parent.parent
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
COLLECTIONS = {
    "AE": ("AE", "Émirats arabes unis (prototype)", "national"),
    "CM": ("CM", "Cameroun (prototype)", "national"),
    "GL": ("GL", "Pratiques mondiales (prototype)", "global_practices"),
    "SCN": ("SCN", "Matériaux de scénario fictifs (prototype)", "scenario"),
    "ITU": ("ITU", "Références ITU (prototype)", "global_practices"),
}
RELIABILITY = {"official": "official", "summary": "summary", "unofficial": "unofficial", "not_found": "not_found",
               "fictional": "unofficial"}
VALIDITY = {"current": "in_force", "in_force": "in_force", "replaced": "replaced"}


def det_id(*parts: str) -> str:
    """Identifiant de 26 caractères (alphabet ULID) déterministe : relancer le script donne les mêmes identifiants."""
    n = int.from_bytes(hashlib.sha256("|".join(parts).encode("utf-8")).digest()[:17], "big") >> 6  # 130 bits
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 31])
        n >>= 5
    return "".join(reversed(out))


def read_inputs(index_dir: Path, manifest: Path | None):
    docs = json.loads((index_dir / "documents.json").read_text(encoding="utf-8"))
    chunks = [json.loads(line) for line in (index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reliability: dict[str, dict] = {}
    if manifest and manifest.is_file():
        with manifest.open(encoding="utf-8", newline="") as fh:
            reliability = {r["doc_id"]: r for r in csv.DictReader(fh)}
    review: dict[str, list[int]] = {}
    rep = index_dir / "extraction_report.json"
    if rep.is_file():
        data = json.loads(rep.read_text(encoding="utf-8"))
        by_name = {Path(d.get("file", "")).name: d.get("review_pages", []) for d in data.get("documents", [])}
        for d in docs:
            review[d["doc_id"]] = by_name.get(Path(d.get("file", "")).name, [])
    return docs, chunks, reliability, review


def build_archive(out: Path, kb_code: str, kb_name: str, kind: str, docs: list[dict], chunks_by_doc: dict[str, list[dict]],
                  reliability: dict[str, dict], review: dict[str, list[int]]) -> dict:
    kb_id = det_id("kb", kb_code)
    drecs, crecs, red = [], [], Counter()
    langs: Counter = Counter()
    for d in sorted(docs, key=lambda x: x["doc_id"]):
        did = d["doc_id"]
        ch = sorted(chunks_by_doc.get(did, []), key=lambda c: c["chunk_id"])
        man = reliability.get(did, {})
        rel = RELIABILITY.get(man.get("reliability") or d.get("reliability") or "", "unofficial")
        vid = det_id("ver", kb_code, did, "1")
        text_hash = hashlib.sha256("".join(c["text"] for c in ch).encode("utf-8")).hexdigest()
        pages = sorted({int(p) for p in review.get(did, [])})
        flagged = pages or any(c.get("needs_review") for c in ch)
        fictional = (man.get("reliability") or d.get("reliability")) == "fictional"
        drecs.append({
            "document_id": det_id("doc", kb_code, did), "code": did, "title": d["title"][:500], "doc_type": d.get("doc_type"),
            "doc_number": None, "doc_date": None, "jurisdiction": d.get("country") or None, "language": d.get("language"),
            "source_url": d.get("url") or None, "reliability": rel,
            "validity": VALIDITY.get(d.get("status", ""), "unknown"), "replaced_by_id": None, "license_spdx": None,
            "redistribution": "unknown", "evidence_default": "assumed" if fictional else "documented",
            "accessed_at": d.get("accessed") or None, "is_current": True,
            "version": {"id": vid, "version_no": 1, "blob_sha256": text_hash, "mime": None, "bytes": sum(len(c["text"]) for c in ch),
                        "original_name": Path(d.get("file", "")).name or None,
                        "extraction_method": (ch[0].get("extraction") if ch else None), "extraction_quality": None,
                        "pages_to_review": pages, "status": "needs_review" if flagged else "ready",
                        "note": "converti depuis l'index du prototype (texte déjà extrait ; originaux non inclus)",
                        "supersedes_id": None, "source_file": None,
                        "quality_report": {"legacy": True, "notes": d.get("notes"), "topics": d.get("topics", []),
                                           "institutions": d.get("institutions", []), "chunks": len(ch),
                                           "pages_to_review": pages, "warnings": ["pages sans numéro (index du prototype)"]}}})
        red["unknown"] += 1
        langs[d.get("language") or "und"] += 1
        for i, c in enumerate(ch):
            crecs.append({"id": det_id("chunk", kb_code, c["chunk_id"]), "document_version_id": vid, "ordinal": i,
                          "page_start": None, "page_end": None, "article": (c.get("article") or None), "section": None,
                          "language": c.get("language"), "text": c["text"],
                          "text_sha256": hashlib.sha256(c["text"].encode("utf-8")).hexdigest(), "char_start": None,
                          "char_end": None, "doc_title": d["title"][:500],
                          "evidence_tag": "assumed" if fictional else "documented", "topics": c.get("topics") or None})
    w = af.ArchiveWriter(out)
    kbj = {"id": kb_id, "code": kb_code, "name": kb_name, "description": "Importé depuis le prototype ALERTE (index du 2026-11-11).",
           "domain": "early_warning", "kind": kind, "languages": sorted(langs), "chunking_params": {"strategy": "legacy"},
           "embedder_fingerprint": None}
    w.add_bytes("data/kb.json", canonical_bytes(kbj), 1)
    w.add_bytes("data/documents.jsonl", af.jsonl_bytes(drecs), len(drecs))
    w.add_bytes("data/chunks.jsonl", af.jsonl_bytes(crecs), len(crecs))
    manifest = {
        "format": af.FORMAT, "format_version": af.FORMAT_VERSION,
        "kb": {"id": kb_id, "code": kb_code, "name": kb_name, "version": None, "languages": sorted(langs), "domain": "early_warning",
               "kind": kind},
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "exporter": {"name": "alerte-platform/legacy_to_archive", "version": "0.1.0"}, "mode": "processed_only",
        "embedding": {"included": False}, "chunking": {"strategy": "legacy"},
        "documents_summary": {"count": len(drecs), "licenses": {"unspecified": len(drecs)}, "redistribution": dict(red)},
        "provenance": {"tool": "scripts/legacy_to_archive.py", "source": "alerte/index/documents.json + chunks.jsonl"},
        "warnings": ["redistribution=unknown pour tous les documents : export ouvert vide tant que les droits ne sont pas qualifiés",
                     "chunks sans numéro de page ; aucun embedding (à calculer après import)"]}
    sha = w.finish(manifest)
    return {"file": str(out), "documents": len(drecs), "chunks": len(crecs), "manifest_sha256": sha}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path, help="dossier (une archive par collection) ou fichier .zip (avec --single)")
    ap.add_argument("--index-dir", type=Path, default=REPO / "alerte" / "index")
    ap.add_argument("--manifest", type=Path, default=REPO / "alerte" / "data" / "manifest.csv")
    ap.add_argument("--single", action="store_true", help="une seule archive pour toutes les collections")
    a = ap.parse_args(argv)
    docs, chunks, reliability, review = read_inputs(a.index_dir, a.manifest)
    by_doc: dict[str, list[dict]] = {}
    for c in chunks:
        by_doc.setdefault(c["doc_id"], []).append(c)
    results = []
    if a.single or a.out.suffix.lower() == ".zip":
        out = a.out if a.out.suffix.lower() == ".zip" else a.out / "alerte-kb-legacy.zip"
        out.parent.mkdir(parents=True, exist_ok=True)
        results.append(build_archive(out, "LEGACY", "Corpus du prototype ALERTE", "mixed", docs, by_doc, reliability, review))
    else:
        a.out.mkdir(parents=True, exist_ok=True)
        groups: dict[str, list[dict]] = {}
        for d in docs:
            groups.setdefault(d.get("collection") or "OTHER", []).append(d)
        for coll, items in sorted(groups.items()):
            code, name, kind = COLLECTIONS.get(coll, (coll, f"Collection {coll} (prototype)", "mixed"))
            results.append(build_archive(a.out / f"alerte-kb-{code}.zip", code, name, kind, items, by_doc, reliability, review))
    for r in results:
        print(f"{Path(r['file']).name}: {r['documents']} documents, {r['chunks']} chunks, manifest {r['manifest_sha256'][:12]}")
    print(f"total : {sum(r['documents'] for r in results)} documents, {sum(r['chunks'] for r in results)} chunks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
