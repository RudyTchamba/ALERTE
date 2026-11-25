#!/usr/bin/env python3
"""Exporte les bases construites vers `alerte-platform/knowledge_bases/` (formats lisibles : JSON / JSONL / YAML / Markdown).

Deux sorties, séparées par la politique de droits (docs/knowledge-base/publication-policy.md) :

* `knowledge_bases/<COL>/` (SUIVI par Git, publiable) : métadonnées, provenance, statuts de droits, statistiques d'extraction,
  identifiants stables et empreintes de TOUS les documents ; le TEXTE (Knowledge Records, chunks) uniquement pour les documents
  dont la redistribution est `allowed`. Pour les autres : `content: null` + `content_withheld_reason`.
* `knowledge_bases/_local/<COL>/` (IGNORÉ par Git) : export complet, texte compris, pour l'usage interne et les évaluations.

Aucun texte n'est lu ailleurs que dans l'API du backend (donc produit par le pipeline d'ALERTE à partir des PDF).
Identifiants stables : dérivés du SHA-256 du PDF, de l'ordinal / de l'article et de l'empreinte du texte (pas d'ULID aléatoire).

    python scripts/kb_export.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
CUR = HERE.parents[1] / "knowledge_bases" / "curation"


def h(*parts: str, n: int = 20) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:n]


def norm(s: str) -> str:
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[’'`´]", "'", s)).strip()


def anorm(s: str | None) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", norm(s or ""))


def jl(path: Path, rows) -> int:  # noqa: ANN001
    path.parent.mkdir(parents=True, exist_ok=True)
    k = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
            k += 1
    return k


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8020")
    ap.add_argument("--token", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--collections", default="CM,AE,GL,ITU")
    a = ap.parse_args()
    c = httpx.Client(base_url=a.api.rstrip("/") + "/api/v1", headers={"Authorization": f"Bearer {a.token}"}, timeout=600)

    def get(path, **params):  # noqa: ANN001, ANN202
        r = c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    cur = {x["code"]: x for x in json.loads((CUR / "documents.curation.json").read_text(encoding="utf-8"))}
    expected = [json.loads(x) for x in (CUR / "expected_documents.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    kbs = {k["code"]: k for k in get("/knowledge-bases") if k["code"] in a.collections.split(",")}
    publication = {"included": [], "withheld": [], "pending_verification": []}
    totals = defaultdict(int)
    ALLC: list[dict] = []
    ALLR: list[dict] = []
    ALLD: list[dict] = []
    for col, kb in sorted(kbs.items()):
        docs, cursor = [], None
        while True:
            page = get(f"/knowledge-bases/{kb['id']}/documents", limit=200, **({"cursor": cursor} if cursor else {}))
            docs += page["items"]
            cursor = page.get("next_cursor")
            if not cursor:
                break
        documents = []
        pub_records, pub_chunks, loc_records, loc_chunks = [], [], [], []
        for d in sorted(docs, key=lambda x: x["code"]):
            v = d.get("version") or {}
            vno = v.get("version_no", 1)
            full = get(f"/documents/{d['id']}/versions/{vno}/preview", page=1, limit=1)
            rep = (full.get("version") or {}).get("quality_report") or {}
            items, cur_ = [], -1
            while True:
                pg = get(f"/documents/{d['id']}/versions/{vno}/chunks", limit=200, cursor=cur_)
                items += pg["items"]
                cur_ = pg.get("next_cursor")
                if cur_ is None:
                    break
            sha = v.get("blob_sha256") or ""
            allowed = d.get("redistribution") == "allowed"
            doc_stable = "doc_" + h(sha, d["code"], n=16)
            cinfo = cur.get(d["code"], {})
            documents.append({
                "document_id": doc_stable, "code": d["code"], "collection": col, "title": d["title"],
                "original_filename": v.get("original_name"), "original_path": cinfo.get("original_path"), "sha256": sha,
                "file_size": v.get("bytes"), "page_count": full.get("total_pages"), "document_type": d.get("doc_type"),
                "reference_number": d.get("doc_number"), "publication_date": d.get("doc_date"), "language": d.get("language"),
                "jurisdiction": d.get("jurisdiction"), "domains": cinfo.get("domains"), "institution_codes": cinfo.get("institution_codes"),
                "source_url": d.get("source_url"), "reliability": d.get("reliability"), "validity": d.get("validity"),
                "redistribution_status": d.get("redistribution"), "license_spdx": d.get("license_spdx"),
                "license_evidence": cinfo.get("license_evidence"), "curation_notes": cinfo.get("notes"),
                "extraction": {"method": v.get("extraction_method"), "quality": v.get("extraction_quality"), "status": v.get("status"),
                               "pages_to_review": v.get("pages_to_review"), "chunks": len(items),
                               "warnings": rep.get("warnings"), "ocr_pages": rep.get("ocr_pages")},
                "extraction_status": "ready" if v.get("status") in ("ready", "ok") and not v.get("pages_to_review") else
                                     ("needs_review" if v.get("pages_to_review") else v.get("status") or "unknown"),
            })
            bucket = "included" if allowed else ("withheld" if d.get("redistribution") == "restricted" else "pending_verification")
            publication[bucket].append({"code": d["code"], "collection": col, "redistribution": d.get("redistribution"),
                                        "evidence": cinfo.get("license_evidence")})
            # ---- chunks + Knowledge Records (article-level)
            by_art: dict[str, list[dict]] = defaultdict(list)
            for it in items:
                ck = {"chunk_id": "ck_" + h(sha, str(it["ordinal"]), it["text_sha256"]), "document_id": doc_stable, "document_code": d["code"],
                      "ordinal": it["ordinal"], "page_start": it.get("page_start"), "page_end": it.get("page_end"), "article": it.get("article"),
                      "section": it.get("section"), "language": it.get("language"), "jurisdiction": d.get("jurisdiction"),
                      "doc_type": d.get("doc_type"), "reliability": d.get("reliability"), "validity": d.get("validity"),
                      "evidence_tag": it.get("evidence_tag"), "text_sha256": it["text_sha256"], "app_chunk_id": it["id"],
                      "char_count": len(it["text"])}
                if it.get("article"):
                    by_art[it["article"]].append({**ck, "_text": it["text"]})
                loc_chunks.append({**ck, "text": it["text"]})
                pub_chunks.append({**ck, "text": it["text"] if allowed else None,
                                   **({} if allowed else {"content_withheld_reason": f"redistribution={d.get('redistribution')}"})})
            for art, cks in by_art.items():
                content = "\n\n".join(x["_text"] for x in cks)
                rid = "kr_" + h(sha, art, *[x["text_sha256"] for x in cks])
                rec = {"record_id": rid, "document_id": doc_stable, "document_code": d["code"], "collection": col, "country": cinfo.get("collection") if col in ("CM", "AE") else None,
                       "jurisdiction": d.get("jurisdiction"), "institution_codes": cinfo.get("institution_codes"), "domain": cinfo.get("domains"),
                       "record_type": "article", "title": f"{d['code']} — {art}", "language": cks[0]["language"], "article_number": art,
                       "section": cks[0].get("section"), "page_start": min((x["page_start"] for x in cks if x["page_start"]), default=None),
                       "page_end": max((x["page_end"] for x in cks if x["page_end"]), default=None), "source_url": d.get("source_url"),
                       "source_reference": f"{d['title']} — {art}", "reliability": d.get("reliability"), "validity": d.get("validity"),
                       "extraction_method": v.get("extraction_method"), "review_status": "needs_review" if v.get("pages_to_review") else "unreviewed",
                       "source_hash": h(*[x["text_sha256"] for x in cks], n=32), "chunk_ids": [x["chunk_id"] for x in cks]}
                loc_records.append({**rec, "content": content})
                pub_records.append({**rec, "content": content if allowed else None,
                                    **({} if allowed else {"content_withheld_reason": f"redistribution={d.get('redistribution')}"})})
            totals["documents"] += 1
            totals["chunks"] += len(items)
            totals["pages"] += full.get("total_pages") or 0
        for base, recs, chks in ((a.out / col, pub_records, pub_chunks), (a.out / "_local" / col, loc_records, loc_chunks)):
            base.mkdir(parents=True, exist_ok=True)
            jl(base / "documents.jsonl", documents)
            jl(base / "records" / "knowledge_records.jsonl", recs)
            jl(base / "chunks" / "chunks.jsonl", chks)
        ALLC.extend(loc_chunks)
        ALLR.extend(loc_records)
        ALLD.extend(documents)
        exp = [e for e in expected if e["collection"] == col]
        jl(a.out / col / "expected_documents.jsonl", exp)
        ov = kb.get("overview") or {}
        manifest = {"collection": col, "name": kb["name"], "kind": kb["kind"], "languages": kb["languages"],
                    "documents": len(documents), "knowledge_records": len(pub_records), "chunks": len(pub_chunks),
                    "published_version_no": ov.get("published_version_no"), "embedded_chunks": ov.get("embedded_chunks"),
                    "embedder_key": ov.get("embedder_key"), "chunks_with_text_published": sum(1 for x in pub_chunks if x["text"]),
                    "records_with_text_published": sum(1 for x in pub_records if x["content"]),
                    "content_policy": "texte publié uniquement pour redistribution=allowed ; voir docs/knowledge-base/publication-policy.md"}
        (a.out / col / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        desc = {"CM": "17 PDF : lois, décrets, plan de contingence, rapports (français/anglais)",
                "AE": "9 PDF : décrets-lois fédéraux, charte et stratégie IA, spécification cell broadcast (anglais)",
                "GL": "16 PDF : textes UE, États-Unis, Philippines, ONU/ITU/OMS, Union africaine, NIST",
                "ITU": "2 PDF : Recommandation Y.3172 et rapport AI Ready"}.get(col, "")
        full_idx = bool(manifest["embedded_chunks"]) and manifest["embedded_chunks"] == manifest["chunks"]
        (a.out / col / "README.md").write_text(
            f"# {col} — {kb['name']}\n\n{desc}. Construite par le pipeline d'ALERTE à partir des PDF originaux (lecture seule).\n\n"
            f"* **{manifest['documents']} documents**, **{manifest['knowledge_records']} Knowledge Records**, **{manifest['chunks']} chunks** ; "
            f"chunks avec texte publié : **{manifest['chunks_with_text_published']}** (le texte n'est publié que pour `redistribution_status = allowed` : "
            "`docs/knowledge-base/publication-policy.md`).\n"
            f"* Vecteurs calculés : **{manifest['embedded_chunks'] or 0} / {manifest['chunks']}** (modèle : {manifest['embedder_key'] or 'aucun'}) — recherche "
            f"**{'hybride' if full_idx else 'lexicale (dégradée) tant que l’index vectoriel est incomplet'}**.\n"
            "* Fichiers : `manifest.json`, `documents.jsonl`, `expected_documents.jsonl`, `records/knowledge_records.jsonl`, `chunks/chunks.jsonl`"
            f"{', `graph/` (institutions, mandats, relations et sources)' if col == 'CM' else ''}.\n"
            f"* Texte complet pour usage interne : `knowledge_bases/_local/{col}/` (non suivi par Git).\n", encoding="utf-8")
        print(f"[export] {col}: {len(documents)} documents, {len(pub_records)} Knowledge Records, {len(pub_chunks)} chunks "
              f"(texte publié : {manifest['chunks_with_text_published']} chunks)")
    for gpath in sorted(CUR.glob("mandates.*.json")):
        col = gpath.stem.split(".")[1]
        if col not in kbs:
            continue
        g = json.loads(gpath.read_text(encoding="utf-8"))
        by_doc_rec = {(r["document_code"], anorm(r["article_number"])): r["record_id"] for r in ALLR}
        rights = {d["code"]: d["redistribution_status"] for d in ALLD}
        mand_pub, mand_loc, rel = [], [], []
        for md in g["mandates"]:
            srcs_loc, srcs_pub = [], []
            for sdef in md["sources"]:
                hit = next((ck for ck in ALLC if ck["document_code"] == sdef["document"] and norm(sdef["quote"]) in norm(ck["text"])
                            and (not sdef["article"] or anorm(ck.get("article")) == anorm(sdef["article"]))), None)
                if hit is None and sdef["article"]:  # étiquette d'article non reconnue par l'OCR : on retrouve le passage par sa phrase
                    hit = next((ck for ck in ALLC if ck["document_code"] == sdef["document"] and norm(sdef["quote"]) in norm(ck["text"])), None)
                res = {"document": sdef["document"], "article": sdef["article"], "role": sdef["role"],
                       "chunk_id": hit["chunk_id"] if hit else None, "page_start": hit["page_start"] if hit else None,
                       "record_id": by_doc_rec.get((sdef["document"], anorm(sdef["article"] or ""))) if sdef["article"] else None,
                       "resolved": bool(hit)}
                srcs_loc.append({**res, "quote": sdef["quote"]})
                srcs_pub.append({**res, **({"quote": sdef["quote"]} if rights.get(sdef["document"]) == "allowed" else {"quote_withheld_reason": "redistribution != allowed"})})
                rel.append({"from": f"mandate:{md['ref']}", "type": "grounded_in" if sdef["role"] == "grounds" else "context_from",
                            "to": hit["chunk_id"] if hit else None, "document": sdef["document"], "resolved": bool(hit)})
            base = {k: v for k, v in md.items() if k != "sources"}
            mand_loc.append({**base, "sources": srcs_loc})
            mand_pub.append({**base, "sources": srcs_pub})
            rel.append({"from": f"institution:{md['institution']}", "type": "holds_" + md["kind"], "to": f"mandate:{md['ref']}", "evidence_tag": md["evidence_tag"]})
        for gb, mm in ((a.out / col, mand_pub), (a.out / "_local" / col, mand_loc)):
            (gb / "graph").mkdir(parents=True, exist_ok=True)
            (gb / "graph" / "institutions.json").write_text(json.dumps({"institutions": g["institutions"], "registry_review": g["registry_review"], "note": g["note"]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            jl(gb / "graph" / "mandates.jsonl", mm)
            jl(gb / "graph" / "relations.jsonl", rel)
        unresolved = [m["ref"] for m in mand_loc for sx in m["sources"] if not sx["resolved"]]
        print(f"[graph] {col}: {len(mand_loc)} mandats, sources non résolues dans le texte extrait : {unresolved or 'aucune'}")

    (a.out / "publication_manifest.json").write_text(json.dumps({
        "policy": "allowed → texte publié ; restricted/unknown → métadonnées seulement",
        "included_with_text": [x for x in publication["included"]], "withheld_restricted": [x for x in publication["withheld"]],
        "pending_verification_unknown_rights": [x for x in publication["pending_verification"]], "totals": dict(totals)},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
