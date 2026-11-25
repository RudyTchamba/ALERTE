#!/usr/bin/env python3
"""Construit les bases de connaissances à partir des PDF originaux, en appelant les MÊMES endpoints que l'interface graphique
(création de base, téléversement, extraction/OCR/découpage par le job `kb_ingest`, publication, embeddings).

Ce script n'est PAS un pipeline parallèle : il ne fait que piloter l'API HTTP du backend d'ALERTE. Il ne lit que les PDF (jamais
de chunks, d'index, d'archives ni de manifeste d'un ancien traitement) et les métadonnées du registre de curation.

    # 1. backend isolé (OCR fra+eng+ara ; PAS de serveur d'embeddings pour l'ingestion)
    ALERTE_DATA_DIR=./data-kb-build ALERTE_TESSDATA_DIR=./data-kb-build/tessdata ALERTE_OCR_LANGS=fra+eng+ara \
      python -m uvicorn app.main:app_factory --factory --port 8020
    # 2. espace + bases + import + publication
    python scripts/kb_build.py --api http://localhost:8020 --create-workspace "ALERTE — Corpus" --stage setup,ingest,publish
    # 3. embeddings (redémarrer le backend avec ALERTE_EMBED_BASE_URL/ALERTE_EMBED_MODEL), reprise possible
    python scripts/kb_build.py --api http://localhost:8020 --token <jeton> --stage embed --collections CM

Étapes : setup · ingest · publish · embed · status. Idempotent : un document déjà présent (même code) est ignoré.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CURATION = HERE.parents[1] / "knowledge_bases" / "curation" / "documents.curation.json"

COLLECTIONS = {
    "CM": {"name": "Cameroun", "kind": "national", "country": ("Cameroun", "CM", ["fr", "en"]), "domain": "civil_protection", "languages": ["fr", "en"]},
    "AE": {"name": "Émirats arabes unis", "kind": "national", "country": ("Émirats arabes unis", "AE", ["ar", "en"]), "domain": "ai_governance", "languages": ["en", "ar"]},
    "GL": {"name": "Références globales et internationales", "kind": "global_practices", "country": None, "domain": "international_commitments", "languages": ["en", "fr"]},
    "ITU": {"name": "Références et standards ITU", "kind": "mixed", "country": None, "domain": "ai_governance", "languages": ["en"]},
}
JURISDICTION = {"GL-01": "EU", "GL-02": "EU", "GL-03": "EU", "GL-04": "PH", "GL-05": "US", "GL-06": "US", "GL-07": "INT", "GL-14": "AU",
                "GL-15": "AU", "GL-17": "INT", "GL-18": "US"}


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.c = httpx.Client(base_url=base.rstrip("/") + "/api/v1", timeout=600)
        self.h = {"Authorization": f"Bearer {token}"} if token else {}

    def call(self, method: str, path: str, ok=(200, 201, 202), **kw):  # noqa: ANN001, ANN201
        r = self.c.request(method, path, headers=kw.pop("headers", self.h), **kw)
        if r.status_code not in ok:
            raise RuntimeError(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
        return r.json() if r.content else None

    def job(self, job_id: str, *, label: str = "", poll: float = 2.0, timeout: float = 86400) -> dict:
        t0, last = time.time(), None
        while time.time() - t0 < timeout:
            j = self.call("GET", f"/jobs/{job_id}")
            prog = (j.get("progress"), j.get("message"))
            if prog != last and label:
                print(f"    … {label} {j.get('progress')} {j.get('message') or ''}", flush=True)
                last = prog
            if j["status"] in ("done", "failed", "interrupted"):
                return j
            time.sleep(poll)
        raise TimeoutError(job_id)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8020")
    ap.add_argument("--token")
    ap.add_argument("--create-workspace", metavar="NOM")
    ap.add_argument("--stage", default="setup,ingest,publish")
    ap.add_argument("--collections", default="CM,AE,GL,ITU")
    ap.add_argument("--only", help="codes de documents séparés par des virgules (ex. CM-01,CM-07)")
    a = ap.parse_args()
    stages = set(a.stage.split(","))
    cols = [c for c in a.collections.split(",") if c in COLLECTIONS]
    api = Api(a.api, a.token)
    if a.create_workspace:
        ws = api.call("POST", "/workspaces", json={"name": a.create_workspace}, headers={})
        api.h = {"Authorization": f"Bearer {ws['owner_token']}"}
        print(f"Espace créé. JETON PROPRIÉTAIRE (affiché une seule fois, à conserver) : {ws['owner_token']}")
    elif not a.token:
        sys.exit("--token ou --create-workspace requis")
    cur = {c["code"]: c for c in json.loads(CURATION.read_text(encoding="utf-8"))}
    countries = {c["iso2"]: c["id"] for c in api.call("GET", "/countries") if c.get("iso2")}
    kbs = {k["code"]: k["id"] for k in api.call("GET", "/knowledge-bases")}

    if "setup" in stages:
        for col in cols:
            spec = COLLECTIONS[col]
            cid = None
            if spec["country"]:
                name, iso, langs = spec["country"]
                if iso not in countries:
                    countries[iso] = api.call("POST", "/countries", json={"name": name, "iso2": iso, "languages": langs})["id"]
                cid = countries[iso]
            if col not in kbs:
                kbs[col] = api.call("POST", "/knowledge-bases", json={"code": col, "name": spec["name"], "kind": spec["kind"],
                                    "country_id": cid, "domain": spec["domain"], "languages": spec["languages"],
                                    "description": "Construite à partir des PDF originaux (voir docs/knowledge-base/)."})["id"]
            print(f"[setup] base {col} : {kbs[col]}")

    if "ingest" in stages:
        for col in cols:
            have = {d["code"] for d in api.call("GET", f"/knowledge-bases/{kbs[col]}/documents", params={"limit": 200})["items"]}
            for code, c in cur.items():
                if c["collection"] != col or code in have or (a.only and code not in a.only.split(",")):
                    continue
                path = REPO / c["original_path"]
                meta = {"code": code, "title": c["title"], "doc_type": c["doc_type"], "language": c["language"],
                        "jurisdiction": JURISDICTION.get(code, col if col in ("CM", "AE") else "INT"),
                        "reliability": c["reliability"], "validity": c["validity"], "redistribution": c["redistribution"],
                        "doc_number": c["doc_number"], "license_spdx": c["license_spdx"], "source_url": c["source_url"]}
                if c.get("doc_date") and len(c["doc_date"]) == 10:
                    meta["doc_date"] = c["doc_date"]
                meta = {k: v for k, v in meta.items() if v}
                t0 = time.time()
                with path.open("rb") as f:
                    r = api.call("POST", f"/knowledge-bases/{kbs[col]}/documents", data=meta, files={"file": (path.name, f, "application/pdf")})
                j = api.job(r["job"]["id"])
                dt = time.time() - t0
                print(f"[ingest] {code:12} {j['status']:8} {dt:6.0f}s  {json.dumps(j.get('result') or j.get('error'), ensure_ascii=False)[:230]}", flush=True)

    if "publish" in stages:
        for col in cols:
            v = api.call("POST", f"/knowledge-bases/{kbs[col]}/publish", json={"note": "Construction à partir des PDF originaux"})
            print(f"[publish] {col} : version {v['version_no']} ({v['documents']} documents)")

    if "embed" in stages:
        for col in cols:
            r = api.call("POST", f"/knowledge-bases/{kbs[col]}/embed", json={})
            print(f"[embed] {col} : job {r['job']['id']} (reprise possible : relancer cette commande)")
            j = api.job(r["job"]["id"], label=f"embed {col}", poll=30)
            print(f"[embed] {col} : {j['status']} {json.dumps(j.get('result') or j.get('error'), ensure_ascii=False)[:200]}")

    if "status" in stages:
        for col in cols:
            k = api.call("GET", f"/knowledge-bases/{kbs[col]}")
            print(f"[status] {col}: {json.dumps(k.get('overview'), ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
