#!/usr/bin/env python3
"""Prépare (par l'API HTTP, comme le ferait l'interface) un espace « ALERTE — Demonstration » jusqu'à l'étape voulue du guide.

Prérequis : backend démarré ; `python scripts/rising_waters_pack.py` déjà exécuté (génère `demo/rising-waters/`).

    python scripts/seed_rising_waters.py --until 8                # tout, jusqu'à un exercice joué en mode scripted (SANS IA)
    python scripts/seed_rising_waters.py --until 4 --country AE   # jumeau Émirats jusqu'aux mandats
    python scripts/seed_rising_waters.py --token <jeton> --from 5 --until 6   # reprendre dans un espace existant

Étapes : 1 espace · 2 pays, institutions, actions · 3 bases de connaissances (import des archives du prototype, publication) ·
4 mandats (import CSV, statut « proposé ») · 5 agents et droits d'accès · 6 scénario (import YAML) · 7 exercice et sièges ·
8 préparation + lancement (autopilot **scripted = SANS IA**).

Ne supprime ni ne modifie rien : n'ajoute que des objets. Relancer l'étape 1 crée un NOUVEL espace (jamais de doublon silencieux :
utilisez --token pour réutiliser un espace). Données fictives ; aucun secret n'est écrit sur disque (le jeton est seulement affiché).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
PACK = HERE.parent.parent / "demo" / "rising-waters"
WS_NAME = "ALERTE — Demonstration"


class Api:
    def __init__(self, base: str, token: str | None) -> None:
        self.c = httpx.Client(base_url=base.rstrip("/") + "/api/v1", timeout=300)
        self.h = {"Authorization": f"Bearer {token}"} if token else {}

    def call(self, method: str, path: str, ok=(200, 201, 202), **kw):  # noqa: ANN001, ANN201
        r = self.c.request(method, path, headers=kw.pop("headers", self.h), **kw)
        if r.status_code not in ok:
            sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
        return r.json() if r.content else None

    def job(self, job_id: str, timeout: float = 600) -> dict:
        end = time.time() + timeout
        while time.time() < end:
            j = self.call("GET", f"/jobs/{job_id}")
            if j["status"] in ("done", "failed", "interrupted"):
                if j["status"] != "done":
                    sys.exit(f"job {job_id} : {j.get('status')} {j.get('error')}")
                return j
            time.sleep(0.3)
        sys.exit("délai dépassé")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--token", default=None, help="jeton propriétaire d'un espace existant (sinon : crée l'espace de démonstration)")
    ap.add_argument("--country", choices=["CM", "AE"], default="CM")
    ap.add_argument("--lang", choices=["fr", "en"], default="fr")
    ap.add_argument("--from", dest="start", type=int, default=1)
    ap.add_argument("--until", type=int, default=8)
    a = ap.parse_args()
    cc = a.country
    setup_file = PACK / f"setup-{cc.lower()}.json"
    if not setup_file.exists():
        sys.exit("pack absent : lancez d'abord `python scripts/rising_waters_pack.py`")
    setup = json.loads(setup_file.read_text(encoding="utf-8"))
    api = Api(a.api, a.token)
    state: dict[str, object] = {}

    if a.start <= 1 <= a.until:
        if a.token:
            sys.exit("l'étape 1 crée un espace : retirez --token ou utilisez --from 2")
        ws = api.call("POST", "/workspaces", json={"name": WS_NAME}, headers={})
        api.h = {"Authorization": f"Bearer {ws['owner_token']}"}
        print(f"[1] Espace « {WS_NAME} » créé. JETON PROPRIÉTAIRE (affiché une seule fois) : {ws['owner_token']}")
    elif not a.token:
        sys.exit("--from > 1 exige --token")
    fac = {"Authorization": "Bearer " + api.call("POST", "/tokens", json={"role": "facilitator", "label": "seed-rising-waters"})["token"]} \
        if a.until >= 7 else None

    countries = {c["iso2"]: c["id"] for c in api.call("GET", "/countries") if c.get("iso2")}
    insts = {i["code"]: i["id"] for i in api.call("GET", "/institutions")}
    if a.start <= 2 <= a.until:
        c = setup["country"]
        if c["iso2"] not in countries:
            countries[c["iso2"]] = api.call("POST", "/countries", json=c)["id"]
        for i in setup["institutions"]:
            if i["code"] not in insts:
                body = {k: v for k, v in i.items() if k != "seat"}
                insts[i["code"]] = api.call("POST", "/institutions", json={**body, "country_id": countries[c["iso2"]]})["id"]
        have = {x["code"] for x in api.call("GET", "/actions")}
        for act in setup["actions"]:
            if act["code"] not in have:
                api.call("POST", "/actions", json=act)
        print(f"[2] Pays {c['name']}, {len(setup['institutions'])} institutions, {len(setup['actions'])} actions")

    kbs = {x["code"]: x["id"] for x in api.call("GET", "/knowledge-bases")}
    if a.start <= 3 <= a.until:
        tmp = Path(tempfile.mkdtemp(prefix="alerte-legacy-kb-"))
        subprocess.run([sys.executable, str(HERE / "legacy_to_archive.py"), "--out", str(tmp)], check=True, capture_output=True)
        for coll in (cc, "GL"):
            if coll in kbs:
                continue
            f = tmp / f"alerte-kb-{coll}.zip"
            r = api.call("POST", "/knowledge-bases/import", files={"file": (f.name, f.read_bytes())})
            api.job(r["job"]["id"])
            cf = api.call("POST", f"/imports/{r['import']['id']}/confirm", json={"mode": "new_kb", "code": coll})
            kbs[coll] = api.job(cf["job"]["id"])["result"]["kb_id"]
            api.call("POST", f"/knowledge-bases/{kbs[coll]}/publish", json={"note": "Import du prototype (droits de redistribution inconnus)"})
        print(f"[3] Bases importées et publiées : {', '.join(sorted(kbs))} (sans embeddings : recherche lexicale seule, signalée « dégradée »)")

    if a.start <= 4 <= a.until:
        rep = api.call("POST", "/mandates/import-csv", content=(PACK / f"mandats-{cc.lower()}.csv").read_bytes(),
                       headers={**api.h, "content-type": "text/csv"})
        print(f"[4] Mandats importés (statut « proposé », sans source) : {rep}")

    agents: dict[str, str] = {}
    if a.start <= 5 <= a.until:
        have = {x["code"]: x["id"] for x in api.call("GET", "/agents")}
        for ag in setup["agents"]:
            if ag["code"] in have:
                agents[ag["institution"]] = have[ag["code"]]
                continue
            body = {k: ag[k] for k in ("code", "name", "role_kind", "mission", "instructions")}
            body["institution_id"] = insts[ag["institution"]]
            aid = api.call("POST", "/agents", json=body)["id"]
            agents[ag["institution"]] = aid
            ids = [kbs[c] for c in ({cc: cc, "INT": "GL"}.get(x, x) for x in ag["kb_collections"]) if c in kbs]
            if ids:
                api.call("PUT", f"/agents/{aid}/kb-grants", json={"kb_ids": ids})
        print(f"[5] {len(agents)} agents créés avec leurs droits d'accès aux bases")

    sc_id = None
    if a.start <= 6 <= a.until:
        stem = "cm01-rising-waters" if cc == "CM" else "ae01-rising-waters-twin"
        lang = a.lang if (PACK / f"{stem}.{a.lang}.alerte-scenario.yaml").exists() else "en"
        r = api.call("POST", "/scenarios/import", content=(PACK / f"{stem}.{lang}.alerte-scenario.yaml").read_bytes(),
                     headers={**api.h, "content-type": "application/x-yaml"})
        sc_id = r["scenario"]["id"]
        print(f"[6] Scénario importé : {r['scenario']['title']} ({len(r.get('warnings') or [])} avertissement(s))")

    if a.start <= 7 <= a.until:
        sc_id = sc_id or next(s["id"] for s in api.call("GET", "/scenarios") if s["code"].startswith(cc))
        if not agents:
            agents = {x["institution_id"]: x["id"] for x in api.call("GET", "/agents") if x.get("institution_id")}
            agents = {code: agents[iid] for code, iid in insts.items() if iid in agents}
        ex = api.call("POST", "/exercises", headers=fac, json={"scenario_id": sc_id, "ai_mode": "scripted", "pace": "auto",
                                                               # Rising Waters a 41 activations : l'estimation haute (≈ 304 appels) dépasse 1,5 x le plafond
                                                               # par défaut (199) et BLOQUE la préparation ; le budget est un réglage légitime de l'exercice
                                                               "settings": {"max_llm_calls": 330},
                                                               "title": f"Rising Waters {cc} — autopilot scripted (SANS IA)"})["id"]
        seats = [{"code": c, "institution_id": insts[c], "agent_id": agents[c], "controller": "agent"} for c in agents]
        api.call("PUT", f"/exercises/{ex}/seats", headers=fac, json={"seats": seats})
        state["exercise"] = ex
        print(f"[7] Exercice créé ({len(seats)} sièges) : {ex}")

    if a.start <= 8 <= a.until:
        ex = state.get("exercise") or api.call("GET", "/exercises", headers=fac)[0]["id"]
        rd = api.call("GET", f"/exercises/{ex}/readiness", headers=fac)
        print(f"[8] Préparation : {len(rd.get('blocking', []))} bloquant(s), {len(rd.get('warnings', []))} avertissement(s)")
        for b in rd.get("blocking", [])[:10]:
            print("    BLOQUANT :", b["code"], b["message"], b.get("subject"))
        if rd.get("blocking"):
            sys.exit("préparation bloquée : corrigez dans l'interface (guide, étape 14), puis relancez avec --from 8")
        api.call("POST", f"/exercises/{ex}/ready", headers=fac)
        api.call("POST", f"/exercises/{ex}/commands", headers=fac, json={"kind": "start", "args": {}})
        t0 = time.time()
        while time.time() - t0 < 900:
            st = api.call("GET", f"/exercises/{ex}", headers=fac)["state"]
            if st in ("completed", "stopped", "failed", "interrupted"):
                break
            time.sleep(1)
        print(f"[8] Exercice terminé : état = {st} ({int(time.time() - t0)} s)")
        api.call("POST", f"/exercises/{ex}/detect-gaps", headers=fac)
    print("Terminé. Ouvrez l'interface et collez le jeton propriétaire (écran /access).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
