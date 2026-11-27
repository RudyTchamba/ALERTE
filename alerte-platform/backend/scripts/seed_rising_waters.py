#!/usr/bin/env python3
"""Prépare (par l'API HTTP, comme le ferait l'interface) un espace « ALERTE — Demonstration » jusqu'à l'étape voulue du guide.

Prérequis : backend démarré ; `python scripts/rising_waters_pack.py` déjà exécuté (génère `demo/rising-waters/`).

    python scripts/seed_rising_waters.py --until 8                # tout, jusqu'à un exercice joué en mode scripted (SANS IA)
    python scripts/seed_rising_waters.py --until 4 --country AE   # jumeau Émirats jusqu'aux mandats
    python scripts/seed_rising_waters.py --token <jeton> --from 5 --until 6   # reprendre dans un espace existant
    python scripts/seed_rising_waters.py --until 7 --ai-mode ai --allow-missing-kbs   # exercice « Modèle réel » (créé, NON lancé : voir le guide, parcours B)
    python scripts/seed_rising_waters.py --token <jeton> --from 5 --until 5 --fix-agents   # aligne des agents existants sur le pack (rôle, institution, mission)

Étapes : 1 espace · 2 pays, institutions, actions · 3 base de connaissances RECONSTRUITE à partir des PDF (vérifiée complète, publiée ;
elle doit déjà exister : `python -m app.cli knowledge build --country CC`, aucun import de l'ancien prototype) ·
4 mandats de la nouvelle base (import CSV, statut « proposé ») · 5 agents et droits d'accès · 6 scénario (import YAML) · 7 exercice et sièges ·
8 préparation + lancement (autopilot **scripted = SANS IA**).

Ne supprime rien : n'ajoute que des objets (un agent déjà présent mais DIFFÉRENT du pack fait échouer l'étape 5 ; --fix-agents l'aligne
explicitement). Le mode scripted est SANS IA : il ne prouve ni la génération par un modèle ni la coordination entre agents. Seul
--ai-mode ai crée un exercice « Modèle réel » (et seul le lancement dans l'interface, après la préparation, l'exécute). Relancer l'étape 1 crée un NOUVEL espace (jamais de doublon silencieux :
utilisez --token pour réutiliser un espace). Données fictives ; aucun secret n'est écrit sur disque (le jeton est seulement affiché).
"""
from __future__ import annotations

import argparse
import json
import sys
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
    ap.add_argument("--ai-mode", choices=["scripted", "ai"], default="scripted",
                    help="scripted = SANS IA (défaut) ; ai = « Modèle réel » (l'étape 8 ne lance alors RIEN : lancez depuis l'interface)")
    ap.add_argument("--pace", choices=["auto", "manual", "auto_delay"], default="auto")
    ap.add_argument("--max-calls", type=int, default=330, help="budget d'appels au modèle de l'exercice (défaut 330)")
    ap.add_argument("--allow-missing-kbs", action="store_true",
                    help="accepter que des bases demandées par les agents (ex. GL) ne soient pas construites : les agents n'y auront pas accès")
    ap.add_argument("--fix-agents", action="store_true", help="aligner sur le pack les agents déjà présents qui en diffèrent (rôle, institution, mission)")
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
        # La base de connaissances est celle RECONSTRUITE à partir des PDF (CLI `python -m app.cli knowledge build`) : ce script n'importe
        # plus l'ancienne archive du prototype et ne construit rien. Il vérifie que la base du pays est complète, puis la publie.
        if cc not in kbs:
            sys.exit(f"[3] la base {cc} n'existe pas dans cet espace. Construisez-la d'abord à partir des PDF : "
                     f"`python -m app.cli knowledge build --country {cc}` (voir docs/knowledge-base/cli-et-pipeline.md), puis relancez avec --from 3.")
        st = api.call("GET", f"/knowledge-bases/{kbs[cc]}/status")
        if st["general_status"] != "ready":
            e = st["embeddings"]
            sys.exit(f"[3] la base {cc} n'est pas complète (état « {st['general_status']} », vecteurs {e['embedded']}/{e['chunks']}). "
                     f"Terminez sa construction : `python -m app.cli knowledge build --country {cc}`, puis relancez avec --from 3.")
        if cc in countries:  # une base nationale est rattachée à son pays (relation enregistrée, pas seulement affichée)
            api.call("PATCH", f"/knowledge-bases/{kbs[cc]}", json={"country_id": countries[cc]})
        if st["active_version"] is None:
            api.call("POST", f"/knowledge-bases/{kbs[cc]}/publish", json={"note": "Base reconstruite à partir des PDF"})
        missing = [c for c in ("GL",) if c not in kbs]
        print(f"[3] Base {cc} reconstruite, complète et publiée." + (f" Non construites (agents sans accès à ces bases) : {', '.join(missing)}." if missing else ""))

    if a.start <= 4 <= a.until:
        mandates_csv = PACK / f"mandats-{cc.lower()}.csv"
        registry = PACK.parent.parent / "knowledge_bases" / "curation" / f"mandates.{cc}.json"
        if not registry.exists():
            sys.exit(f"[4] aucun registre de mandats de la NOUVELLE base pour {cc} ({registry.relative_to(PACK.parent.parent)} absent) : "
                     f"rien n'est importé. Un éventuel {mandates_csv.name} serait un reste de l'ancien prototype (codes périmés) : ignoré.")
        if not mandates_csv.exists():
            sys.exit(f"[4] {mandates_csv.name} absent : lancez `python scripts/rising_waters_pack.py` (il le génère depuis {registry.name}).")
        import csv as _csv
        ref_csv = {r["line_id"] for r in _csv.DictReader(mandates_csv.read_text(encoding="utf-8-sig").splitlines())}
        ref_json = {m["ref"] for m in json.loads(registry.read_text(encoding="utf-8"))["mandates"]}
        if ref_csv != ref_json:
            sys.exit(f"[4] {mandates_csv.name} est PÉRIMÉ : ses mandats ({sorted(ref_csv ^ ref_json)[:6]}…) ne correspondent pas à {registry.name}. "
                     "Régénérez-le : `python scripts/rising_waters_pack.py`.")
        rep = api.call("POST", "/mandates/import-csv", content=mandates_csv.read_bytes(),
                       headers={**api.h, "content-type": "text/csv"})
        print(f"[4] Mandats importés (statut « proposé », sans source) : {rep}")

    agents: dict[str, str] = {}
    if a.start <= 5 <= a.until:
        have = {x["code"]: x for x in api.call("GET", "/agents")}
        wanted = {ag["code"]: ag for ag in setup["agents"]}
        # bases demandées par les agents : si l'une n'est pas construite, on échoue SAUF choix explicite (--allow-missing-kbs)
        absent = sorted({{cc: cc, "INT": "GL"}.get(x, x) for ag in setup["agents"] for x in ag["kb_collections"]} - set(kbs))
        if absent and not a.allow_missing_kbs:
            sys.exit(f"[5] bases demandées par les agents mais non construites : {', '.join(absent)}. Les agents n'y auraient PAS accès. "
                     "Construisez-les, ou acceptez explicitement cette limite avec --allow-missing-kbs (à signaler dans le rapport de test).")
        diffs = []
        for code, ag in wanted.items():
            cur = have.get(code)
            if cur is None:
                continue
            bad = [k for k in ("role_kind", "mission", "instructions") if (cur.get(k) or "") != ag[k]] + \
                  (["institution"] if cur.get("institution_id") != insts.get(ag["institution"]) else [])
            if bad:
                diffs.append((code, cur["id"], bad))
        if diffs and not a.fix_agents:
            sys.exit("[5] des agents existants DIFFÈRENT du pack : " + "; ".join(f"{c} ({', '.join(b)})" for c, _, b in diffs)
                     + ". Le script ne les modifie pas en silence : corrigez-les dans l'interface (Agents) ou relancez avec --fix-agents.")
        for code, aid, bad in diffs:
            ag = wanted[code]
            api.call("PATCH", f"/agents/{aid}", json={"role_kind": ag["role_kind"], "institution_id": insts[ag["institution"]],
                                                       "mission": ag["mission"], "instructions": ag["instructions"]})
            print(f"    agent {code} aligné sur le pack ({', '.join(bad)})")
        for ag in setup["agents"]:
            if ag["code"] in have:
                agents[ag["institution"]] = have[ag["code"]]["id"]
                continue
            body = {k: ag[k] for k in ("code", "name", "role_kind", "mission", "instructions")}
            body["institution_id"] = insts[ag["institution"]]
            aid = api.call("POST", "/agents", json=body)["id"]
            agents[ag["institution"]] = aid
            ids = [kbs[c] for c in ({cc: cc, "INT": "GL"}.get(x, x) for x in ag["kb_collections"]) if c in kbs]
            if ids:
                api.call("PUT", f"/agents/{aid}/kb-grants", json={"kb_ids": ids})
        print(f"[5] {len(agents)} agents prêts avec leurs droits d'accès aux bases" + (f" (bases ABSENTES, sans accès : {', '.join(absent)})" if absent else ""))

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
        label = "autopilot scripted (SANS IA)" if a.ai_mode == "scripted" else "autopilot MODÈLE RÉEL"
        ex = api.call("POST", "/exercises", headers=fac, json={"scenario_id": sc_id, "ai_mode": a.ai_mode, "pace": a.pace,
                                                               # l'estimation haute d'appels dépasse 1,5 x le plafond serveur par défaut (199) et BLOQUE la
                                                               # préparation ; le budget est un réglage légitime de l'exercice (--max-calls)
                                                               "settings": {"max_llm_calls": a.max_calls},
                                                               "title": f"Rising Waters {cc} — {label}"})["id"]
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
        if a.ai_mode == "ai":
            print("[8] Exercice « Modèle réel » PRÉPARÉ (modèle joignable, vérifié par la préparation). Il n'est PAS lancé par ce script : ouvrez-le "
                  "dans l'interface et cliquez « Lancer ». Rien n'a été généré par un modèle jusqu'ici.")
            print("Terminé. Ouvrez l'interface et collez le jeton propriétaire (écran /access).")
            return 0
        api.call("POST", f"/exercises/{ex}/commands", headers=fac, json={"kind": "start", "args": {}})
        t0 = time.time()
        while time.time() - t0 < 900:
            st = api.call("GET", f"/exercises/{ex}", headers=fac)["state"]
            if st in ("completed", "stopped", "failed", "interrupted"):
                break
            time.sleep(1)
        print(f"[8] Exercice SANS IA terminé : état = {st} ({int(time.time() - t0)} s). Aucun modèle de langage n'a été appelé.")
        api.call("POST", f"/exercises/{ex}/detect-gaps", headers=fac)
    print("Terminé. Ouvrez l'interface et collez le jeton propriétaire (écran /access).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
