#!/usr/bin/env python3
"""Génère le « pack Rising Waters » au format de la plateforme, à partir des données du prototype `alerte/data/` (lecture seule).

    python scripts/rising_waters_pack.py            # écrit ../demo/rising-waters/

Sorties (toutes FICTIVES : le système d'IA HydroSense et les chiffres des événements sont inventés) :

* `cm01-rising-waters.fr.alerte-scenario.yaml` / `.en.…` et `ae01-rising-waters-twin.fr|en.…` : scénarios importables par l'écran
  « Scénarios » → « Importer un YAML » (format `alerte-scenario`) ;
* `mandats-<pays>.csv` : registre de mandats issu de la NOUVELLE base de connaissances (`knowledge_bases/curation/mandates.<PAYS>.json`,
  sources = codes des documents reconstruits `CM-01`…, jamais les anciens `CM-S01`). Import CSV de l'écran « Pays et institutions »,
  colonne `institution` = code d'institution. **Aucun repli sur l'ancien prototype** : un pays sans registre curé n'a pas de fichier
  (le script le dit) et chaque source citée doit exister dans `knowledge_bases/curation/documents.curation.json` ;
* `setup-cm.json`, `setup-ae.json` : pays, institutions, catalogue d'actions et fiches d'agents (utilisés par `seed_rising_waters.py`) ;
* `lacunes-attendues.PRIVE.json` : les lacunes que l'auteur du scénario comptait révéler. **À ne jamais importer dans le scénario** :
  elles servent seulement à l'évaluation indépendante (mesure T3, fixtures scellées).

Le dossier `alerte/` du prototype ne sert plus QU'AUX scénarios (événements fictifs), aux rôles des sièges et au catalogue d'actions de
l'auteur du scénario : ce ne sont pas des connaissances documentaires.

Les étiquettes (`tags`) des événements sont dérivées des FAITS de l'événement (diffusion publique, dommage possible, sortie d'IA utilisée,
canal exposé, acteur étranger…) — jamais des lacunes attendues.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
def find_legacy() -> Path | None:
    """Dossier `alerte/` du prototype : variable ALERTE_LEGACY_DIR, sinon `alerte/` dans le dépôt, sinon `alerte/` à côté du dépôt."""
    repo = HERE.parent.parent.parent
    for c in (os.environ.get("ALERTE_LEGACY_DIR"), repo / "alerte", repo.parent / "alerte"):
        if c and (Path(c) / "data" / "scenarios").is_dir():
            return Path(c)
    return None


LEGACY = (find_legacy() or Path("alerte-introuvable")) / "data"
OUT = HERE.parent.parent / "demo" / "rising-waters"
CURATION = HERE.parent.parent / "knowledge_bases" / "curation"   # registre curé de la NOUVELLE base de connaissances
MANDATE_COLS = ["line_id", "country", "institution", "kind", "action", "description", "source_doc", "article", "procedure", "depends_on",
                "dependency_ready", "evidence", "assumed_by", "quote", "audit_note"]

FAULT_MAP = {"language_exclusion": "language_error", "data_abroad": "data_leaves_country", "": "none"}
KIND_MAP = {"MET": "agency", "DPC": "agency", "OPS": "operator", "ART": "regulator", "MINSANTE": "ministry", "DPA": "regulator",
            "CTD": "local_authority", "ANTIC": "agency", "HYDRO": "ai_system"}
PUBLIC_COMM = {"send_mass_alert", "decide_public_alert", "compel_operator_alert", "correct_false_alert",
               "public_communication_after_error", "multilingual_alerting", "reach_unconnected"}
AI_OUTPUT = {"validate_ai_forecast", "report_sensor_outage", "human_validate_ai_alert", "authorise_automatic_ai_alert"}
COUNTRY = {"CM": {"name": "Cameroun", "iso2": "CM", "languages": ["fr", "en"]},
           "AE": {"name": "Émirats arabes unis", "iso2": "AE", "languages": ["ar", "en"]}}


PREFIX = {"CM": "", "AE": "AE-"}  # les codes d'institution/agent sont UNIQUES par espace : le jumeau UAE porte un préfixe pour cohabiter avec le Cameroun


def pf(country: str, code: str) -> str:
    return PREFIX[country] + code


def derive_tags(e: dict) -> list[str]:
    acts, fm, tags = set(e["required_actions"]), e.get("failure_mode") or "", set()
    if e["severity"] >= 3:
        tags.add("life_risk")
        if e["act"] in (1, 2):
            tags.add("time_critical")
    if acts & PUBLIC_COMM:
        tags.add("public_communication")
    if "liability_alert_harm" in acts or fm in ("missed_event", "privacy_breach", "data_abroad"):
        tags.add("harm_possible")
    if acts & AI_OUTPUT or fm in ("false_alarm", "missed_event") and "HYDRO" in (e["sender"], *e["to"]):
        tags.add("ai_output_used_in_decision")
    if fm == "spoofing" or "block_spoofed_alert" in acts:
        tags.add("channel_abuse")
    if fm == "data_abroad" or "cross_border_agreement" in acts:
        tags.add("foreign_actor")
    if fm in ("privacy_breach", "data_abroad"):
        tags.add("rights_risk")
    return sorted(tags)


def title_of(e: dict, lang: str) -> str:
    txt = e["text"][lang].strip().split(". ")[0].rstrip(".")
    return f"{e['sim_time']} — {txt[:90]}"


def build_scenario(src: Path, country: str, lang: str, code: str, title: str) -> dict:
    s = yaml.safe_load(src.read_text(encoding="utf-8"))
    injects = []
    for e in s["events"]:
        item = {
            "seq": e["id"], "sim_time": e["sim_time"], "title": title_of(e, lang), "body": e["text"][lang].strip(),
            "from_actor": e["sender"], "fault_mode": FAULT_MAP.get(e.get("failure_mode") or "", e.get("failure_mode") or "none"),
            "recipients": [pf(country, r) for r in e["to"]], "tags": derive_tags(e),
            "demands": [{"action_code": a, "derivation": "scenario_author",
                         "justification": f"Exigence écrite par l'auteur du scénario pour l'événement {e['id']} (pas une obligation officielle)."}
                        for a in e["required_actions"]],
        }
        if "HYDRO" in e["to"]:
            item["system_output"] = {"source": "HydroSense (système d'IA FICTIF)", "statement": e["text"][lang].strip()}
        if e.get("realism_source"):
            item["source_note"] = "Inspiré de (références du prototype) : " + ", ".join(e["realism_source"])
        injects.append(item)
    return {"format": "alerte-scenario", "format_version": 1,
            "scenario": {"code": code, "title": title, "language": lang, "version": 1, "country": COUNTRY[country],
                         "description": (s.get("summary") or "").strip() + "  — " + (s.get("fictional_notice") or "")},
            "injects": injects}


def kb_document_codes() -> set[str]:
    """Codes des documents de la NOUVELLE base (curation lue dans les PDF reconstruits)."""
    return {d["code"] for d in json.loads((CURATION / "documents.curation.json").read_text(encoding="utf-8"))}


def load_new_mandates(country: str, action_codes: set[str]) -> dict | None:
    """Mandats d'un pays depuis la nouvelle base (`mandates.<PAYS>.json`) ; None si le pays n'a pas de registre curé.
    Échoue (sans rien écrire) si une source n'existe pas dans la base ou si une action n'est pas au catalogue."""
    f = CURATION / f"mandates.{country}.json"
    if not f.is_file():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    codes, problems = kb_document_codes(), []
    for m in data["mandates"]:
        for src in m.get("sources") or []:
            if src["document"] not in codes:
                problems.append(f"{m['ref']} : source {src['document']!r} absente de la nouvelle base")
        if m["action"] not in action_codes:
            problems.append(f"{m['ref']} : action {m['action']!r} absente du catalogue d'actions")
    if problems:
        sys.exit(f"{f.name} incohérent avec la nouvelle base :\n  " + "\n  ".join(problems))
    return data


def mandate_rows(country: str, data: dict) -> list[dict]:
    rows = []
    for m in data["mandates"]:
        srcs = m.get("sources") or []
        rows.append({"line_id": m["ref"], "country": country, "institution": pf(country, m["institution"]), "kind": m["kind"],
                     "action": m["action"], "description": m["description"],
                     "source_doc": "; ".join(dict.fromkeys(x["document"] for x in srcs)),
                     "article": "; ".join(x["article"] for x in srcs if x.get("article")), "procedure": "", "depends_on": "",
                     "dependency_ready": "", "evidence": m["evidence_tag"], "assumed_by": "",
                     "quote": " | ".join(x["quote"] for x in srcs if x.get("quote")), "audit_note": m.get("audit_note") or ""})
    return rows


def build_setup(country: str, mandates: dict | None = None) -> dict:
    roles = yaml.safe_load((LEGACY / "scenarios" / "roles" / f"{country.lower()}.yaml").read_text(encoding="utf-8"))["roles"]
    actions = yaml.safe_load((LEGACY / "mandates" / "actions.yaml").read_text(encoding="utf-8"))["actions"]
    insts, agents = [], []
    for r in roles:
        if r["code"] in ("COORD", "LEGAL"):
            continue  # le chef d'exercice (COORD) est du code déterministe et le conseiller juridique est l'outil `ask_legal` : ce ne sont pas des sièges
        insts.append({"code": pf(country, r["code"]), "name": r["name"], "kind": KIND_MAP.get(r["code"], "other")})
        instr = "\n".join(filter(None, [r.get("perspective"), "Priorités : " + " ; ".join(r.get("priorities") or []) if r.get("priorities") else "",
                                        "Ton : " + r["voice"] if r.get("voice") else ""]))
        agents.append({"institution": pf(country, r["code"]), "code": f"AG-{pf(country, r['code'])}", "name": f"Agent {pf(country, r['code'])}",
                       "role_kind": "ai_system" if r.get("kind") == "ai_system" else "institution",
                       "mission": r.get("mission", ""), "instructions": instr,
                       "kb_collections": [c for c in (r.get("kb_countries") or []) if c in ("CM", "AE", "INT")]})
    # institutions citées par les mandats de la NOUVELLE base mais qui ne tiennent PAS de siège (pas d'agent) ; aucune lecture des anciens registres
    extra: dict[str, tuple[str, str]] = {i["code"]: (i["name"], i["kind"]) for i in (mandates or {}).get("institutions", [])}
    used = {m["institution"] for m in mandates["mandates"]} if mandates else set()
    known = {i["code"] for i in insts}
    for code in sorted(used - {c[len(PREFIX[country]):] for c in known}):
        name, kind = extra.get(code, (code, "other"))
        insts.append({"code": pf(country, code), "name": name, "kind": kind, "seat": False})
    acts = [{"code": a["code"], "label": a.get("label_fr") or a["label"], "domain": a["category"], "derivation": "scenario_author",
             "justification": "Action exigée par le scénario Rising Waters (définie par l'auteur du scénario, pas par un texte officiel)."}
            for a in actions]
    return {"country": COUNTRY[country], "institutions": insts, "actions": acts, "agents": agents}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--legacy", default=None, help="dossier `alerte/` du prototype (défaut : ALERTE_LEGACY_DIR, ./alerte ou ../alerte)")
    args = ap.parse_args()
    global LEGACY
    if args.legacy:
        LEGACY = Path(args.legacy) / "data"
    if not (LEGACY / "scenarios").is_dir():
        sys.exit("dossier `alerte/data/scenarios` introuvable : indiquez --legacy <chemin du dossier alerte/> (ou ALERTE_LEGACY_DIR). "
                 "Le pack déjà généré reste dans demo/rising-waters/ et suffit pour suivre le guide.")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)  # les fichiers existants sont REMPLACÉS un à un (jamais supprimés avant génération)
    expected = {}
    action_codes = {a["code"] for a in build_setup("CM")["actions"]}
    for cc, stem, code, titles in (
            ("CM", "cm01_rising_waters", "CM-01", {"fr": "Rising Waters — Cameroun", "en": "Rising Waters — Cameroon"}),
            ("AE", "ae01_rising_waters_twin", "AE-01", {"fr": "Rising Waters — Émirats (jumeau)", "en": "Rising Waters — UAE twin"})):
        for lang in ("fr", "en"):
            if any(lang not in e["text"] for e in yaml.safe_load((LEGACY / "scenarios" / f"{stem}.yaml").read_text(encoding="utf-8"))["events"]):
                continue  # le prototype n'a pas écrit les événements dans cette langue : rien n'est inventé ni traduit automatiquement
            doc = build_scenario(LEGACY / "scenarios" / f"{stem}.yaml", cc, lang, code, titles[lang])
            name = f"{stem.replace('_', '-')}.{lang}.alerte-scenario.yaml"
            (out / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
        new_mandates = load_new_mandates(cc, action_codes)
        (out / f"setup-{cc.lower()}.json").write_text(json.dumps(build_setup(cc, new_mandates), ensure_ascii=False, indent=2), encoding="utf-8")
        target = out / f"mandats-{cc.lower()}.csv"
        if new_mandates is None:
            print(f"AVERTISSEMENT {cc} : aucun registre de mandats dans la nouvelle base (knowledge_bases/curation/mandates.{cc}.json) -> "
                  f"{target.name} NON généré (aucun repli sur l'ancien prototype).")
            if target.exists():
                print(f"  {target.name} est déjà présent : il date d'une génération précédente depuis l'ANCIEN prototype ; ne l'importez pas.")
        else:
            with target.open("w", encoding="utf-8", newline="") as fh:
                wr = csv.DictWriter(fh, fieldnames=MANDATE_COLS, lineterminator="\n")
                wr.writeheader()
                wr.writerows(mandate_rows(cc, new_mandates))
        s = yaml.safe_load((LEGACY / "scenarios" / f"{stem}.yaml").read_text(encoding="utf-8"))
        expected[code] = [{"seq": e["id"], "expected_gaps": e.get("expected_gaps") or []} for e in s["events"]]
    acts = build_setup("CM")["actions"]  # catalogue COMMUN aux deux pays (les codes d'action sont partagés)
    with (out / "actions.csv").open("w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["code", "label", "domain", "derivation", "justification", "reference_note"], lineterminator="\n")
        wr.writeheader()
        for a in acts:
            wr.writerow({**a, "reference_note": ""})
    (out / "lacunes-attendues.PRIVE.json").write_text(json.dumps(
        {"avertissement": "PRIVÉ : à ne JAMAIS importer dans un scénario ni montrer aux agents (évaluation T3 uniquement).", **expected},
        ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Pack Rising Waters (généré)\n\nGénéré par `backend/scripts/rising_waters_pack.py` : mandats depuis la NOUVELLE base (`knowledge_bases/curation/`), scénarios depuis `alerte/data/` (prototype, lecture seule).\n"
        "Toutes les situations sont **fictives**. Voir `docs/runbooks/guide-test-complet-interface.md`.\n\n"
        "| Fichier | Usage |\n|---|---|\n| `actions.csv` | **Catalogue d'actions : à importer EN PREMIER** (Pays et institutions → Registre des mandats → Catalogue d'actions → Importer un CSV) |\n| `*.alerte-scenario.yaml` | Scénarios (écran Scénarios → Importer un YAML) |\n"
        "| `mandats-*.csv` | Registre de mandats de la nouvelle base, sources `CM-xx` (Pays et institutions → Mandats → Importer un CSV) |\n"
        "| `setup-*.json` | Pays, institutions, actions et agents (script `seed_rising_waters.py`) |\n"
        "| `lacunes-attendues.PRIVE.json` | Lacunes visées par l'auteur ; **ne jamais importer dans le scénario** |\n", encoding="utf-8")
    print("pack écrit dans", out)
    for p in sorted(out.iterdir()):
        print(" ", p.name, p.stat().st_size, "octets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
