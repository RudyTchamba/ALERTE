#!/usr/bin/env python
"""Recrée le cas réel « Cameroun » dans un espace ALERTE EN COURS D'EXÉCUTION, via l'API HTTP.

    python scripts/seed_cameroon.py --token <jeton propriétaire> [--api http://localhost:8000] [--corpus-dir DIR]

1. Corpus : les 17 documents CM du prototype (lois, décrets, plans, rapports IFRC/UNICEF/Gavi) sont restaurés depuis
   l'historique Git (commit 5787a2e) dans un dossier temporaire, sauf si --corpus-dir est fourni, puis importés dans une
   base « Corpus national Cameroun » (extraction, OCR, découpage, embeddings) et publiés. Droits de redistribution : « unknown ».
2. Pays « Cameroun », 8 institutions, 10 actions, 10 mandats PROPOSÉS avec la source exacte (extrait du corpus).
   Les mandats ne sont PAS validés et aucun registre n'est déclaré complet : ces décisions reviennent à des humains.
3. 7 agents (accès au corpus), scénario « Crue de l'Extrême-Nord (octobre 2024) » (4 événements), exercice non lancé.

Idempotent : ce qui existe déjà (par code ou par nom) est réutilisé. Nécessite un serveur d'embeddings pour la recherche
hybride (sinon recherche lexicale) ; le pays « Cameroun » est créé s'il n'existe pas.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

COMMIT = "5787a2e"
REPO = Path(__file__).resolve().parents[3]

ap = argparse.ArgumentParser()
ap.add_argument("--token", required=True)
ap.add_argument("--api", default="http://localhost:8000")
ap.add_argument("--corpus-dir", type=Path, default=None, help="dossier contenant manifest.csv et les PDF CM-*.pdf")
a = ap.parse_args()
c = httpx.Client(base_url=a.api.rstrip("/") + "/api/v1", timeout=600, headers={"Authorization": f"Bearer {a.token}"})


def call(method, path, ok=(200, 201, 202), **kw):
    r = c.request(method, path, **kw)
    if r.status_code not in ok:
        sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
    return r.json() if r.content else None


def wait(job_id, timeout=1800):
    end = time.time() + timeout
    while time.time() < end:
        j = call("GET", f"/jobs/{job_id}")
        if j["status"] in ("done", "failed", "interrupted"):
            return j
        time.sleep(1)
    return {"status": "timeout"}


def restore_corpus() -> Path:
    out = Path(tempfile.mkdtemp(prefix="alerte-cm-"))
    git = ["git", "-C", str(REPO)]
    (out / "manifest.csv").write_bytes(subprocess.run([*git, "show", f"{COMMIT}:alerte/data/manifest.csv"], check=True, capture_output=True).stdout)
    files = subprocess.run([*git, "ls-tree", "-r", "--name-only", COMMIT, "--", "alerte/data/docs/CM"], check=True, capture_output=True, text=True).stdout.split()
    for f in files:
        (out / Path(f).name).write_bytes(subprocess.run([*git, "show", f"{COMMIT}:{f}"], check=True, capture_output=True).stdout)
    print(f"corpus restauré : {len(files)} documents dans {out}", flush=True)
    return out


CORPUS = a.corpus_dir or restore_corpus()
if not any(x["name"] == "Cameroun" for x in call("GET", "/countries")):
    call("POST", "/countries", json={"name": "Cameroun", "iso2": "CM", "languages": ["fr", "en"]})

kbs = call("GET", "/knowledge-bases")
kb = next((k for k in kbs if k["name"] == "Corpus national Cameroun"), None)
if kb is None:
    kb = call("POST", "/knowledge-bases", json={"name": "Corpus national Cameroun", "kind": "national", "languages": ["fr", "en"],
                                                "description": "Textes réels (lois, décrets, plans, rapports) — corpus du prototype ALERTE."})
kb_id = kb["id"]
print("KB", kb_id, flush=True)

rows = [r for r in csv.DictReader(open(CORPUS / "manifest.csv", encoding="utf-8")) if r["doc_id"].startswith("CM-")]
done_docs = []
already = {d["title"] for d in (call("GET", f"/knowledge-bases/{kb_id}/documents", params={"limit": 200}) or {}).get("items", [])}
for r in rows:
    if r["title"][:500] in already:
        continue
    f = CORPUS / Path(r["file"]).name
    if not f.exists():
        print("absent:", f.name, flush=True)
        continue
    meta = {"title": r["title"][:500], "doc_type": r["doc_type"] or None, "jurisdiction": "CM", "language": r["language"] or None,
            "source_url": r["url"] or None, "reliability": r["reliability"] if r["reliability"] in ("official", "summary", "unofficial") else None,
            "validity": "in_force" if r.get("status") == "current" else "unknown", "redistribution": "unknown"}
    data = {k: v for k, v in meta.items() if v}
    t0 = time.time()
    with open(f, "rb") as fh:
        up = call("POST", f"/knowledge-bases/{kb_id}/documents", files={"file": (f.name, fh, "application/pdf")}, data=data)
    j = wait(up["job"]["id"])
    doc = up["document"]
    print(f"{r['doc_id']}: job={j['status']} {time.time() - t0:.0f}s {j.get('error') or ''}", flush=True)
    done_docs.append((r["doc_id"], doc["id"]))

emb = call("POST", f"/knowledge-bases/{kb_id}/embed", json={})
if emb and emb.get("job"):
    print("embeddings :", wait(emb["job"]["id"], 3600)["status"], flush=True)

country = next(x for x in call("GET", "/countries") if x["name"] == "Cameroun")["id"]
existing = {i["code"]: i for i in call("GET", "/institutions")}

INSTS = [
    ("PROCIV", "Direction de la Protection Civile (MINAT)", "agency"),
    ("GOUVEN", "Gouverneur de la Région de l'Extrême-Nord", "local_authority"),
    ("MINSANTE", "Ministère de la Santé Publique", "ministry"),
    ("ART", "Agence de Régulation des Télécommunications", "regulator"),
    ("MINPOSTEL", "Ministère des Postes et Télécommunications", "ministry"),
    ("OPS", "Opérateurs de téléphonie mobile", "operator"),
    ("MAIRIE", "Commune de Maroua (Maire)", "local_authority"),
]
inst = {}
for code, name, kind in INSTS:
    inst[code] = existing[code]["id"] if code in existing else call("POST", "/institutions", json={"code": code, "name": name, "kind": kind, "country_id": country})["id"]
inst["ANTIC"] = existing["ANTIC"]["id"] if "ANTIC" in existing else call("POST", "/institutions", json={"code": "ANTIC", "name": "Agence Nationale des Technologies de l'Information et de la Communication", "kind": "agency", "country_id": country})["id"]
print("institutions:", ", ".join(inst), flush=True)

ACTIONS = [
    ("issue_flood_warning", "Émettre un avis de crue", "Attendu de tout dispositif d'alerte précoce (cadre Sendai / EW4All)"),
    ("activate_emergency_plan", "Déclencher le plan d'urgence (ORSEC)", "Décret 98/031, art. 2-3"),
    ("coordinate_civil_protection", "Coordonner la protection civile", "Décret 98/031 ; PNC"),
    ("monitor_risks", "Surveiller les risques et centraliser l'information", "PNC §2.1.2.1 (Observatoire national des risques)"),
    ("broadcast_public_alert", "Diffuser l'alerte aux populations", "PNC, stratégie de gestion de l'information"),
    ("emergency_telecom_plan", "Mettre en œuvre les télécommunications d'urgence", "Décret 2005/124, art. 58"),
    ("regulate_operators", "Contrôler les opérateurs de télécommunications", "Loi 2010/013, art. 36"),
    ("counter_false_alerts", "Contrer les fausses alertes en ligne", "Loi 2010/012, art. 7 et 78"),
    ("cholera_response", "Surveillance et riposte contre le choléra", "Plan de préparation et de riposte choléra (MINSANTE)"),
    ("municipal_safety", "Assurer la sécurité et la salubrité publiques locales", "Loi 2019/024, art. 216-218"),
]
have = {a["code"] for a in call("GET", "/actions")}
for code, label, note in ACTIONS:
    if code not in have:
        call("POST", "/actions", json={"code": code, "label": label, "domain": "alerte", "derivation": "referential", "reference_note": note})


def chunk(query, suffix):
    hits = call("POST", f"/knowledge-bases/{kb_id}/search", json={"query": query, "k": 10})["hits"]
    h = next((x for x in hits if x["chunk_id"].endswith(suffix)), None)
    if h is None:
        sys.exit(f"extrait introuvable : {suffix} ({query})")
    return {"document_version_id": h["document_version_id"], "chunk_id": h["chunk_id"]}


# (institution, action, kind, evidence, description, [(query, suffix)])
MANDATES = [
    ("GOUVEN", "activate_emergency_plan", "duty", "inferred", "Le gouverneur déclenche le plan ORSEC au niveau régional (selon l'IFRC citant le décret 98/031, art. 2-3).",
     [("le gouverneur ou le préfet déclenche le plan ORSEC", "C6W6ZZ")]),
    ("PROCIV", "coordinate_civil_protection", "duty", "documented", "La DPC est chargée de l'organisation des activités de protection civile sur l'ensemble du territoire.",
     [("qui déclenche le plan d'organisation des secours en cas de catastrophe", "C65NGK"), ("missions de la protection civile ministre administration territoriale", "WPX6C3")]),
    ("PROCIV", "monitor_risks", "duty", "documented", "L'Observatoire national des risques, au sein de la DPC, collecte, analyse, stocke et diffuse l'information.",
     [("Observatoire National des Risques collecte analyse diffusion", "5BFHG3")]),
    ("PROCIV", "broadcast_public_alert", "duty", "inferred", "La diffusion de l'alerte est faite par les autorités administratives et la DPC ; aucun autre détail sur le système d'alerte (IFRC).",
     [("alerte des populations en cas de catastrophe", "C6W706")]),
    ("GOUVEN", "broadcast_public_alert", "duty", "inferred", "Les autorités administratives diffusent l'alerte, conjointement avec la DPC, sans règle de répartition (IFRC).",
     [("alerte des populations en cas de catastrophe", "C6W706")]),
    ("MINPOSTEL", "emergency_telecom_plan", "duty", "documented", "Le Service des télécommunications d'urgence conçoit et met en œuvre les plans d'urgence des télécommunications.",
     [("télécommunications d'urgence", "ZRQVR0")]),
    ("ART", "regulate_operators", "power", "documented", "L'Agence assure la régulation, le contrôle et le suivi des activités des opérateurs.",
     [("Agence de Régulation des Télécommunications missions", "2219J9"), ("Agence de Régulation des Télécommunications missions", "D7NHTZ")]),
    ("ANTIC", "counter_false_alerts", "power", "inferred", "L'ANTIC régule la sécurité électronique (art. 7) ; la propagation de fausses nouvelles est réprimée (art. 78).",
     [("Agence de Régulation des Télécommunications missions", "W2VES4"), ("fausses informations diffusion de nouvelles mensongères sanctions", "W2VEVE")]),
    ("MINSANTE", "cholera_response", "duty", "documented", "Le plan national organise la détection, la notification et la riposte contre le choléra.",
     [("surveillance épidémiologique notification des cas de choléra district de santé", "CDMDDQ")]),
    ("MAIRIE", "municipal_safety", "duty", "documented", "Le Maire est chargé de la police municipale : bon ordre, sûreté, sécurité et salubrité publiques.",
     [("le maire est chargé de la police municipale prévention des accidents fléaux calamiteux", "EHBNE6"),
      ("le maire est chargé de la police municipale prévention des accidents fléaux calamiteux", "EHBNE8")]),
]
# Statut de procédure selon les sources : ORSEC et plan choléra décrivent une procédure ; l'IFRC indique qu'aucun
# détail n'existe sur le système d'alerte ; ailleurs, le texte attribue la mission sans décrire la procédure.
PROCEDURE = {("GOUVEN", "activate_emergency_plan"): "specific", ("MINSANTE", "cholera_response"): "specific",
             ("PROCIV", "broadcast_public_alert"): "none", ("GOUVEN", "broadcast_public_alert"): "none"}
existing_m = {(m["institution_id"], m["action_code"]) for m in call("GET", "/mandates")}
n = 0
for ic, action, kind, ev, desc, srcs in MANDATES:
    if (inst[ic], action) in existing_m:
        continue
    call("POST", "/mandates", json={"institution_id": inst[ic], "kind": kind, "action_code": action, "description": desc,
                                    "procedure_status": PROCEDURE.get((ic, action), "general"), "evidence_tag": ev, "sources": [chunk(q, s) for q, s in srcs]})
    n += 1
print("mandats proposés créés :", n, flush=True)

pub = call("POST", f"/knowledge-bases/{kb_id}/publish", json={"note": "Corpus réel Cameroun v1"}, ok=(200, 201, 202, 409))
print("publication KB :", "déjà publiée (aucun changement)" if pub and pub.get("error", {}).get("code") == "kb.publish.unchanged"
      else "ok" if pub and not pub.get("error") else pub, flush=True)

SEATS = ["PROCIV", "GOUVEN", "MINSANTE", "ART", "OPS", "MAIRIE", "ANTIC"]
agents = {a["code"]: a["id"] for a in call("GET", "/agents")}
for code in SEATS:
    ac = f"AG-{code}"
    if ac not in agents:
        name = next((n_ for c_, n_, _ in INSTS if c_ == code), "Agence Nationale des TIC")
        agents[ac] = call("POST", "/agents", json={"institution_id": inst[code], "code": ac, "name": f"Agent {code}",
                                                    "mission": f"Représenter {name} dans la limite de ses mandats documentés."})["id"]
    call("PUT", f"/agents/{agents[ac]}/kb-grants", json={"kb_ids": [kb_id]})

scs = {s["code"]: s["id"] for s in call("GET", "/scenarios")}
if "CRUE-EN-2024" in scs:
    sc = scs["CRUE-EN-2024"]
else:
    sc = call("POST", "/scenarios", json={"code": "CRUE-EN-2024", "title": "Crue de l'Extrême-Nord (octobre 2024)", "country_id": country, "language": "fr",
                                          "description": "Inspiré des inondations réelles de l'Extrême-Nord (UNICEF, flash update n° 5, 24 octobre 2024) et de l'épidémie de choléra qui a suivi (Gavi)."})["id"]
    INJ = [
        ("J1 06:00", "Crue du Logone", "Des pluies diluviennes font monter le Logone ; les digues autour de Kousseri sont menacées.", "CAPTEURS",
         ["PROCIV", "GOUVEN", "MAIRIE"], ["life_risk", "time_critical"], ["issue_flood_warning", "activate_emergency_plan", "coordinate_civil_protection"]),
        ("J1 10:00", "Villages inondés", "Plusieurs villages sont sous les eaux ; des milliers d'habitants doivent être alertés et évacués.", "TERRAIN",
         ["PROCIV", "GOUVEN", "OPS", "ART"], ["life_risk", "time_critical", "public_communication"], ["broadcast_public_alert", "monitor_risks"]),
        ("J1 14:00", "Fausse alerte virale", "Un message viral annonce faussement la rupture d'une digue et appelle à fuir de nuit.", "RÉSEAUX SOCIAUX",
         ["ANTIC", "ART", "OPS"], ["public_communication", "harm_possible"], ["counter_false_alerts", "regulate_operators"]),
        ("J3 08:00", "Premiers cas de choléra", "Des cas de diarrhée aiguë sont signalés dans les sites de déplacés ; suspicion de choléra.", "DISTRICT DE SANTÉ",
         ["MINSANTE", "MAIRIE", "PROCIV"], ["life_risk", "harm_possible"], ["cholera_response", "municipal_safety"]),
    ]
    for t, title, body, frm, rec, tags, dem in INJ:
        i = call("POST", f"/scenarios/{sc}/injects", json={"title": title, "body": body, "sim_time": t, "from_actor": frm,
                                                           "recipients": [inst[x] for x in rec], "tags": tags})
        call("PUT", f"/injects/{i['id']}/demands", json={"demands": [{"action_code": d, "derivation": "referential", "justification": "Attendu du dispositif national (voir catalogue)"} for d in dem]})
print("scénario :", sc, flush=True)

if any(e["scenario_id"] == sc for e in call("GET", "/exercises")):
    print("exercice déjà présent pour ce scénario : rien à créer.", flush=True)
    sys.exit(0)
fac = {"Authorization": "Bearer " + call("POST", "/tokens", json={"role": "facilitator", "label": "cm-setup"})["token"]}
ex = c.post("/exercises", headers=fac, json={"scenario_id": sc, "ai_mode": "ai", "title": "Crue de l'Extrême-Nord — corpus réel (IA)"}).json()
c.put(f"/exercises/{ex['id']}/seats", headers=fac, json={"seats": [{"code": s, "institution_id": inst[s], "agent_id": agents[f"AG-{s}"], "controller": "agent"} for s in SEATS]})
rd = c.get(f"/exercises/{ex['id']}/readiness", headers=fac).json()
print("exercice :", ex["code"], ex["id"], "| préparation ok =", rd.get("ok"), flush=True)
for chk in rd.get("checks", []):
    print(f"   [{chk['level']}] {chk['code']}: {chk['message'][:150]}", flush=True)
