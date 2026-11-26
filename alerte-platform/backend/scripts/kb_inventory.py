#!/usr/bin/env python3
"""Inventaire exhaustif des PDF d'un dossier source (LECTURE SEULE : rien n'est écrit dans le dossier source).

    python scripts/kb_inventory.py --source ../../alerte --out ../knowledge_bases/inventory

Pour chaque PDF : chemin relatif, taille, SHA-256, nombre de pages, pages sans couche texte exploitable (candidates à l'OCR),
métadonnées PDF brutes, doublons exacts (SHA-256) et quasi-doublons (recouvrement de 5-grammes). Aucune métadonnée n'est inventée :
le titre, le pays, le type, la langue… viennent du registre de curation (`knowledge_bases/curation/documents.curation.json`,
établi par lecture de la première page) quand il existe, sinon restent `null` (« à qualifier »).
N'utilise AUCUN résultat d'un ancien traitement (ni chunks, ni index, ni manifeste du prototype).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path

MIN_PAGE_CHARS = 80  # même seuil que le pipeline (app/knowledge/extract.py : MIN_PAGE_CHARS)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def pdfinfo(p: Path) -> dict:
    out = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=60)
    info = {}
    for ln in out.stdout.splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            info[k.strip()] = v.strip()
    return {"pages": int(info.get("Pages", 0) or 0), "pdf_title": info.get("Title") or None, "producer": info.get("Producer") or None,
            "encrypted": info.get("Encrypted", "no").startswith("yes"), "ok": out.returncode == 0}


def page_texts(p: Path) -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, timeout=300)
    return out.stdout.decode("utf-8", "ignore").split("\f")[:-1] if out.returncode == 0 else []


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", s)).strip()


def shingles(text: str, n: int = 5) -> set[str]:
    w = norm(text)[:6000].split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True, help="dossier racine contenant les PDF (ex. ../../alerte)")
    ap.add_argument("--curation", type=Path, default=Path(__file__).resolve().parents[2] / "knowledge_bases" / "curation" / "documents.curation.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    root = a.source.resolve()
    repo = root.parent
    cur = {c["original_path"]: c for c in json.loads(a.curation.read_text(encoding="utf-8"))} if a.curation.exists() else {}
    pdfs = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
    rows, sh = [], {}
    for p in pdfs:
        rel = str(p.relative_to(repo))
        info = pdfinfo(p)
        pages = page_texts(p)
        poor = [i + 1 for i, t in enumerate(pages) if len(t.strip()) < MIN_PAGE_CHARS]
        c = cur.get(rel, {})
        row = {
            "original_filename": p.name, "original_path": rel, "file_size": p.stat().st_size, "sha256": sha256_file(p),
            "page_count": info["pages"], "pages_without_text_layer": len(poor), "pages_without_text_layer_list": poor[:200],
            "pdf_title_metadata": info["pdf_title"], "encrypted": info["encrypted"], "readable": info["ok"] and bool(pages),
            "code": c.get("code"), "collection": c.get("collection"), "title": c.get("title"), "doc_type": c.get("doc_type"),
            "reference_number": c.get("doc_number"), "publication_date": c.get("doc_date"), "language": c.get("language"),
            "domains": c.get("domains"), "source_url": c.get("source_url"), "reliability": c.get("reliability", "unknown"),
            "validity": c.get("validity", "unknown"), "redistribution_status": c.get("redistribution", "unknown"),
            "curation_status": "curated_from_first_page" if c else "to_qualify",
            "extraction_status": "pending" if info["ok"] and pages else "failed",
        }
        rows.append(row)
        sh[rel] = shingles(" ".join(pages[:3]))
    by_sha: dict[str, list[str]] = {}
    for r in rows:
        by_sha.setdefault(r["sha256"], []).append(r["original_path"])
    dups_exact = [v for v in by_sha.values() if len(v) > 1]
    near = []
    keys = list(sh)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            A, B = sh[keys[i]], sh[keys[j]]
            if A and B and len(A & B) / min(len(A), len(B)) > 0.8 and by_sha.get(next(r["sha256"] for r in rows if r["original_path"] == keys[i])) != by_sha.get(next(r["sha256"] for r in rows if r["original_path"] == keys[j])):
                near.append([keys[i], keys[j]])
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "pdf_inventory.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {"source": str(root.relative_to(repo)), "pdf_found": len(rows), "total_bytes": sum(r["file_size"] for r in rows),
               "total_pages": sum(r["page_count"] for r in rows), "pages_without_text_layer": sum(r["pages_without_text_layer"] for r in rows),
               "exact_duplicates": dups_exact, "near_duplicates": near, "unreadable": [r["original_path"] for r in rows if not r["readable"]],
               "by_collection": {k: sum(1 for r in rows if r["collection"] == k) for k in sorted({r["collection"] or "to_qualify" for r in rows})},
               "not_curated": [r["original_path"] for r in rows if r["curation_status"] == "to_qualify"]}
    (a.out / "inventory_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
