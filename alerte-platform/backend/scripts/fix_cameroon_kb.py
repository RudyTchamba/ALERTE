"""Corrige le corpus Cameroun importé du prototype, puis (option --rerun) rejoue l'exercice et compare les lacunes.

Défauts corrigés :
* DOC-0006 « Décret 98/031 » contenait le rapport IDNDR (mauvais fichier dans le manifeste du prototype) :
  nouvelle version avec le vrai décret (scripts/corpus_fixes/CM-07_...pdf) ; l'ancienne reste dans l'historique ;
* titres faux (DOC-0007, DOC-0013), fiabilité (« official » donné aux rapports et à la presse), validité, licences ;
* liste des documents attendus (couverture mesurable), puis publication d'une nouvelle version de la base.

Usage : python scripts/fix_cameroon_kb.py --token <jeton animateur> [--rerun]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
DECREE = HERE / "corpus_fixes" / "CM-07_Decree_No_98-031_of_9_March_1998_on_the_Organisation_of_Emergency_and_Rescue_Plans.pdf"
KB_NAME = "Corpus national Cameroun"

# code -> métadonnées corrigées. Lois et décrets : textes officiels publiés par l'État (redistribution autorisée,
# à confirmer par l'équipe) ; rapports d'organisations et presse : sources secondaires, non redistribuées.
OFFICIAL = {"reliability": "official", "validity": "in_force", "redistribution": "allowed", "evidence_default": "documented"}
SECONDARY = {"reliability": "summary", "validity": "unknown", "redistribution": "restricted", "evidence_default": "inferred"}
META: dict[str, dict] = {
    **{c: OFFICIAL for c in ("DOC-0001", "DOC-0002", "DOC-0003", "DOC-0004", "DOC-0005", "DOC-0008", "DOC-0010")},
    "DOC-0006": {**OFFICIAL, "title": "Décret n° 98/031 du 9 mars 1998 portant organisation des plans d'urgence et des secours "
                                      "en cas de catastrophe ou de risque majeur", "doc_type": "decree", "language": "fr"},
    "DOC-0007": {**OFFICIAL, "title": "Décret n° 2005/124 du 15 avril 2005 portant organisation du Ministère des Postes "
                                      "et Télécommunications", "doc_type": "decree", "language": "fr"},
    "DOC-0009": {**OFFICIAL, "title": "Plan National de Contingence (PNC), Cameroun, avril 2011"},
    "DOC-0017": {**OFFICIAL, "validity": "unknown"},
    "DOC-0014": {**OFFICIAL, "validity": "unknown", "doc_type": "statement"},  # déclaration officielle du gouvernement à l'ONU
    "DOC-0011": SECONDARY, "DOC-0012": SECONDARY, "DOC-0015": SECONDARY, "DOC-0016": SECONDARY,
    "DOC-0013": {**SECONDARY, "reliability": "unofficial", "doc_type": "press",
                 "title": "Investir au Cameroun — article de presse sur la Stratégie nationale d'intelligence artificielle (2025)"},
}
# Documents attendus pour un exercice d'alerte et de crise (couverture) : (titre, référence, code présent ou None)
EXPECTED = [
    ("Loi n° 86/016 portant réorganisation générale de la protection civile", "Loi 86/016", "DOC-0005"),
    ("Décret n° 98/031 portant organisation des plans d'urgence et des secours", "Décret 98/031", "DOC-0006"),
    ("Plan National de Contingence", "PNC 2011", "DOC-0009"),
    ("Loi n° 90/047 relative à l'état d'urgence", "Loi 90/047", "DOC-0008"),
    ("Loi n° 2010/013 régissant les communications électroniques", "Loi 2010/013", "DOC-0002"),
    ("Loi n° 2015/006 modifiant la loi 2010/013", "Loi 2015/006", "DOC-0003"),
    ("Loi n° 2010/012 relative à la cybersécurité et à la cybercriminalité", "Loi 2010/012", "DOC-0004"),
    ("Loi n° 2024/017 relative à la protection des données à caractère personnel", "Loi 2024/017", "DOC-0001"),
    ("Loi n° 2019/024 portant Code général des collectivités territoriales décentralisées", "Loi 2019/024", "DOC-0010"),
    ("Décret n° 2005/124 portant organisation du MINPOSTEL", "Décret 2005/124", "DOC-0007"),
    ("Plan de préparation et de riposte au choléra (MINSANTE)", "Plan choléra", "DOC-0017"),
    ("Décret n° 96/054 fixant la composition et les attributions du Conseil national de la protection civile", "Décret 96/054", None),
    ("Texte créant l'Observatoire national des risques (ONR)", "ONR", None),
    ("Stratégie nationale d'intelligence artificielle (texte officiel)", "SNIA 2025", None),
    ("Texte organisant l'alerte précoce et la diffusion des alertes au public (cell broadcast / SMS)", "alerte au public", None),
]

ap = argparse.ArgumentParser()
ap.add_argument("--token", required=True)
ap.add_argument("--api", default="http://localhost:8000")
ap.add_argument("--rerun", action="store_true", help="rejoue l'exercice Cameroun (IA) et compare ses lacunes à --ref")
ap.add_argument("--ref", default="EX-019", help="exercice de référence (sièges copiés, lacunes comparées)")
ap.add_argument("--title", default="Crue de l'Extrême-Nord — corpus corrigé (IA)", help="titre du nouvel exercice")
a = ap.parse_args()
c = httpx.Client(base_url=a.api.rstrip("/") + "/api/v1", headers={"Authorization": f"Bearer {a.token}"}, timeout=120)


def call(method: str, path: str, ok=(200, 201, 202), **kw):  # noqa: ANN001, ANN201
    r = c.request(method, path, **kw)
    if r.status_code not in ok:
        sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
    return r.json() if r.content else None


def wait(job_id: str, timeout: int = 1800) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        j = call("GET", f"/jobs/{job_id}")
        if j["status"] in ("done", "failed", "interrupted"):
            return j
        time.sleep(1)
    return {"status": "timeout"}


kb = next(k for k in call("GET", "/knowledge-bases") if k["name"] == KB_NAME)
docs = {d["code"]: d for d in call("GET", f"/knowledge-bases/{kb['id']}/documents", params={"limit": 200})["items"]}
print(f"base {kb['name']} : {len(docs)} documents")

# 1. Le vrai décret 98/031 en nouvelle version de DOC-0006 (une seule fois)
d6 = docs["DOC-0006"]
first = call("GET", f"/documents/{d6['id']}/versions")
latest = max(first, key=lambda v: v["version_no"]) if isinstance(first, list) else None
chunks = call("GET", f"/documents/{d6['id']}/versions/{latest['version_no']}/chunks", params={"limit": 3}) if latest else None
items = chunks.get("items", chunks) if isinstance(chunks, dict) else (chunks or [])
if items and "98/031" in (items[0].get("text") or "")[:300]:
    print("DOC-0006 : le vrai décret est déjà la version courante")
else:
    with DECREE.open("rb") as fh:
        up = call("POST", f"/documents/{d6['id']}/versions", files={"file": (DECREE.name, fh, "application/pdf")},
                  data={"note": "Correction : la version 1 contenait le rapport IDNDR (mauvais fichier du prototype)"})
    j = wait(up["job"]["id"])
    print("DOC-0006 : nouvelle version", up["version"]["version_no"], "->", j["status"], j.get("error") or "")

# 2. Métadonnées
for code, meta in META.items():
    if code in docs:
        call("PATCH", f"/documents/{docs[code]['id']}", json=meta)
print(f"métadonnées corrigées : {len(META)} documents")

# 3. Documents attendus (idempotent : par titre)
have = {e["title"] for e in call("GET", f"/knowledge-bases/{kb['id']}/expected")["items"]}
for title, cit, code in EXPECTED:
    if title in have:
        continue
    body = {"title": title, "jurisdiction": "CM", "citation": cit, "status": "present" if code else "missing"}
    if code and code in docs:
        body["matched_document_id"] = docs[code]["id"]
    call("POST", f"/knowledge-bases/{kb['id']}/expected", json=body)
print(f"documents attendus : {len(EXPECTED)} ({sum(1 for e in EXPECTED if e[2])} présents)")

# 4. Publication
pub = call("POST", f"/knowledge-bases/{kb['id']}/publish", json={"note": "Corrections : décret 98/031, titres, fiabilité, licences"},
           ok=(200, 201, 202, 409))
print("publication :", (pub or {}).get("version_no") or (pub or {}).get("error", {}).get("code") or pub)
ov = call("GET", f"/knowledge-bases/{kb['id']}")
print("couverture :", (ov.get("overview") or {}).get("coverage"))

if not a.rerun:
    sys.exit(0)

# 5. Rejouer l'exercice avec les mêmes sièges qu'EX-019, puis comparer les lacunes
exs = call("GET", "/exercises")
ref = next(e for e in exs if e["code"] == a.ref)
ref_full = call("GET", f"/exercises/{ref['id']}")
seats = [{"code": s["code"], "institution_id": s["institution_id"], "agent_id": s["agent_id"], "controller": "agent"}
         for s in ref_full["seats"]]
ex = call("POST", "/exercises", json={"scenario_id": ref["scenario_id"], "ai_mode": "ai", "pace": "auto",
                                      "title": a.title, "settings": ref_full.get("settings")})
call("PUT", f"/exercises/{ex['id']}/seats", json={"seats": seats})
call("POST", f"/exercises/{ex['id']}/ready")
call("POST", f"/exercises/{ex['id']}/commands", json={"kind": "start"})
print("exercice", ex["code"], "lancé")
t0 = time.time()
while time.time() - t0 < 3600:
    st = call("GET", f"/exercises/{ex['id']}")["state"]
    if st in ("completed", "stopped", "interrupted"):
        break
    time.sleep(10)
print("état final :", st, f"({time.time() - t0:.0f} s)")
call("POST", f"/exercises/{ex['id']}/detect-gaps")


def gap_set(eid: str) -> dict[str, str]:
    return {g["title"]: f"S{g['severity']}" for g in call("GET", "/gaps", params={"exercise": eid}) if g.get("is_current", True)}


before, after = gap_set(ref["id"]), gap_set(ex["id"])
print(f"\nlacunes {a.ref} : {len(before)} | {ex['code']} : {len(after)}")
for t in sorted(set(before) - set(after)):
    print("  disparue :", t)
for t in sorted(set(after) - set(before)):
    print("  nouvelle :", t)
for t in sorted(set(before) & set(after)):
    print("  confirmée:", t)
