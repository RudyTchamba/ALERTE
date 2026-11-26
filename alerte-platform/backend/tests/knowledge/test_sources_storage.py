"""Stockage physique par portée et migration non destructive des PDF sources."""
from __future__ import annotations

import hashlib
import json

import pytest

from app.knowledge.services import sources as S


def _pdf(path, body: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n" + body)
    return path


def _tree(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob("*")) if p.is_file()}


def test_scope_is_mandatory_and_validated():
    with pytest.raises(S.SourceError) as e:
        S.validate_scope(None)
    assert e.value.code == "sources.scope_required"
    for bad in ("", "C", "../CM", "CM/AE", "organizations", "organizations/../CM", "A" * 33, "CM AE"):
        with pytest.raises(S.SourceError):
            S.validate_scope(bad)
    assert S.validate_scope("CM") == "CM" and S.validate_scope("ITU") == "ITU" and S.validate_scope("organizations/ITU") == "organizations/ITU"
    assert S.scope_relpath("country", "CM") == "CM" and S.scope_relpath("global", "GL") == "GL"
    assert S.scope_relpath("organization", "ITU") == "organizations/ITU"   # une organisation n'est pas un pays


def test_dry_run_writes_nothing_and_source_is_never_touched(tmp_path):
    src, store = tmp_path / "old" / "x", tmp_path / "storage"
    _pdf(src / "a.pdf", b"AAA")
    before = _tree(tmp_path / "old")
    rep = S.migrate(store, [("CM", src, "legacy_project", "x")], dry_run=True)
    assert rep.counts() == {"copied": 1} and not store.exists() and _tree(tmp_path / "old") == before
    S.migrate(store, [("CM", src, "legacy_project", "x")], dry_run=False)
    assert _tree(tmp_path / "old") == before  # la source n'a ni bougé ni changé
    assert (store / "CM" / "a.pdf").read_bytes() == (src / "a.pdf").read_bytes()


def test_same_name_different_content_is_kept_with_technical_suffix(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    _pdf(a / "decret.pdf", b"CONTENU-1")
    _pdf(b / "decret.pdf", b"CONTENU-2")
    store = tmp_path / "storage"
    rep = S.migrate(store, [("CM", a, "legacy_project", None), ("CM", b, "platform_existing", None)], dry_run=False)
    names = sorted(p.name for p in (store / "CM").iterdir())
    assert len(names) == 2 and "decret.pdf" in names and any(n.startswith("decret__") for n in names)
    assert [i.decision for i in rep.items] == ["copied", "renamed_collision"]
    assert {i.migration_filename for i in rep.items} == {"decret.pdf"}  # le nom d'origine reste consigné


def test_same_content_is_never_copied_twice_even_with_another_name(tmp_path):
    a = tmp_path / "a"
    _pdf(a / "un.pdf", b"IDENTIQUE")
    _pdf(a / "deux.pdf", b"IDENTIQUE")
    store = tmp_path / "storage"
    rep = S.migrate(store, [("CM", a, "legacy_project", None)], dry_run=False)
    assert rep.counts() == {"copied": 1, "duplicate_skipped": 1} and len(list((store / "CM").iterdir())) == 1
    rep2 = S.migrate(store, [("CM", a, "legacy_project", None)], dry_run=False)   # relance : idempotente
    assert rep2.counts() == {"duplicate_skipped": 2} and len(list((store / "CM").iterdir())) == 1


def test_scope_comes_from_the_operator_never_from_the_file_name(tmp_path):
    src = tmp_path / "src"
    _pdf(src / "AE-99_Federal_Law_UAE.pdf", b"X")     # un nom qui « sonne » émirati, rangé par l'opérateur dans CM
    store = tmp_path / "storage"
    S.migrate(store, [("CM", src, "upload", None)], dry_run=False)
    assert (store / "CM" / "AE-99_Federal_Law_UAE.pdf").exists() and not (store / "AE").exists()


@pytest.mark.parametrize("name", ["rapport final (v2) #3.pdf", "ÉTUDE été 2024 — brouillon.PDF", "a" * 300 + ".pdf", "../../etc/passwd.pdf"])
def test_arbitrary_names_are_safe_and_kept_inside_the_scope_dir(tmp_path, name):
    safe = S.safe_physical_name(name)
    assert "/" not in safe and "\\" not in safe and ".." not in safe.split(".")[0:1] and len(safe) <= S.MAX_NAME
    assert safe.lower().endswith(".pdf")


def test_destination_inside_source_is_refused(tmp_path):
    src = tmp_path / "src"
    _pdf(src / "a.pdf", b"A")
    with pytest.raises(S.SourceError) as e:
        S.migrate(src / "storage", [("CM", src, "legacy_project", None)], dry_run=False)
    assert e.value.code == "sources.overlap"


def test_manifest_records_provenance_and_verify_detects_tampering(tmp_path):
    src, store = tmp_path / "src", tmp_path / "storage"
    _pdf(src / "a.pdf", b"AAA")
    rep = S.migrate(store, [("CM", src, "legacy_project", "dossier historique CM")], dry_run=False)
    man = tmp_path / "m.jsonl"
    S.write_manifest(man, rep)
    row = json.loads(man.read_text().splitlines()[0])
    assert row["source_kind"] == "legacy_project" and row["download_name"] is None and row["sha256"] and row["migrated_at"]
    expected = {it.destination: it.sha256 for it in rep.items}
    assert S.verify_scope(store, "CM", expected) == {"missing": [], "modified": [], "unknown": []}
    (store / "CM" / "a.pdf").write_bytes(b"%PDF-1.4\nALTERE")
    assert S.verify_scope(store, "CM", expected)["modified"] == ["CM/a.pdf"]


def test_stage_and_place_never_overwrite_and_stay_in_scope(tmp_path):
    import io
    root = tmp_path / "knowledge_sources"
    a = S.stage_stream(root, io.BytesIO(b"%PDF-1.4\nUN"))
    b = S.stage_stream(root, io.BytesIO(b"%PDF-1.4\nDEUX"))
    r1 = S.place(root, a, "CM", "même nom.pdf")
    r2 = S.place(root, b, "CM", "même nom.pdf")
    assert r1 == "CM/même nom.pdf" and r2.startswith("CM/même nom__") and r1 != r2
    assert (root / r1).read_bytes().endswith(b"UN") and (root / r2).read_bytes().endswith(b"DEUX")
    assert not list((root / ".incoming").iterdir())          # aucun résidu temporaire
    org = S.place(root, S.stage_stream(root, io.BytesIO(b"%PDF-1.4\nITU")), "organizations/ITU", "rec.pdf")
    assert org == "organizations/ITU/rec.pdf" and not (root / "ITU").exists()


def test_resolve_refuses_path_escape(tmp_path):
    root = tmp_path / "ks"
    root.mkdir()
    assert S.resolve(root, "CM/a.pdf") == (root / "CM" / "a.pdf").resolve()
    for bad in ("../x.pdf", "/etc/passwd", "CM/../../x"):
        with pytest.raises(S.SourceError):
            S.resolve(root, bad)
