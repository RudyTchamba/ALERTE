"""Export/import ZIP : aller-retour (hashs identiques), modes, open_publication, archives piégées, atomicité, empreintes."""
from __future__ import annotations

import io
import json
import stat
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.core.canonical_json import canonical_bytes
from app.core.errors import Unprocessable
from app.knowledge import archive, kbops
from app.knowledge import archive_format as af
from app.knowledge.embedders import FixtureEmbedder
from app.knowledge.models import Chunk, ChunkEmbedding, Document, KBExport, KBImport, KnowledgeBase
from tests.knowledge.conftest import LAW_FR, Env, make_pdf


def build_source(env: Env, ws: str, redistribution="allowed") -> str:
    kb = env.kb(ws, "SRC", languages=["fr"], description="Corpus de test")
    pdf = make_pdf(["<h2>Décret n° 5</h2><p>Article 1 - Texte du décret sur les alertes. " + "Contenu. " * 30 + "</p>"])
    env.add_doc(ws, kb, "decret.pdf", pdf, embed=True, title="Décret 5", code="DEC-5", redistribution=redistribution,
                license_spdx="CC0-1.0", jurisdiction="XX", reliability="official")
    env.add_doc(ws, kb, "loi.txt", LAW_FR.encode(), embed=True, title="Loi 12", code="LOI-12", redistribution=redistribution)
    env.add_doc(ws, kb, "reg.csv", b"a;b\n1;2\n3;4\n", embed=True, title="Registre", code="REG", redistribution=redistribution)
    return kb


def export(env: Env, ws: str, kb: str, **req) -> bytes:
    req = {"mode": "full_reimportable", "include": {"embeddings": True}, **req}
    with env.session() as s:
        ex = KBExport(workspace_id=ws, kb_id=kb, mode=req["mode"], options={k: v for k, v in req.items() if k != "mode"})
        s.add(ex)
        s.commit()
        eid = ex.id
    res = archive.run_export(env.rt, None, eid)
    return env.rt.blobs.read_bytes(res["blob_sha256"])


def do_import(env: Env, ws: str, data: bytes, confirm: bool = True, **opts):
    sha = env.rt.blobs.put_bytes(data)
    with env.session() as s:
        imp = KBImport(workspace_id=ws, blob_sha256=sha)
        s.add(imp)
        s.commit()
        iid = imp.id
    report = archive.validate_import(env.rt, None, iid)
    if not confirm or not report["ok"]:
        return report, None, iid
    return report, archive.confirm_import(env.rt, None, iid, {"mode": "new_kb", **opts}), iid


def manifest_of(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return json.loads(z.read("manifest.json"))


def files_map(data: bytes) -> dict[str, str]:
    return {f["path"]: f["sha256"] for f in manifest_of(data)["files"]}


def counts(env: Env) -> tuple[int, int, int]:
    with env.session() as s:
        return tuple(s.scalar(select(func.count()).select_from(m)) for m in (KnowledgeBase, Document, Chunk))


def test_roundtrip_between_two_installations_identical_hashes(tmp_path):
    a, b = Env(tmp_path / "a"), Env(tmp_path / "b")
    wa, wb = a.workspace(), b.workspace()
    kb = build_source(a, wa)
    data = export(a, wa, kb)
    m = manifest_of(data)
    assert m["format"] == "alerte-kb-archive" and m["format_version"] == "1.0.0" and m["embedding"]["included"] is True
    names = set(files_map(data))
    assert {"data/kb.json", "data/documents.jsonl", "data/chunks.jsonl", "bag-info.txt"} <= names
    assert sum(1 for n in names if n.startswith("data/sources/")) == 3 and any(n.endswith(".f32.npy") for n in names)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.read("manifest.sha256").split()[0].decode() == __import__("hashlib").sha256(z.read("manifest.json")).hexdigest()
        assert z.read("manifest.json") == canonical_bytes(json.loads(z.read("manifest.json")))
        blob = z.read("manifest.json").decode()
        assert str(tmp_path) not in blob and "/home/" not in blob and "\\\\" not in blob   # aucun chemin absolu
    report, result, _ = do_import(b, wb, data)
    assert report["ok"] and report["conflicts"]["kb"] is False and result["id_conflicts_remapped"] is False
    assert result["embeddings_reused"] == m["embedding"]["count"]
    kb2 = result["kb_id"]
    assert kb2 == kb                                                      # identifiants préservés sans conflit
    data2 = export(b, wb, kb2)
    f1, f2 = files_map(data), files_map(data2)
    for path in f1:
        if path != "bag-info.txt":
            assert f1[path] == f2[path], path                             # hashs identiques fichier par fichier
    # la KB importée est opérationnelle : recherche lexicale + vectorielle sans ré-ingestion
    with b.session() as s:
        sc = b.rt.ui_scope(s, wb, kb2)
    hits = b.rt.search.search(sc, "Article 33 opérateurs téléphonie", 3)
    assert hits and hits[0].article == "Article 33" and hits[0].signals["dense"] and not hits[0].signals["degraded"]


def test_same_installation_reimport_remaps_ids_and_is_idempotent(env):
    ws = env.workspace()
    kb = build_source(env, ws)
    data = export(env, ws, kb)
    report, result, iid = do_import(env, ws, data)
    assert report["ok"] and report["conflicts"]["kb"] and report["conflicts"]["chunks"] > 0
    assert result["id_conflicts_remapped"] and result["kb_id"] != kb and result["kb_code"] == "SRC-2"
    with env.session() as s:
        imp = s.get(KBImport, iid)
        assert imp.import_map["kb"] == {kb: result["kb_id"]} and len(imp.import_map["chunks"]) == result["chunks"]
        old = set(s.scalars(select(Chunk.text_sha256).where(Chunk.kb_id == kb)))
        new = set(s.scalars(select(Chunk.text_sha256).where(Chunk.kb_id == result["kb_id"])))
        assert old == new
    # même archive une seconde fois : refus avec lien vers la KB existante
    report2, result2, _ = do_import(env, ws, data)
    assert report2["ok"] is False and report2["already_imported"] == result["kb_id"] and result2 is None
    assert report2["errors"][0]["code"] == "kb.import.already_imported"


def test_new_version_mode_adds_versions_without_duplicates(env):
    ws = env.workspace()
    kb = build_source(env, ws)
    data = export(env, ws, kb)
    # archive d'un autre espace logique : même contenu → tous les documents sont des doublons (même SHA-256)
    env.add_doc(ws, kb, "nouveau.txt", b"Article 1 - Nouveau texte " + b"x " * 100, embed=True, title="Nouveau", code="NEW")
    _, result, _ = do_import(env, ws, data, mode="new_version", target_kb_id=kb)
    assert result["kb_id"] == kb and result["documents_skipped_duplicates"] == 3 and result["chunks"] == 0
    # une archive dont un document a un contenu différent crée une nouvelle version du MÊME document
    with env.session() as s:
        doc = s.scalar(select(Document).where(Document.kb_id == kb, Document.code == "LOI-12"))
        sha, size, _ = kbops.store_upload(env.rt, s, io.BytesIO((LAW_FR + "\nArticle 34 - Ajout.").encode()), "loi2.txt")
        v = kbops.add_version(s, ws, doc, sha, size, "loi2.txt", None)
        s.commit()
        vid = v.id
    from app.knowledge.ingest import ingest_version
    ingest_version(env.rt, None, vid, embed=True)
    data2 = export(env, ws, kb, document_ids=[doc.id], mode="selection")
    kb2 = env.kb(ws, "TARGET")
    # import dans une autre KB : le document n'existe pas → créé ; puis re-import de la v2 sur la KB cible → doublon sauté
    _, r1, _ = do_import(env, ws, data2, mode="new_version", target_kb_id=kb2)
    assert r1["documents"] == 1 and r1["chunks"] == 5


def test_modes_selection_processed_only_documents_only(env):
    ws = env.workspace()
    kb = build_source(env, ws)
    with env.session() as s:
        doc_id = s.scalar(select(Document.id).where(Document.kb_id == kb, Document.code == "LOI-12"))
    sel = export(env, ws, kb, mode="selection", document_ids=[doc_id])
    assert manifest_of(sel)["documents_summary"]["count"] == 1
    proc = export(env, ws, kb, mode="processed_only")
    assert not any(n.startswith("data/sources/") for n in files_map(proc)) and "data/chunks.jsonl" in files_map(proc)
    docs_only = export(env, ws, kb, mode="documents_only")
    names = files_map(docs_only)
    assert any(n.startswith("data/sources/") for n in names) and manifest_of(docs_only)["embedding"]["included"] is False
    with zipfile.ZipFile(io.BytesIO(docs_only)) as z:
        assert z.read("data/chunks.jsonl") == b""
    with pytest.raises(Unprocessable):
        export(env, ws, kb, mode="selection")
    # une archive « traité seulement » se réimporte (sans originaux)
    report, result, _ = do_import(env, ws, proc)
    assert report["ok"] and result["chunks"] > 0 and report["summary"]["sources"] == 0


def test_open_publication_excludes_or_refuses_restricted_and_unknown(env):
    ws = env.workspace()
    kb = env.kb(ws, "PUB")
    env.add_doc(ws, kb, "a.txt", ("Article 1 - Libre " + "a " * 100).encode(), title="Libre", code="FREE", redistribution="allowed", license_spdx="CC0-1.0")
    env.add_doc(ws, kb, "b.txt", ("Article 1 - Inconnu " + "b " * 100).encode(), title="Inconnu", code="UNK")           # défaut : unknown
    env.add_doc(ws, kb, "c.txt", ("Article 1 - Restreint " + "c " * 100).encode(), title="Restreint", code="RES", redistribution="restricted")
    data = export(env, ws, kb, mode="open_publication", include={})
    m = manifest_of(data)
    assert m["mode"] == "open_publication" and m["documents_summary"]["count"] == 1
    assert m["documents_summary"]["redistribution"] == {"allowed": 1} and any("UNK" in w and "RES" in w for w in m["warnings"])
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert "UNK" not in z.read("data/documents.jsonl").decode() and "Restreint" not in z.read("data/chunks.jsonl").decode()
    with env.session() as s:
        by_code = {d.code: d.id for d in s.scalars(select(Document).where(Document.kb_id == kb))}
    with env.session() as s:
        with pytest.raises(Unprocessable) as e:   # sélection explicite contenant un document restreint → échec avec la liste
            archive.plan_export(s, ws, kb, {"mode": "open_publication", "document_ids": [by_code["FREE"], by_code["RES"]]})
        assert e.value.code == "kb.export.restricted_documents"
        assert [d["code"] for d in e.value.details["documents"]] == ["RES"]
        with pytest.raises(Unprocessable) as e2:  # rien de redistribuable
            archive.plan_export(s, ws, kb, {"mode": "open_publication", "document_ids": [by_code["UNK"]]})
        assert e2.value.code == "kb.export.restricted_documents"
    # d'après le legacy, tout est « unknown » : l'export ouvert est vide donc refusé
    kb_unknown = env.kb(ws, "UNKNOWN-ONLY")
    env.add_doc(ws, kb_unknown, "d.txt", ("Article 1 - U " + "d " * 100).encode())
    with env.session() as s, pytest.raises(Unprocessable):
        archive.plan_export(s, ws, kb_unknown, {"mode": "open_publication"})


def test_embeddings_reused_only_when_fingerprint_identical(tmp_path):
    a = Env(tmp_path / "a")
    wa = a.workspace()
    kb = build_source(a, wa)
    data = export(a, wa, kb)
    other = Env(tmp_path / "other", embedder=FixtureEmbedder(32))      # empreinte différente (dimension)
    wo = other.workspace()
    report, result, _ = do_import(other, wo, data)
    assert report["summary"]["embeddings_reusable"] is False and any("à recalculer" in w for w in report["warnings"])
    assert result["embeddings_reused"] == 0 and result["embeddings_to_recompute"] is True
    with other.session() as s:
        assert s.scalar(select(func.count()).select_from(ChunkEmbedding)) == 0
        assert s.get(KnowledgeBase, result["kb_id"]).embedder_key is None
    # sans embeddings dans l'archive : rien à réutiliser, pas d'erreur
    plain = export(a, wa, kb, include={})
    assert manifest_of(plain)["embedding"]["included"] is False
    assert do_import(other, wo, plain)[1]["embeddings_reused"] == 0


# --------------------------------------------------------------------------- archives piégées
def zip_bytes(entries: list[tuple[str, bytes]], symlinks: set[str] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            zi = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = ((stat.S_IFLNK | 0o777) if name in (symlinks or set()) else (stat.S_IFREG | 0o644)) << 16
            z.writestr(zi, data)
    return buf.getvalue()


def rewrite(data: bytes, mutate) -> bytes:  # noqa: ANN001
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = [(i.filename, z.read(i)) for i in z.infolist()]
    return zip_bytes(mutate(entries))


@pytest.fixture
def good(env):
    ws = env.workspace()
    kb = build_source(env, ws)
    return env, ws, export(env, ws, kb, include={})


def assert_rejected(env, ws, data, code=None):
    before = counts(env)
    report, result, _ = do_import(env, ws, data)
    assert report["ok"] is False and result is None
    if code:
        assert report["errors"][0]["code"] == code, report
    assert counts(env) == before          # rejet TOTAL : rien n'est créé
    return report


def test_trap_zip_slip_absolute_backslash_and_whitelist(good):
    env, ws, data = good
    for evil in ("../evil.txt", "data/../../evil.txt", "/etc/passwd", "C:/Windows/x.txt", "data\\sources\\x.pdf",
                 "data/sources/../../x", "~/x", "script.sh", "data/other.json", "data/sources/a/b.txt"):
        rep = assert_rejected(env, ws, rewrite(data, lambda es, evil=evil: es + [(evil, b"x")]), "kb.import.integrity_failed")
        assert "chemin" in rep["errors"][0]["message"] or "traversée" in rep["errors"][0]["message"]


def test_trap_symlink_and_duplicate_entries(good):
    env, ws, data = good
    sym = rewrite(data, lambda es: es + [("data/sources/link.txt", b"/etc/passwd")])
    with zipfile.ZipFile(io.BytesIO(sym)) as z:
        entries = [(i.filename, z.read(i)) for i in z.infolist()]
    assert_rejected(env, ws, zip_bytes(entries, symlinks={"data/sources/link.txt"}), "kb.import.integrity_failed")
    assert_rejected(env, ws, rewrite(data, lambda es: es + [es[0]]), "kb.import.integrity_failed")


def test_trap_decompression_bomb_and_entry_limits(good, monkeypatch):
    env, ws, data = good
    bomb = rewrite(data, lambda es: es + [("data/sources/bomb.bin", b"\0" * (60 * 1024 * 1024))])
    assert len(bomb) < 2 * 1024 * 1024
    assert_rejected(env, ws, bomb, "kb.import.too_large")
    monkeypatch.setattr(af, "MAX_ENTRIES", 3)
    assert_rejected(env, ws, data, "kb.import.too_large")
    monkeypatch.setattr(af, "MAX_ENTRIES", 10_000)
    monkeypatch.setattr(af, "MAX_UNCOMPRESSED", 1000)
    assert_rejected(env, ws, data, "kb.import.too_large")


def test_trap_modified_hash_manifest_and_files(good):
    env, ws, data = good

    def edit_chunks(es):  # un chunk modifié : le hash du fichier ne correspond plus
        return [(n, d.replace(b"Article 33", b"Article 99") if n == "data/chunks.jsonl" else d) for n, d in es]
    assert_rejected(env, ws, rewrite(data, edit_chunks), "kb.import.integrity_failed")

    def edit_manifest(es):  # manifest altéré : manifest.sha256 ne correspond plus
        return [(n, d.replace(b'"mode":"full_reimportable"', b'"mode":"processed_only"') if n == "manifest.json" else d) for n, d in es]
    assert_rejected(env, ws, rewrite(data, edit_manifest), "kb.import.integrity_failed")

    def drop_file(es):
        return [(n, d) for n, d in es if n != "data/documents.jsonl"]
    assert_rejected(env, ws, rewrite(data, drop_file), "kb.import.integrity_failed")

    def rehash_but_lie_about_text(es):  # fichier ET manifest recalculés mais text_sha256 interne faux → rejeté quand même
        out = {n: d for n, d in es}
        lines = out["data/chunks.jsonl"].split(b"\n")
        rec = json.loads(lines[0])
        rec["text"] = rec["text"] + " injecté"
        lines[0] = canonical_bytes(rec)
        out["data/chunks.jsonl"] = b"\n".join(lines)
        m = json.loads(out["manifest.json"])
        for f in m["files"]:
            if f["path"] == "data/chunks.jsonl":
                f["sha256"] = __import__("hashlib").sha256(out["data/chunks.jsonl"]).hexdigest()
                f["bytes"] = len(out["data/chunks.jsonl"])
        out["manifest.json"] = canonical_bytes(m)
        out["manifest.sha256"] = (__import__("hashlib").sha256(out["manifest.json"]).hexdigest() + "  manifest.json\n").encode()
        return list(out.items())
    rep = assert_rejected(env, ws, rewrite(data, rehash_but_lie_about_text), "kb.import.integrity_failed")
    assert "text_sha256" in rep["errors"][0]["message"]
    assert_rejected(env, ws, b"ceci n'est pas un zip", "kb.import.integrity_failed")


def test_unsupported_format_version_rejected(good):
    env, ws, data = good

    def bump(es):
        out = dict(es)
        m = json.loads(out["manifest.json"])
        m["format_version"] = "2.0.0"
        out["manifest.json"] = canonical_bytes(m)
        out["manifest.sha256"] = (__import__("hashlib").sha256(out["manifest.json"]).hexdigest() + "  manifest.json\n").encode()
        return list(out.items())
    assert_rejected(env, ws, rewrite(data, bump), "kb.import.unsupported_version")


def test_confirm_is_atomic_on_failure(env, monkeypatch):
    ws = env.workspace()
    kb = build_source(env, ws)
    data = export(env, ws, kb)
    report, _, iid = do_import(env, ws, data, confirm=False)
    assert report["ok"]
    before = counts(env)

    def boom(*a, **k):
        raise RuntimeError("panne au milieu de l'import")
    monkeypatch.setattr(archive, "fts_insert", boom)
    with pytest.raises(RuntimeError):
        archive.confirm_import(env.rt, None, iid, {"mode": "new_kb"})
    assert counts(env) == before                                   # transaction annulée : aucune ligne créée
    with env.session() as s:
        assert s.get(KBImport, iid).status == "failed"


def test_archive_independent_of_chroma_and_contains_no_secret(env):
    ws = env.workspace()
    kb = build_source(env, ws)
    data = export(env, ws, kb)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        assert not any("chroma" in n.lower() or n.endswith((".sqlite", ".bin")) for n in names)
        text = b"".join(z.read(n) for n in names if n.endswith((".json", ".jsonl", ".txt")))
    for needle in (b"api_key", b"Bearer ", b"password", str(Path(env.settings.data_dir)).encode()):
        assert needle not in text
