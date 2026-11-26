"""Pipeline documentaire de bout en bout via la CLI (`python -m app.cli`) et cohérence avec l'API.

Embeddings : FixtureEmbedder (déterministe, SANS IA) — ces tests vérifient la plomberie, l'isolation et la reprise, pas la pertinence.
PDF : générés localement (weasyprint) ; aucun nom de fichier n'a de sens pour le pipeline.
"""
from __future__ import annotations

import hashlib
import json

import pytest
from sqlalchemy import text

from app import cli
from app.core.config import get_settings
from tests.knowledge.conftest import LAW_FR, make_pdf


def pdf_of(tag: str) -> bytes:
    return make_pdf([f"<h1>{tag}</h1><p>Article 1 - Texte propre à {tag}. " + f"Contenu distinct {tag}. " * 25 + "</p>",
                     f"<p>Article 2 - Suite de {tag}. " + f"Obligation {tag}. " * 25 + "</p>"])


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("ALERTE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ALERTE_EMBED_PROVIDER", "fixture")
    monkeypatch.setenv("ALERTE_LOG_LEVEL", "WARNING")
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def run(*argv: str) -> int:
    return cli.main(list(argv))


def setup_kbs(home, *codes: str) -> None:
    assert run("workspace", "create", "--name", "T") == 0
    for c in codes:
        kind = "global_practices" if c == "GL" else "national"
        extra = ["--scope-kind", "organization"] if c == "ITU" else []
        assert run("knowledge", "kb-create", "--code", c, "--name", c, "--kind", kind, *extra) == 0


def put(home, folder: str, name: str, tag: str):
    p = home / "src" / folder / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pdf_of(tag))
    return p


def fp(home, code: str) -> dict:
    """Empreinte complète d'une base : documents, versions, chunks, FTS, vecteurs, fichiers — pour prouver qu'elle n'a pas bougé."""
    ctx = cli.make_ctx()
    try:
        with ctx.engine.connect() as c:
            kb = c.execute(text("select id from knowledge_base where code=:c"), {"c": code}).scalar()
            q = lambda sql: c.execute(text(sql), {"k": kb}).fetchall()  # noqa: E731
            out = {
                "documents": q("select id, code, current_version_id from document where kb_id=:k order by id"),
                "versions": q("select id, processing_state, status, storage_path from document_version where kb_id=:k order by id"),
                "chunks": q("select id, text_sha256 from chunk where kb_id=:k order by id"),
                "fts": q("select count(*) from chunk_fts where kb_id=:k"),
                "emb": q("select e.chunk_id, e.created_at from chunk_embedding e join chunk c on c.id=e.chunk_id where c.kb_id=:k order by 1"),
                "events": q("select count(*) from document_event where kb_id=:k"),
                "kb_versions": q("select id from kb_version where kb_id=:k"),
            }
        d = ctx.settings.sources_dir / code
        out["files"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.glob("*"))} if d.is_dir() else {}
        return out
    finally:
        ctx.engine.dispose()


def status(code: str) -> dict:
    ctx = cli.make_ctx()
    try:
        from app.knowledge.models import KnowledgeBase
        from app.knowledge.services import build as B
        with ctx.session_factory() as s:
            kb = s.query(KnowledgeBase).filter_by(code=code).one()
            return B.kb_status(ctx.services["knowledge"], s, kb)
    finally:
        ctx.engine.dispose()


# --------------------------------------------------------------------------------------------- périmètre obligatoire
def test_every_operation_refuses_without_scope(home, capsys):
    setup_kbs(home, "CM", "AE")
    for cmd in (["build"], ["status"], ["process"], ["embed"], ["index"], ["check"], ["retry"], ["publish"], ["sources-list"]):
        assert run("knowledge", *cmd) == cli.EXIT_REFUSED, cmd
    assert "aucune construction globale" in capsys.readouterr().err
    assert run("knowledge", "build", "--country", "ZZ") == cli.EXIT_REFUSED   # base inconnue : refus, pas de repli global


# --------------------------------------------------------------------------------------------- import, collisions, doublons
def test_import_many_collisions_duplicates_and_name_independence(home, capsys):
    setup_kbs(home, "CM", "AE")
    # un fichier nommé comme un autre pays/une organisation : le dossier est décidé par le PÉRIMÈTRE, jamais par le nom
    a = put(home, "a", "AE-01_ITU_Cameroun_2031.pdf", "A")
    b1 = put(home, "b", "decret.pdf", "B1")
    b2 = put(home, "c", "decret.pdf", "B2")           # même nom, autre contenu
    dup = put(home, "d", "copie.pdf", "B1")           # autre nom, MÊME contenu que b1
    junk = home / "src" / "junk.pdf"
    junk.write_bytes(b"ceci n'est pas un pdf")
    assert run("knowledge", "import", "--country", "CM", str(a), str(b1), str(b2), str(dup), str(junk), "--no-process") == 1
    out = capsys.readouterr().out
    assert "REFUSÉ      copie.pdf" in out and "kb.document.duplicate" in out
    assert "REFUSÉ      junk.pdf" in out
    d = get_settings().sources_dir / "CM"
    names = sorted(p.name for p in d.iterdir())
    assert len(names) == 3 and "AE-01_ITU_Cameroun_2031.pdf" in names and "decret.pdf" in names
    assert any(n.startswith("decret__") for n in names)            # collision : suffixe technique, aucun écrasement
    assert not (get_settings().sources_dir / "AE").exists()        # rien n'a atterri dans AE à cause d'un nom
    assert not [p for p in d.rglob("*") if p.is_dir() or p.is_symlink()]  # ni sous-dossier par PDF, ni lien
    st = status("CM")
    assert st["documents"] == 3 and st["documents_by_state"] == {"uploaded": 3}
    with cli.make_ctx().engine.connect() as c:
        jur = c.execute(text("select distinct jurisdiction from document")).fetchall()
    assert all(j[0] is None for j in jur)                          # rien de déduit du nom de fichier


# --------------------------------------------------------------------------------------------- construction isolée + incrémental
def test_build_one_base_leaves_the_other_untouched_and_is_incremental(home, capsys):
    setup_kbs(home, "CM", "AE")
    ae = [put(home, "ae", f"x{i}.pdf", f"AE{i}") for i in range(2)]
    cm = [put(home, "cm", f"y{i}.pdf", f"CM{i}") for i in range(2)]
    assert run("knowledge", "import", "--country", "AE", *map(str, ae)) == 0
    assert run("knowledge", "build", "--country", "AE") == 0
    before_ae = fp(home, "AE")
    assert before_ae["chunks"] and before_ae["emb"] and before_ae["fts"][0][0] == len(before_ae["chunks"])

    assert run("knowledge", "import", "--country", "CM", *map(str, cm), "--no-process") == 0
    assert run("knowledge", "build", "--country", "CM", "--steps", "process,embed,index") == 0
    assert fp(home, "AE") == before_ae                                # AE : strictement identique (docs, chunks, FTS, vecteurs, fichiers, événements)
    cm1 = fp(home, "CM")
    assert cm1["chunks"] and len(cm1["emb"]) == len(cm1["chunks"])
    assert status("CM")["general_status"] == "ready"

    # ajout d'UN seul PDF : seuls ses chunks sont calculés ; les vecteurs existants ne sont pas recalculés
    new = put(home, "cm", "z.pdf", "CM-NOUVEAU")
    assert run("knowledge", "import", "--country", "CM", str(new), "--no-process") == 0
    assert run("knowledge", "build", "--country", "CM") == 0
    cm2 = fp(home, "CM")
    assert set(cm1["emb"]) <= set(cm2["emb"]) and len(cm2["emb"]) > len(cm1["emb"])   # mêmes lignes (même date de calcul) + nouvelles
    assert {c[0] for c in cm1["chunks"]} <= {c[0] for c in cm2["chunks"]}
    assert fp(home, "AE") == before_ae
    capsys.readouterr()
    assert run("knowledge", "check", "--country", "CM") == 0


# --------------------------------------------------------------------------------------------- interruption et reprise
def test_interrupted_document_is_recovered_and_resumed_without_duplication(home, capsys):
    setup_kbs(home, "CM")
    p = put(home, "s", "doc.pdf", "REPRISE")
    assert run("knowledge", "import", "--country", "CM", str(p)) == 0
    n_chunks = fp(home, "CM")["chunks"]
    ctx = cli.make_ctx()
    with ctx.engine.begin() as c:   # simule un arrêt brutal en pleine extraction
        c.execute(text("update document_version set processing_state='extracting', status='processing'"))
    ctx.engine.dispose()
    assert status("CM")["documents_by_state"] == {"extracting": 1}
    assert run("knowledge", "check", "--country", "CM") == 1           # un document bloqué est signalé
    assert run("knowledge", "recover") == 0
    assert status("CM")["documents_by_state"] == {"failed": 1}
    assert run("knowledge", "retry", "--country", "CM") == 0
    after = fp(home, "CM")
    assert status("CM")["documents_by_state"] == {"ready": 1}
    assert [c[0] for c in after["chunks"]] and len(after["chunks"]) == len(n_chunks)   # reprise : pas de doublon de chunks
    states = [e[0] for e in json.loads(json.dumps([[r[0]] for r in
              cli.make_ctx().engine.connect().execute(text("select state from document_event order by created_at, id")).fetchall()]))]
    assert "failed" in states and states[-1] == "ready"                # historique conservé


# --------------------------------------------------------------------------------------------- migration, adoption, intégrité
def test_migrate_adopt_verify_with_provenance(home, capsys):
    setup_kbs(home, "CM", "ITU")
    src = home / "src" / "old" / "docs"
    f1 = put(home, "old/docs/CM", "CM-01_x.pdf", "M1")
    f2 = put(home, "old/docs/ITU", "T-REC-1.pdf", "ITU1")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob("*.pdf")}
    man = home / "manifest.jsonl"
    assert run("knowledge", "sources-migrate", "--map", f"CM={src / 'CM'}", "--map", f"organizations/ITU={src / 'ITU'}") == 0
    assert not get_settings().sources_dir.exists() or not list(get_settings().sources_dir.rglob("*.pdf"))   # simulation par défaut
    assert run("knowledge", "sources-migrate", "--map", f"CM={src / 'CM'}", "--map", f"organizations/ITU={src / 'ITU'}",
               "--apply", "--manifest", str(man)) == 0
    assert (get_settings().sources_dir / "organizations" / "ITU" / "T-REC-1.pdf").is_file()   # ITU = organisation, pas un pays
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in src.rglob("*.pdf")} == before and f1.exists() and f2.exists()
    assert run("knowledge", "adopt", "--country", "CM", "--manifest", str(man)) == 0
    assert run("knowledge", "adopt", "--country", "ITU", "--manifest", str(man)) == 0
    assert run("knowledge", "adopt", "--country", "CM") == 0          # rien de plus à adopter : idempotent
    assert status("CM")["documents"] == 1 and status("ITU")["documents"] == 1 and status("ITU")["scope_path"] == "organizations/ITU"
    ctx = cli.make_ctx()
    with ctx.engine.connect() as c:
        prov = json.loads(c.execute(text("select provenance from document_version where storage_path like 'CM/%'")).scalar())
    assert prov["origin"] == "adopted" and prov["source_kind"] == "legacy_project"
    ctx.engine.dispose()
    assert run("knowledge", "sources-verify", "--country", "CM") == 0
    (get_settings().sources_dir / "CM" / "CM-01_x.pdf").write_bytes(b"%PDF-1.4 modifie")   # modification manuelle
    assert run("knowledge", "sources-verify", "--country", "CM") == 1


# --------------------------------------------------------------------------------------------- CLI ⇄ API, isolation de la recherche
def test_cli_and_api_share_services_and_search_is_scoped(home, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app
    setup_kbs(home, "CM", "AE")
    for code, tag in (("CM", "ALPHA"), ("AE", "OMEGA")):
        assert run("knowledge", "import", "--country", code, str(put(home, code, f"{tag}.pdf", tag))) == 0
    assert run("knowledge", "build", "--country", "CM") == 0
    assert run("knowledge", "build", "--country", "AE") == 0
    with TestClient(create_app(get_settings())) as client:
        ctx = cli.make_ctx()
        from app.core.security import generate_token
        from app.workspaces.models import AccessToken, Workspace
        with ctx.session_factory() as s:
            ws = s.query(Workspace).filter(Workspace.name == "T").one()
            plain, h = generate_token("own")
            s.add(AccessToken(workspace_id=ws.id, role="owner", label="t", token_hash=h))
            s.commit()
        ctx.engine.dispose()
        hdr = {"Authorization": f"Bearer {plain}"}
        kbs = {k["code"]: k for k in client.get("/api/v1/knowledge-bases", headers=hdr).json()}
        for code in ("CM", "AE"):
            api = client.get(f"/api/v1/knowledge-bases/{kbs[code]['id']}/status", headers=hdr).json()
            cli_st = status(code)
            assert {k: api[k] for k in ("documents", "chunks", "documents_by_state", "general_status")} == \
                   {k: cli_st[k] for k in ("documents", "chunks", "documents_by_state", "general_status")}
        r = client.post(f"/api/v1/knowledge-bases/{kbs['CM']['id']}/search", headers=hdr, json={"query": "Contenu distinct OMEGA", "k": 10}).json()
        assert r["hits"] and all("OMEGA" not in h["text"] for h in r["hits"])      # AE n'apparaît jamais dans une recherche CM
        r = client.post(f"/api/v1/knowledge-bases/{kbs['AE']['id']}/search", headers=hdr, json={"query": "Contenu distinct ALPHA", "k": 10}).json()
        assert all("ALPHA" not in h["text"] for h in r["hits"])


def test_unused_fixture_text_is_available():
    assert "Article 1er" in LAW_FR


def test_curation_links_registry_to_pdf_by_sha256_not_by_filename(home, capsys):
    setup_kbs(home, "CM")
    src = home / "src" / "old" / "CM"
    put(home, "old/CM", "fichier-sans-sens.pdf", "REGISTRE")
    put(home, "old/CM", "CM-99_nom_trompeur.pdf", "AUTRE")   # son nom ressemble à un code de registre mais il n'est PAS cité
    man = home / "m.jsonl"
    assert run("knowledge", "sources-migrate", "--map", f"CM={src}", "--apply", "--manifest", str(man)) == 0
    assert run("knowledge", "adopt", "--country", "CM", "--manifest", str(man)) == 0
    reg = home / "registre.json"
    reg.write_text(json.dumps([
        {"code": "CM-01", "collection": "CM", "title": "Décret n° 1", "doc_type": "decree", "language": "fr", "doc_date": "2020-01-02",
         "reliability": "official", "validity": "unknown", "redistribution": "unknown", "original_path": "alerte/data/docs/CM/fichier-sans-sens.pdf"},
        {"code": "CM-02", "collection": "CM", "title": "Introuvable", "original_path": "alerte/data/docs/CM/absent.pdf"},
        {"code": "AE-01", "collection": "AE", "title": "Autre base", "original_path": "x/fichier-sans-sens.pdf"},
    ]), encoding="utf-8")
    assert run("knowledge", "curate", "--country", "CM", "--curation", str(reg), "--manifest", str(man)) == 1   # CM-02 : pas dans le manifeste
    assert "CM-02 (not_in_manifest)" in capsys.readouterr().out
    ctx = cli.make_ctx()
    with ctx.engine.connect() as c:
        rows = {r[0]: r for r in c.execute(text("select code, title, doc_type, jurisdiction, doc_date from document")).fetchall()}
    ctx.engine.dispose()
    assert rows["CM-01"][1:4] == ("Décret n° 1", "decree", "CM")          # appliqué au bon PDF (via SHA-256)
    other = [r for k, r in rows.items() if k != "CM-01"][0]
    assert other[1] == "CM-99_nom_trompeur" and other[2] is None          # l'autre PDF n'a RIEN reçu, malgré son nom


def test_failed_rebuild_keeps_the_last_published_version_and_refuses_to_publish(home, capsys):
    setup_kbs(home, "CM")
    assert run("knowledge", "import", "--country", "CM", str(put(home, "s", "ok.pdf", "STABLE"))) == 0
    assert run("knowledge", "build", "--country", "CM", "--publish", "--note", "v1") == 0
    v1 = fp(home, "CM")
    assert len(v1["kb_versions"]) == 1
    bad = put(home, "s", "bad.pdf", "FUTUR-ECHEC")
    assert run("knowledge", "import", "--country", "CM", str(bad), "--no-process") == 0
    stored = next(p for p in (get_settings().sources_dir / "CM").iterdir() if p.name == "bad.pdf")
    stored.write_bytes(b"%PDF-1.4 corrompu")   # le fichier source devient illisible après l'enregistrement
    capsys.readouterr()
    assert run("knowledge", "build", "--country", "CM", "--publish") == 1       # construction partielle : code de sortie non nul
    out = capsys.readouterr().out
    assert "publish_refused" in out and '"result": "partial"' in out
    after = fp(home, "CM")
    assert after["kb_versions"] == v1["kb_versions"]                             # aucune nouvelle version : la précédente reste active
    assert status("CM")["documents_by_state"] == {"ready": 1, "failed": 1} and status("CM")["active_version"] == 1
    # le document sain n'a pas bougé (chunks, vecteurs)
    assert {c[0] for c in v1["chunks"]} <= {c[0] for c in after["chunks"]} and set(v1["emb"]) <= set(after["emb"])


def test_failed_vectorization_is_reported_and_blocks_publication(home, monkeypatch, capsys):
    setup_kbs(home, "CM")
    assert run("knowledge", "import", "--country", "CM", str(put(home, "s", "a.pdf", "VEC"))) == 0
    monkeypatch.setenv("ALERTE_EMBED_PROVIDER", "openai_compat")      # aucun serveur configuré : la vectorisation échoue
    monkeypatch.setenv("ALERTE_EMBED_BASE_URL", "")                  # une chaîne vide l'emporte aussi sur un éventuel fichier .env
    monkeypatch.setenv("ALERTE_EMBED_MODEL", "")
    get_settings.cache_clear()
    capsys.readouterr()
    assert run("knowledge", "build", "--country", "CM", "--publish") == 1
    out = capsys.readouterr().out
    assert '"result": "partial"' in out and '"vectorization"' in out and '"status": "failed"' in out
    assert "publish_refused" in out and "vectorisation incomplète" in out
    assert status("CM")["active_version"] is None                      # rien n'a été publié
    assert run("knowledge", "publish", "--country", "CM") != 0         # la commande de publication directe est aussi refusée
    assert run("knowledge", "check", "--country", "CM") == 1           # et la vérification signale la base comme incomplète
