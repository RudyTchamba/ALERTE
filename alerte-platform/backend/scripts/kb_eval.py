#!/usr/bin/env python3
"""Évalue la recherche documentaire (Recall@5, MRR, FR→EN / EN→FR) sur `knowledge_bases/evaluation/questions.jsonl`.

Les chunks « gold » ne sont jamais saisis à la main : ils sont RÉSOLUS dans le corpus construit (chunks du document attendu qui
contiennent textuellement `evidence_quote`, et, si indiqué, l'article attendu). Une question dont la preuve n'est pas retrouvée
est marquée `not_evaluable` (problème de couverture ou d'extraction du corpus), jamais comptée comme réussite ni comme échec.

    python scripts/kb_eval.py --api http://localhost:8020 --token <jeton> --out ../knowledge_bases/evaluation --label lexical
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import httpx


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[’'`´]", "'", s)).strip()


def anorm(s: str | None) -> str:
    """Article normalisé : « ARTICLE9 », « Article 9 », « ARTICLE 9. » désignent le même article."""
    return re.sub(r"[^a-z0-9]", "", norm(s or ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8020")
    ap.add_argument("--token", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--label", default="run", help="étiquette du mode (ex. lexical, hybrid)")
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    c = httpx.Client(base_url=a.api.rstrip("/") + "/api/v1", headers={"Authorization": f"Bearer {a.token}"}, timeout=600)
    questions = [json.loads(x) for x in (a.out / "questions.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    kbs = {k["code"]: k for k in c.get("/knowledge-bases").json()}
    # chunks par (collection, document)
    cache: dict[tuple[str, str], list[dict]] = {}

    def chunks(col: str, code: str) -> list[dict]:
        if (col, code) in cache:
            return cache[(col, code)]
        docs = c.get(f"/knowledge-bases/{kbs[col]['id']}/documents", params={"limit": 200}).json()["items"]
        d = next((x for x in docs if x["code"] == code), None)
        out: list[dict] = []
        if d:
            vno = (d.get("version") or {}).get("version_no", 1)
            cur = -1
            while True:
                pg = c.get(f"/documents/{d['id']}/versions/{vno}/chunks", params={"limit": 200, "cursor": cur}).json()
                out += pg["items"]
                cur = pg.get("next_cursor")
                if cur is None:
                    break
        cache[(col, code)] = out
        return out

    rows, degraded_seen, embedded = [], False, {}
    for col in {q["collection"] for q in questions}:
        if col in kbs:
            ov = (c.get(f"/knowledge-bases/{kbs[col]['id']}").json().get("overview") or {})
            embedded[col] = {"chunks": ov.get("chunks"), "embedded_chunks": ov.get("embedded_chunks"), "embedder_key": ov.get("embedder_key")}
    for q in questions:
        col, doc = q["collection"], q["expected_document"]
        if col not in kbs:
            rows.append({**q, "status": "not_evaluable", "reason": "base absente"})
            continue
        cands = chunks(col, doc)
        gold = [ch["id"] for ch in cands if norm(q["evidence_quote"]) in norm(ch["text"])
                and (not q.get("expected_article") or anorm(ch.get("article")) == anorm(q["expected_article"]))]
        resolution = "quote+article"
        if not gold and q.get("expected_article"):
            # numéro d'article mal lu par l'OCR (« ARTICLE §3 ») : on évalue la récupération du PASSAGE (phrase retrouvée), signalé
            gold = [ch["id"] for ch in cands if norm(q["evidence_quote"]) in norm(ch["text"])]
            resolution = "quote_only (étiquette d'article non reconnue)"
        if not gold:
            rows.append({**q, "status": "not_evaluable", "reason": "preuve introuvable dans le texte extrait (couverture ou extraction)"})
            continue
        r = c.post(f"/knowledge-bases/{kbs[col]['id']}/search", json={"query": q["question"], "k": a.k}).json()
        degraded_seen = degraded_seen or bool(r.get("degraded"))
        ids = [h["chunk_id"] for h in r["hits"]]
        rank = next((i + 1 for i, x in enumerate(ids) if x in gold), None)
        doc_rank = next((i + 1 for i, h in enumerate(r["hits"]) if h["doc_code"] == doc), None)
        dlang = next((ch.get("language") for ch in chunks(col, doc) if ch["id"] in gold), None)
        rows.append({**q, "status": "evaluated", "gold_resolution": resolution, "gold_chunks": len(gold), "rank": rank, "document_rank": doc_rank, "doc_language": dlang,
                     "cross_language": bool(dlang and dlang[:2] != q["question_language"]), "hit_docs": [h["doc_code"] for h in r["hits"]]})
    ev = [r for r in rows if r["status"] == "evaluated"]

    def metrics(sel: list[dict]) -> dict:
        n = len(sel)
        return {"n": n, "recall_at_5": round(sum(1 for r in sel if r["rank"]) / n, 3) if n else None,
                "mrr": round(sum(1 / r["rank"] for r in sel if r["rank"]) / n, 3) if n else None,
                "document_recall_at_5": round(sum(1 for r in sel if r["document_rank"]) / n, 3) if n else None}
    summary = {"label": a.label, "k": a.k, "questions_total": len(questions), "evaluated": len(ev),
               "not_evaluable": len(rows) - len(ev), "search_degraded_lexical_only": degraded_seen, "embeddings": embedded,
               "overall": metrics(ev), "same_language": metrics([r for r in ev if not r["cross_language"]]),
               "cross_language": metrics([r for r in ev if r["cross_language"]]),
               "by_collection": {col: metrics([r for r in ev if r["collection"] == col]) for col in sorted({r["collection"] for r in ev})},
               "target_T1": "Recall@5 >= 0.80 sur >= 40 questions évaluables"}
    (a.out / f"results_{a.label}.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    miss = defaultdict(list)
    for r in rows:
        if r["status"] == "not_evaluable":
            miss[r["reason"]].append(r["id"])
    for k, v in miss.items():
        print("non évaluables :", k, v)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
