"""Pipeline documentaire par les routes HTTP que l'interface appelle (TestClient) : import multiple, collisions, doublons, états,
historique, relance individuelle, construction par base, isolation, fichiers non enregistrés, droits.
Embeddings : FixtureEmbedder (SANS IA)."""
from __future__ import annotations

from sqlalchemy import text

from tests.knowledge.conftest import make_pdf
from tests.knowledge.test_api import API, mk_kb, upload, wait_job


def pdf(tag: str) -> bytes:
    return make_pdf([f"<h1>{tag}</h1><p>Article 1 - Disposition {tag}. " + f"Texte {tag}. " * 30 + "</p>"])


def kb_status(client, owner, kb):
    return client.get(f"{API}/knowledge-bases/{kb}/status", headers=owner).json()


def test_multi_import_ten_pdfs_with_collisions_duplicates_and_independent_failures(client, owner, app):
    kb = mk_kb(client, owner, "Cameroun")
    jobs, results = [], []
    files = [(f"doc{i}.pdf", pdf(f"N{i}")) for i in range(10)]
    files += [("doc0.pdf", pdf("AUTRE-CONTENU")),       # même nom, contenu différent : conservé, rien n'est écrasé
              ("copie.pdf", files[1][1]),               # contenu identique à doc1.pdf : doublon refusé (SHA-256)
              ("faux.pdf", b"pas un pdf"),              # invalide : refusé sans arrêter les autres
              ("AE-01_ITU_2031.pdf", pdf("NOMTROMPEUR"))]
    for name, data in files:
        r = upload(client, owner, kb, name, data)
        results.append((name, r.status_code, r.json()))
        if r.status_code == 202:
            jobs.append(r.json()["job"]["id"])
    codes = {n: (s, b.get("error", {}).get("code")) for n, s, b in results if s != 202}
    assert codes["copie.pdf"] == (409, "kb.document.duplicate") and codes["faux.pdf"][0] in (415, 422)
    assert sum(1 for _, s, _ in results if s == 202) == 12            # 10 + collision de nom + nom trompeur
    for j in jobs:
        jr = wait_job(client, owner, j, timeout=120)
        assert jr["status"] == "done", jr["error"]
    st = kb_status(client, owner, kb)
    assert st["documents"] == 12 and st["documents_by_state"].get("ready", 0) + st["documents_by_state"].get("needs_review", 0) == 12
    # stockage : un fichier par PDF directement dans le dossier de la base, aucun écrasement, aucun sous-dossier ni lien
    d = app.state.ctx.settings.sources_dir / "KB-CAMEROUN" if False else app.state.ctx.settings.sources_dir / st["scope_path"]
    names = sorted(p.name for p in d.iterdir())
    assert len(names) == 12 and all(p.is_file() and not p.is_symlink() for p in d.iterdir())
    assert "doc0.pdf" in names and any(n.startswith("doc0__") for n in names) and "AE-01_ITU_2031.pdf" in names
    docs = client.get(f"{API}/knowledge-bases/{kb}/documents", headers=owner, params={"limit": 50}).json()["items"]
    trompe = next(x for x in docs if x["version"]["original_name"] == "AE-01_ITU_2031.pdf")
    assert trompe["jurisdiction"] is None and trompe["doc_type"] is None and trompe["version"]["storage_path"].startswith(st["scope_path"] + "/")
    assert trompe["version"]["provenance"]["origin"] == "upload"


def test_states_history_individual_retry_and_build_scope_isolation(client, owner, app):
    cm, ae = mk_kb(client, owner, "Cameroun"), mk_kb(client, owner, "Emirats")
    for name, kb in (("a.pdf", ae), ("b.pdf", cm)):
        wait_job(client, owner, upload(client, owner, kb, name, pdf(name)).json()["job"]["id"], timeout=60)
    rt = app.state.ctx.services["knowledge"]

    def fp(kb):
        with rt.factory() as s:
            q = lambda sql: s.execute(text(sql), {"k": kb}).fetchall()  # noqa: E731
            return [q("select id, processing_state from document_version where kb_id=:k"), q("select id from chunk where kb_id=:k"),
                    q("select count(*) from chunk_fts where kb_id=:k"), q("select chunk_id from chunk_embedding e join chunk c on c.id=e.chunk_id where c.kb_id=:k")]
    # historique par document : états traversés dans l'ordre
    d = client.get(f"{API}/knowledge-bases/{ae}/documents", headers=owner).json()["items"][0]
    ev = client.get(f"{API}/documents/{d['id']}/versions/1/events", headers=owner).json()["events"]
    seq = [e["state"] for e in ev]
    assert seq[0] == "uploaded" and "extracting" in seq and "chunking" in seq and seq[-1] in ("ready", "needs_review")
    before_ae = fp(ae)
    # construction de CM seulement
    r = client.post(f"{API}/knowledge-bases/{cm}/build", headers=owner, json={"steps": ["embed", "index"]})
    assert r.status_code == 202 and wait_job(client, owner, r.json()["job"]["id"], timeout=120)["status"] == "done"
    assert fp(ae) == before_ae and fp(cm)[3]                                    # AE intact ; CM a ses vecteurs
    # étape inconnue / périmètre étranger : refusés
    assert client.post(f"{API}/knowledge-bases/{cm}/build", headers=owner, json={"steps": ["everything"]}).status_code == 422
    assert client.post(f"{API}/knowledge-bases/{'0' * 26}/build", headers=owner, json={}).status_code == 404
    # relance individuelle d'un document en échec : seul lui est retraité, sans doublon de chunks
    cm_doc = client.get(f"{API}/knowledge-bases/{cm}/documents", headers=owner).json()["items"][0]
    n_chunks = len(fp(cm)[1])
    with rt.factory() as s:
        s.execute(text("update document_version set processing_state='failed', status='failed', processing_error='simulé' where id=:i"), {"i": cm_doc["version"]["id"]})
        s.commit()
    assert kb_status(client, owner, cm)["general_status"] == "errors"
    r = client.post(f"{API}/documents/{cm_doc['id']}/versions/1/reprocess", headers=owner)
    assert r.status_code == 202 and wait_job(client, owner, r.json()["job"]["id"], timeout=120)["status"] == "done"
    assert len(fp(cm)[1]) == n_chunks and fp(ae) == before_ae
    listed = client.get(f"{API}/knowledge-bases/{cm}/documents", headers=owner, params={"state": "failed"}).json()["items"]
    assert listed == []
    chk = client.get(f"{API}/knowledge-bases/{cm}/check", headers=owner).json()
    assert {c["id"]: c["ok"] for c in chk["checks"]}["source_files_intact"] is True


def test_unregistered_files_can_be_adopted_and_untracked_names_stay_meaningless(client, owner, app):
    kb = mk_kb(client, owner, "Global")
    scope = kb_status(client, owner, kb)["scope_path"]
    d = app.state.ctx.settings.sources_dir / scope
    d.mkdir(parents=True, exist_ok=True)
    (d / "CM-77_nom_trompeur.pdf").write_bytes(pdf("ADOPTE"))
    un = client.get(f"{API}/knowledge-bases/{kb}/unregistered", headers=owner).json()
    assert [f["name"] for f in un["files"]] == ["CM-77_nom_trompeur.pdf"]
    r = client.post(f"{API}/knowledge-bases/{kb}/adopt", headers=owner, json={"files": [f"{scope}/CM-77_nom_trompeur.pdf", "../etc/passwd", f"{scope}/absent.pdf"]})
    assert r.status_code == 202
    out = r.json()["documents"]
    assert out[0].get("document_id") and out[1].get("error") and out[2].get("error")      # un refus n'arrête pas les autres
    for j in r.json()["jobs"]:
        assert wait_job(client, owner, j["id"], timeout=120)["status"] == "done"
    assert client.get(f"{API}/knowledge-bases/{kb}/unregistered", headers=owner).json()["files"] == []
    doc = client.get(f"{API}/knowledge-bases/{kb}/documents", headers=owner).json()["items"][0]
    assert doc["jurisdiction"] is None and doc["version"]["provenance"]["origin"] == "adopted"
    assert (d / "CM-77_nom_trompeur.pdf").is_file()                                       # ni déplacé ni copié
    assert len(list(d.iterdir())) == 1
