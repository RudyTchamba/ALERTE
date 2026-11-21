#!/usr/bin/env python3
"""Peuple un backend EN COURS D'EXÉCUTION avec un espace de démonstration (via l'API HTTP, comme le ferait l'interface).

Usage (backend démarré, venv actif) :
    python scripts/seed_demo.py [--api http://localhost:8000] [--token <jeton propriétaire existant>]

* Sans `--token`, crée un NOUVEL espace de travail « Démo ALERTE » et affiche le jeton propriétaire (affiché une seule fois).
* Les données sont FICTIVES (pays « Demoland », texte de loi d'exemple). Par défaut l'exercice est joué en mode `scripted` : c'est un
  fournisseur de test SANS IA — les décisions affichées ne prouvent rien sur la qualité d'un modèle. `--ai-mode ai` utilise le
  serveur de génération configuré côté backend (ALERTE_LLM_BASE_URL / ALERTE_LLM_MODEL).
* Aucune donnée existante n'est modifiée ni supprimée ; le script ne fait qu'ajouter.
"""
from __future__ import annotations

import argparse
import sys
import time

import httpx

LAW = """Loi n° 2021-12 relative à l'alerte précoce (texte d'exemple fictif)

Article 1er - Objet
La présente loi organise la diffusion des alertes aux populations par les opérateurs de téléphonie mobile.

Article 2 - Définitions
Au sens de la présente loi, on entend par alerte tout message officiel émis par l'autorité nationale de protection civile.

Article 12 - Mission de l'autorité météorologique
L'autorité météorologique nationale émet les avis de vigilance et transmet sans délai tout avis de crue à la protection civile.

Article 33 - Obligations des opérateurs
Les opérateurs de téléphonie mobile sont tenus de diffuser sans délai toute alerte transmise par l'autorité nationale.
"""


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.c = httpx.Client(base_url=base.rstrip("/") + "/api/v1", timeout=120)
        self.h = {"Authorization": f"Bearer {token}"} if token else {}

    def call(self, method: str, path: str, ok=(200, 201, 202), **kw):  # noqa: ANN001, ANN201
        r = self.c.request(method, path, headers=kw.pop("headers", self.h), **kw)
        if r.status_code not in ok:
            sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
        return r.json() if r.content else None

    def wait_job(self, job_id: str, timeout: float = 300) -> dict:
        end = time.time() + timeout
        while time.time() < end:
            j = self.call("GET", f"/jobs/{job_id}")
            if j["status"] in ("done", "failed", "interrupted"):
                if j["status"] != "done":
                    sys.exit(f"job {job_id}: {j}")
                return j
            time.sleep(0.3)
        sys.exit("délai dépassé")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--token", default=None)
    ap.add_argument("--ai-mode", choices=["scripted", "ai"], default="scripted",
                    help="`ai` : agents pilotés par le serveur de génération configuré (ALERTE_LLM_BASE_URL côté backend)")
    ap.add_argument("--sim-timeout", type=float, default=180, help="durée maximale d'attente de la simulation (s)")
    ap.add_argument("--no-simulation", action="store_true", help="ne joue pas l'exercice scripté (données de configuration seulement)")
    a = ap.parse_args()

    api = Api(a.api, a.token)
    if not a.token:
        ws = api.call("POST", "/workspaces", json={"name": "Démo ALERTE"}, headers={})
        api.h = {"Authorization": f"Bearer {ws['owner_token']}"}
        print(f"Espace créé. JETON PROPRIÉTAIRE (affiché une seule fois) : {ws['owner_token']}")
    fac = {"Authorization": "Bearer " + api.call("POST", "/tokens", json={"role": "facilitator", "label": "demo"})["token"]}

    country = api.call("POST", "/countries", json={"code": "DEM", "name": "Demoland"})["id"]
    inst = {}
    for code, name in (("MET", "Service météorologique national"), ("DPC", "Direction de la protection civile"),
                       ("TEL", "Autorité de régulation des télécommunications")):
        inst[code] = api.call("POST", "/institutions", json={"code": code, "name": name, "kind": "agency", "country_id": country})["id"]

    kb = api.call("POST", "/knowledge-bases", json={"name": "Corpus national (démo)", "kind": "national", "languages": ["fr"]})["id"]
    up = api.call("POST", f"/knowledge-bases/{kb}/documents", files={"file": ("loi-2021-12.txt", LAW.encode())},
                  data={"title": "Loi 2021-12 (exemple)", "jurisdiction": "DEM"})
    api.wait_job(up["job"]["id"])
    emb = api.call("POST", f"/knowledge-bases/{kb}/embed", json={})
    if emb and emb.get("job"):
        api.wait_job(emb["job"]["id"])
    chunks = api.call("GET", f"/documents/{up['document']['id']}/versions/1/chunks")["items"]
    art12 = next(c for c in chunks if c["article"] and "12" in c["article"])
    api.call("POST", f"/knowledge-bases/{kb}/publish", json={"note": "v1 démo"})

    api.call("POST", "/actions", json={"code": "broadcast_public_alert", "label": "Diffuser l'alerte aux populations", "domain": "alerte",
                                       "derivation": "referential", "reference_note": "Loi 2021-12, art. 33 (obligation des opérateurs)"})
    api.call("POST", "/actions", json={"code": "issue_flood_warning", "label": "Émettre un avis de crue", "domain": "alerte",
                                       "derivation": "referential", "reference_note": "Loi 2021-12, art. 12"})
    m = api.call("POST", "/mandates", json={
        "institution_id": inst["MET"], "kind": "duty", "action_code": "issue_flood_warning", "procedure_status": "specific",
        "has_deadline": True, "sources": [{"document_version_id": art12["document_version_id"], "chunk_id": art12["id"]}]})
    api.call("POST", f"/mandates/{m['id']}/validate")

    # Revue du registre : l'absence de mandat n'est une lacune QUE si un humain déclare le registre complet.
    for code in ("MET", "DPC", "TEL"):
        api.call("PUT", f"/institutions/{inst[code]}/registry-review", json={
            "status": "reviewed_complete", "note": "Démo : registre déclaré complet par l'auteur de la démonstration."})

    agents = {}
    for code in inst:
        agents[code] = api.call("POST", "/agents", json={"institution_id": inst[code], "code": f"AG-{code}", "name": f"Agent {code}",
                                                          "mission": "Agir dans les limites de son mandat documenté."})["id"]
        api.call("PUT", f"/agents/{agents[code]}/kb-grants", json={"kb_ids": [kb]})

    sc = api.call("POST", "/scenarios", json={"code": "CRUE-01", "title": "Crue soudaine (démo)", "country_id": country, "language": "fr"})["id"]
    inj = api.call("POST", f"/scenarios/{sc}/injects", json={
        "title": "Alerte de crue", "body": "Des pluies intenses provoquent une montée rapide des eaux.", "sim_time": "J1 06:00",
        "from_actor": "CAPTEURS", "recipients": [inst["MET"], inst["DPC"]],
        "tags": ["life_risk", "time_critical", "public_communication", "harm_possible"]})
    api.call("PUT", f"/injects/{inj['id']}/demands", json={"demands": [
        {"action_code": "issue_flood_warning", "derivation": "referential", "justification": "Loi 2021-12, art. 12"},
        {"action_code": "broadcast_public_alert", "derivation": "referential", "justification": "Loi 2021-12, art. 33"}]})

    ex = api.call("POST", "/exercises", headers=fac, json={
        "scenario_id": sc, "ai_mode": a.ai_mode,
        "title": "Exercice de démonstration (scripted, SANS IA)" if a.ai_mode == "scripted" else "Exercice de démonstration (modèle réel)"})["id"]
    api.call("PUT", f"/exercises/{ex}/seats", headers=fac, json={"seats": [
        {"code": c, "institution_id": inst[c], "agent_id": agents[c], "controller": "agent"} for c in ("MET", "DPC")]})
    api.call("POST", f"/exercises/{ex}/ready", headers=fac)
    print(f"Exercice préparé : {ex}")

    if not a.no_simulation:
        api.call("POST", f"/exercises/{ex}/commands", headers=fac, json={"kind": "start", "args": {}})
        end = time.time() + a.sim_timeout
        state = ""
        while time.time() < end:
            state = api.call("GET", f"/exercises/{ex}", headers=fac).get("state", "")
            if state in ("completed", "stopped", "failed", "interrupted"):
                break
            time.sleep(0.5)
        print(f"Simulation : état final = {state}")
        api.call("POST", f"/exercises/{ex}/detect-gaps", headers=fac)
        rep = api.call("POST", f"/exercises/{ex}/reports", headers=fac, json={"title": "Rapport de démonstration", "language": "fr"})
        api.wait_job(rep["job"]["id"])
        print("Lacunes détectées et rapport généré.")
    print("Terminé. Ouvrez http://localhost:5173/access et collez le jeton propriétaire.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
