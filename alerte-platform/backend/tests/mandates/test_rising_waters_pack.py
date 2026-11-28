"""Le pack de démonstration doit être généré à partir de la NOUVELLE base de connaissances, jamais de l'ancien prototype."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from tests.mandates.conftest import API, mk_action, mk_inst

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "rising_waters_pack.py"


@pytest.fixture
def pack():
    spec = importlib.util.spec_from_file_location("rising_waters_pack", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _actions(pack, cc="CM") -> set[str]:
    data = json.loads((pack.CURATION / f"mandates.{cc}.json").read_text(encoding="utf-8"))
    return {m["action"] for m in data["mandates"]}


def test_cameroon_mandates_cite_only_documents_of_the_new_base(pack):
    data = pack.load_new_mandates("CM", _actions(pack))
    rows = pack.mandate_rows("CM", data)
    assert len(rows) == len(data["mandates"]) == 14
    cited = {c for r in rows for c in r["source_doc"].split("; ") if c}
    assert cited and cited <= pack.kb_document_codes()
    assert not [c for c in cited if "-S" in c]                    # jamais les anciens codes du prototype (CM-S01…)
    assert {r["evidence"] for r in rows} <= {"documented", "inferred", "assumed"}
    assert all(r["procedure"] == "" and r["dependency_ready"] == "" for r in rows)


def test_a_country_without_a_curated_registry_gets_nothing_instead_of_legacy_data(pack):
    assert pack.load_new_mandates("ZZ", set()) is None            # aucun registre de la nouvelle base : pas de repli sur l'ancien prototype


def test_unknown_source_or_action_stops_the_generation(pack, tmp_path, monkeypatch):
    cur = tmp_path / "curation"
    cur.mkdir()
    (cur / "documents.curation.json").write_text(json.dumps([{"code": "CM-01"}]), encoding="utf-8")
    base = {"institutions": [], "mandates": [{"ref": "L1", "institution": "DPC", "kind": "duty", "action": "act", "description": "d",
                                              "evidence_tag": "documented", "sources": [{"document": "CM-S01"}]}]}
    (cur / "mandates.XX.json").write_text(json.dumps(base), encoding="utf-8")
    monkeypatch.setattr(pack, "CURATION", cur)
    with pytest.raises(SystemExit, match="CM-S01"):                # source absente de la nouvelle base
        pack.load_new_mandates("XX", {"act"})
    base["mandates"][0]["sources"] = [{"document": "CM-01"}]
    (cur / "mandates.XX.json").write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(SystemExit, match="act_inconnue|catalogue"):
        pack.load_new_mandates("XX", {"autre"})                    # action absente du catalogue
    assert pack.load_new_mandates("XX", {"act"})["mandates"][0]["ref"] == "L1"


def test_import_keeps_the_new_source_code_the_quote_and_the_audit_note(pack, mclient, h):
    data = pack.load_new_mandates("CM", _actions(pack))
    rows = pack.mandate_rows("CM", data)[:1]
    mk_inst(mclient, h, rows[0]["institution"])
    mk_action(mclient, h, rows[0]["action"])
    import csv
    import io
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=pack.MANDATE_COLS, lineterminator="\n")
    wr.writeheader()
    wr.writerows(rows)
    rep = mclient.post(f"{API}/mandates/import-csv", json={"csv_text": buf.getvalue()}, headers=h).json()
    assert rep["created"] == 1 and rep["errors"] == []
    m = mclient.get(f"{API}/mandates", headers=h).json()[0]
    assert rows[0]["source_doc"] in m["notes"] and "citation :" in m["notes"] and "note d'audit :" in m["notes"]
    assert m["validation"] == "proposed" and m["sources"] == []


# --------------------------------------------------------------------------- fiches de comportement des agents
# identifiants des modes de panne du scénario (jamais dans un prompt, intégrité I2) ; les mots courants d'un rôle (« false alarms », « spoofed alerts »)
# restent dans la caractérisation historique du prototype (perspective), ils ne désignent aucun inject.
FAULT_HINTS = ("false_alarm", "over_trust", "missed_event", "privacy_breach", "data_leaves_country", "language_error", "spoofing", "fault_mode")


def test_every_cameroon_seat_has_its_own_specific_instructions_within_the_prompt_limit(pack):
    setup = pack.build_setup("CM")
    seats = {a["institution"] for a in setup["agents"]}
    assert seats == {"HYDRO", "MET", "DPC", "OPS", "ART", "MINSANTE", "DPA", "CTD", "ANTIC"}
    texts = {a["institution"]: a["instructions"] for a in setup["agents"]}
    assert all(t.strip() for t in texts.values()), "aucune instruction vide (MINSANTE, DPA, CTD et HYDRO l'étaient)"
    assert all(len(t) <= 1500 for t in texts.values()), "le prompt tronque `instructions` à 1 500 caractères"
    assert len(set(texts.values())) == len(texts)                      # jamais deux agents avec les mêmes consignes
    assert all(a["mission"].strip() for a in setup["agents"])


def test_briefs_name_real_contacts_and_carry_no_hint_about_the_expected_gaps(pack):
    setup = pack.build_setup("CM")
    codes = {a["institution"] for a in setup["agents"]}
    briefs = pack.load_agent_briefs("CM")
    for seat, b in briefs.items():
        for contact in b.get("contacts", []):
            assert contact.split(" ")[0] in codes, f"{seat} : contact inconnu {contact!r}"   # annuaire cohérent avec les sièges
    blob = " ".join(a["instructions"].lower() for a in setup["agents"])
    assert not [h for h in FAULT_HINTS if h in blob]                  # intégrité I2 : aucun indice de lacune dans les consignes


def test_hydro_is_the_ai_system_under_test_never_a_decision_maker(pack):
    setup = pack.build_setup("CM")
    hydro = next(a for a in setup["agents"] if a["institution"] == "HYDRO")
    assert hydro["role_kind"] == "ai_system" and "never activated" in hydro["instructions"].lower()
    assert next(i for i in setup["institutions"] if i["code"] == "HYDRO")["kind"] == "ai_system"
    antic = next(a for a in setup["agents"] if a["institution"] == "ANTIC")
    assert antic["role_kind"] == "institution"


def test_country_without_briefs_keeps_the_legacy_instructions(pack):
    assert pack.load_agent_briefs("AE") == {}


# --------------------------------------------------------------------------- registre des Émirats (NOUVELLE base, mandats PROPOSÉS)
def test_uae_mandates_cite_only_documents_of_the_new_base_and_keep_honest_evidence_levels(pack):
    data = pack.load_new_mandates("AE", _actions(pack, "AE"))
    rows = pack.mandate_rows("AE", data)
    assert len(rows) == len(data["mandates"]) >= 8
    cited = {c for r in rows for c in r["source_doc"].split("; ") if c}
    assert cited and not [c for c in cited if "-S" in c]              # jamais les anciens codes du prototype (AE-S02…)
    assert all(c.startswith("AE-") for c in cited)
    for m in data["mandates"]:
        if m["evidence_tag"] == "assumed":
            assert not m.get("sources")                              # une hypothèse n'est jamais présentée comme une disposition citée
        for s in m.get("sources") or []:
            assert s.get("quote") and len(s["quote"]) >= 20          # toute source porte une citation exacte (vérifiée contre le PDF hors test)
    assert {r["evidence"] for r in rows} <= {"documented", "inferred", "assumed"}
    assert all(r["institution"].startswith("AE-") for r in rows)     # codes d'institution préfixés comme dans setup-ae.json


def test_uae_registry_institutions_all_have_a_seat_in_the_generated_setup(pack):
    setup = pack.build_setup("AE", pack.load_new_mandates("AE", _actions(pack, "AE")))
    seats = {i["code"] for i in setup["institutions"] if i.get("seat", True)}
    data = pack.load_new_mandates("AE", _actions(pack, "AE"))
    assert {pack.pf("AE", m["institution"]) for m in data["mandates"]} <= seats
