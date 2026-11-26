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
    assert pack.load_new_mandates("AE", set()) is None            # pas de repli sur l'ancien prototype


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
