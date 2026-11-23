"""Fonde les mandats du gouverneur sur le texte réel du décret 98/031 (art. 3), au lieu du modèle de loi de l'IFRC.

Art. 3 : le gouverneur déclenche le plan d'urgence au niveau de la province ; le plan ne peut être déclenché que sur
« renseignements sûrs, ne donnant lieu à aucun doute » ; l'action comporte « la diffusion de l'alerte » et
« l'information du public ». Aucun délai n'est fixé. Usage : python scripts/fix_cameroon_mandates.py --token <animateur>
"""
from __future__ import annotations

import argparse
import sys

import httpx

ap = argparse.ArgumentParser()
ap.add_argument("--token", required=True)
ap.add_argument("--api", default="http://localhost:8000")
a = ap.parse_args()
c = httpx.Client(base_url=a.api.rstrip("/") + "/api/v1", headers={"Authorization": f"Bearer {a.token}"}, timeout=60)


def call(method: str, path: str, ok=(200, 201), **kw):  # noqa: ANN001, ANN201
    r = c.request(method, path, **kw)
    if r.status_code not in ok:
        sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
    return r.json() if r.content else None


kb = next(k for k in call("GET", "/knowledge-bases") if k["name"] == "Corpus national Cameroun")
doc = next(d for d in call("GET", f"/knowledge-bases/{kb['id']}/documents", params={"limit": 200})["items"] if d["code"] == "DOC-0006")
ver = max(call("GET", f"/documents/{doc['id']}/versions"), key=lambda v: v["version_no"])
chunks = call("GET", f"/documents/{doc['id']}/versions/{ver['version_no']}/chunks", params={"limit": 50})["items"]
art3 = next(ch for ch in chunks if ch.get("article") == "Article 3")
assert "gouverneur" in art3["text"] and "diffusion de l" in art3["text"], "article 3 introuvable"


def exact(fragment: str, until: str | None = None) -> str:
    """Extrait EXACT du texte stocké (apostrophes typographiques comprises) : du repère jusqu'à `until` inclus."""
    i = art3["text"].find(fragment)
    assert i >= 0, fragment
    j = art3["text"].find(until, i) + len(until) if until else i + len(fragment)
    return art3["text"][i:j]


insts = {i["code"]: i["id"] for i in call("GET", "/institutions")}
mandates = call("GET", "/mandates", params={"institution_id": insts["GOUVEN"]})
mandates = mandates.get("items", mandates) if isinstance(mandates, dict) else mandates
by_action = {m["action_code"]: m for m in mandates}

PLAN = {
    "activate_emergency_plan": {
        "quote": ("par le gouverneur au niveau de la province", None),
        "corrections": {"evidence_tag": "documented", "procedure_status": "specific", "has_deadline": False,
                        "description": "Le gouverneur déclenche le plan d'urgence au niveau de la province, uniquement sur "
                                       "renseignements sûrs ne donnant lieu à aucun doute (décret 98/031, art. 3). Aucun délai fixé."}},
    "broadcast_public_alert": {
        "quote": ("la diffusion de l", "alerte"),
        "corrections": {"evidence_tag": "documented", "procedure_status": "general", "has_deadline": False,
                        "description": "Une fois le plan d'urgence déclenché, l'action du gouverneur comporte la diffusion de "
                                       "l'alerte et l'information du public (décret 98/031, art. 3-3). Rien n'encadre une alerte "
                                       "précoce avant certitude, ni son délai."}},
}
for action, plan in PLAN.items():
    m = by_action.get(action)
    if m is None:
        print("mandat absent :", action)
        continue
    quote = exact(*plan["quote"])
    for src in m.get("sources", []):  # remplace une ancienne citation de l'article 3 si elle diffère
        if src["chunk_id"] == art3["id"] and src.get("quote") != quote:
            call("DELETE", f"/mandates/{m['id']}/sources/{src['id']}", ok=(200, 204))
    m = call("GET", f"/mandates/{m['id']}")
    have = {s["chunk_id"] for s in m.get("sources", [])}
    if art3["id"] not in have:
        call("POST", f"/mandates/{m['id']}/sources", json={"document_version_id": ver["id"], "chunk_id": art3["id"],
                                                          "article": "Article 3", "quote": quote})
    out = call("POST", f"/mandates/{m['id']}/validate", json={"note": "Fondé sur le texte réel du décret 98/031, art. 3",
                                                              "corrections": plan["corrections"]})
    print(f"GOUVEN {action}: {out['validation']} · {out['evidence_tag']} · procédure {out['procedure_status']} · "
          f"{len(out.get('sources', []))} source(s)")
