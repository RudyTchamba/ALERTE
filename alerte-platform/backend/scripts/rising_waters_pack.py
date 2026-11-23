#!/usr/bin/env python3
"""Génère le « pack Rising Waters » au format de la plateforme, à partir des données du prototype `alerte/data/` (lecture seule).

    python scripts/rising_waters_pack.py            # écrit ../demo/rising-waters/

Sorties (toutes FICTIVES : le système d'IA HydroSense et les chiffres des événements sont inventés) :

* `cm01-rising-waters.fr.alerte-scenario.yaml` / `.en.…` et `ae01-rising-waters-twin.fr|en.…` : scénarios importables par l'écran
  « Scénarios » → « Importer un YAML » (format `alerte-scenario`) ;
* `mandats-cm.csv`, `mandats-ae.csv` : registres de mandats du prototype (import CSV de l'écran « Pays et institutions »,
  colonne `institution` = code d'institution) ;
* `setup-cm.json`, `setup-ae.json` : pays, institutions, catalogue d'actions et fiches d'agents (utilisés par `seed_rising_waters.py`) ;
* `lacunes-attendues.PRIVE.json` : les lacunes que l'auteur du scénario comptait révéler. **À ne jamais importer dans le scénario** :
  elles servent seulement à l'évaluation indépendante (mesure T3, fixtures scellées).

Les étiquettes (`tags`) des événements sont dérivées des FAITS de l'événement (diffusion publique, dommage possible, sortie d'IA utilisée,
canal exposé, acteur étranger…) — jamais des lacunes attendues.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent.parent.parent / "alerte" / "data"
OUT = HERE.parent.parent / "demo" / "rising-waters"

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


def build_setup(country: str) -> dict:
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
    # institutions citées par le registre de mandats mais qui ne tiennent PAS de siège (pas d'agent)
    extra = {"COORD": ("Conseil national de protection civile / comité de crise (le « chef d'exercice » du prototype n'est pas un siège)", "agency"),
             "ONR": ("Observatoire national des risques (ONR)", "agency"), "MOI": ("Ministère de l'Intérieur (MOI)", "ministry")}
    with (LEGACY / "mandates" / f"{country.lower()}_mandates.csv").open(encoding="utf-8") as fh:
        used = {row["institution"] for row in csv.DictReader(fh)}
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
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*"):
        old.unlink()
    expected = {}
    for cc, stem, code, titles in (
            ("CM", "cm01_rising_waters", "CM-01", {"fr": "Rising Waters — Cameroun", "en": "Rising Waters — Cameroon"}),
            ("AE", "ae01_rising_waters_twin", "AE-01", {"fr": "Rising Waters — Émirats (jumeau)", "en": "Rising Waters — UAE twin"})):
        for lang in ("fr", "en"):
            if any(lang not in e["text"] for e in yaml.safe_load((LEGACY / "scenarios" / f"{stem}.yaml").read_text(encoding="utf-8"))["events"]):
                continue  # le prototype n'a pas écrit les événements dans cette langue : rien n'est inventé ni traduit automatiquement
            doc = build_scenario(LEGACY / "scenarios" / f"{stem}.yaml", cc, lang, code, titles[lang])
            name = f"{stem.replace('_', '-')}.{lang}.alerte-scenario.yaml"
            (out / name).write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")
        (out / f"setup-{cc.lower()}.json").write_text(json.dumps(build_setup(cc), ensure_ascii=False, indent=2), encoding="utf-8")
        with (LEGACY / "mandates" / f"{cc.lower()}_mandates.csv").open(encoding="utf-8", newline="") as fh:
            rd = csv.DictReader(fh)
            rows = list(rd)
            cols = rd.fieldnames or []
        with (out / f"mandats-{cc.lower()}.csv").open("w", encoding="utf-8", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=cols)
            wr.writeheader()
            for row in rows:
                row["institution"] = pf(cc, row["institution"])
                wr.writerow(row)
        s = yaml.safe_load((LEGACY / "scenarios" / f"{stem}.yaml").read_text(encoding="utf-8"))
        expected[code] = [{"seq": e["id"], "expected_gaps": e.get("expected_gaps") or []} for e in s["events"]]
    (out / "lacunes-attendues.PRIVE.json").write_text(json.dumps(
        {"avertissement": "PRIVÉ : à ne JAMAIS importer dans un scénario ni montrer aux agents (évaluation T3 uniquement).", **expected},
        ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(
        "# Pack Rising Waters (généré)\n\nGénéré par `backend/scripts/rising_waters_pack.py` à partir de `alerte/data/` (prototype, lecture seule).\n"
        "Toutes les situations sont **fictives**. Voir `docs/runbooks/guide-test-complet-interface.md`.\n\n"
        "| Fichier | Usage |\n|---|---|\n| `*.alerte-scenario.yaml` | Scénarios (écran Scénarios → Importer un YAML) |\n"
        "| `mandats-*.csv` | Registre de mandats (Pays et institutions → Mandats → Importer un CSV) |\n"
        "| `setup-*.json` | Pays, institutions, actions et agents (script `seed_rising_waters.py`) |\n"
        "| `lacunes-attendues.PRIVE.json` | Lacunes visées par l'auteur ; **ne jamais importer dans le scénario** |\n", encoding="utf-8")
    print("pack écrit dans", out)
    for p in sorted(out.iterdir()):
        print(" ", p.name, p.stat().st_size, "octets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
