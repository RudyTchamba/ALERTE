"""Script de conversion du prototype, export/import par HTTP, progression des jobs, test avec un vrai serveur d'embeddings."""
from __future__ import annotations

import io
import json
import os
import runpy
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import select

from app.knowledge import archive_format as af
from app.knowledge.models import Chunk
from tests.knowledge.conftest import LAW_FR
from tests.knowledge.test_api import API, mk_kb, upload, wait_job

REPO = Path(__file__).resolve().parents[4]
LEGACY = REPO / "alerte" / "index"
SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "legacy_to_archive.py"


@pytest.mark.skipif(not (LEGACY / "chunks.jsonl").is_file(), reason="index du prototype absent")
def test_legacy_conversion_yields_valid_archives(tmp_path):
    mod = runpy.run_path(str(SCRIPT))
    assert mod["main"](["--out", str(tmp_path / "out")]) == 0
    archives = sorted((tmp_path / "out").glob("*.zip"))
    assert len(archives) >= 3
    total_docs = total_chunks = 0
    for z in archives:
        p = af.open_and_validate(z)                           # validation durcie complète
        total_docs += len(p.documents)
        total_chunks += len(p.chunks)
        assert all(d["redistribution"] == "unknown" and d["version"]["source_file"] is None for d in p.documents)
        assert p.manifest["mode"] == "processed_only" and p.manifest["embedding"]["included"] is False
        assert "/home/" not in json.dumps(p.documents)       # aucun chemin absolu du prototype
    assert (total_docs, total_chunks) == (45, 4235)
    # déterministe : relancer donne les mêmes identifiants de chunks
    mod["main"](["--out", str(tmp_path / "out2")])
    assert [af.open_and_validate(z).chunks[0]["id"] for z in sorted((tmp_path / "out2").glob("*.zip"))] == \
           [af.open_and_validate(z).chunks[0]["id"] for z in archives]
    single = tmp_path / "all.zip"
    assert mod["main"](["--out", str(single)]) == 0 and len(af.open_and_validate(single).documents) == 45


@pytest.mark.skipif(not (LEGACY / "chunks.jsonl").is_file(), reason="index du prototype absent")
def test_legacy_archive_imports_through_api_and_open_export_is_refused(client, owner, tmp_path):
    runpy.run_path(str(SCRIPT))["main"](["--out", str(tmp_path / "out")])
    data = (tmp_path / "out" / "alerte-kb-AE.zip").read_bytes()
    r = client.post(f"{API}/knowledge-bases/import", headers=owner, files={"file": ("ae.zip", data)})
    assert r.status_code == 202
    iid = r.json()["import"]["id"]
    assert wait_job(client, owner, r.json()["job"]["id"])["status"] == "done"
    imp = client.get(f"{API}/imports/{iid}", headers=owner).json()
    assert imp["status"] == "validated" and imp["report"]["summary"]["documents"] == 9
    assert any("redistribution inconnue" in w for w in imp["report"]["warnings"])
    c = client.post(f"{API}/imports/{iid}/confirm", headers=owner, json={})
    assert c.status_code == 202
    j = wait_job(client, owner, c.json()["job"]["id"])
    assert j["status"] == "done", j["error"]
    kb = j["result"]["kb_id"]
    assert client.get(f"{API}/knowledge-bases/{kb}", headers=owner).json()["overview"]["chunks"] == 239
    s = client.post(f"{API}/knowledge-bases/{kb}/search", headers=owner, json={"query": "personal data protection", "k": 3}).json()
    assert s["hits"] and s["degraded"] is True   # KB importée sans embeddings : recherche lexicale seule, signalée
    # droits inconnus partout → export ouvert refusé (liste fournie)
    e = client.post(f"{API}/knowledge-bases/{kb}/exports", headers=owner, json={"mode": "open_publication"})
    assert e.status_code == 422 and e.json()["error"]["code"] == "kb.export.restricted_documents"
    # confirmation avant validation / double confirmation refusées
    assert client.post(f"{API}/imports/{iid}/confirm", headers=owner, json={}).status_code == 409


def test_http_export_download_reimport_roundtrip(client, owner):
    kb = mk_kb(client, owner)
    for name, body in (("loi.txt", LAW_FR), ("autre.txt", "Article 1 - Autre texte sur les alertes. " + "mot " * 60)):
        r = upload(client, owner, kb, name, body.encode(), title=name, redistribution="allowed", license_spdx="CC0-1.0")
        wait_job(client, owner, r.json()["job"]["id"])
    ex = client.post(f"{API}/knowledge-bases/{kb}/exports", headers=owner,
                     json={"mode": "full_reimportable", "include": {"embeddings": True}})
    assert ex.status_code == 202
    assert wait_job(client, owner, ex.json()["job"]["id"])["status"] == "done"
    eid = ex.json()["export"]["id"]
    assert client.get(f"{API}/exports/{eid}", headers=owner).json()["status"] == "done"
    dl = client.get(f"{API}/exports/{eid}/download", headers=owner)
    assert dl.status_code == 200 and dl.headers["content-type"] == "application/zip" and "attachment" in dl.headers["content-disposition"]
    assert zipfile.ZipFile(io.BytesIO(dl.content)).testzip() is None
    # export ouvert : tous « allowed » → accepté
    op = client.post(f"{API}/knowledge-bases/{kb}/exports", headers=owner, json={"mode": "open_publication"})
    assert op.status_code == 202
    # autre espace : 404 sur l'export et le téléchargement
    other = {"Authorization": "Bearer " + client.post(f"{API}/workspaces", json={"name": "Autre"}, headers=owner).json()["owner_token"]}
    assert client.get(f"{API}/exports/{eid}/download", headers=other).status_code == 404
    assert client.post(f"{API}/knowledge-bases/import", headers=other, files={"file": ("x.zip", dl.content)}).status_code == 202
    # réimport dans le même espace (conflits d'identifiants → import_map)
    r = client.post(f"{API}/knowledge-bases/import", headers=owner, files={"file": ("a.zip", dl.content)})
    iid = r.json()["import"]["id"]
    wait_job(client, owner, r.json()["job"]["id"])
    c = client.post(f"{API}/imports/{iid}/confirm", headers=owner, json={"code": "COPIE"})
    j = wait_job(client, owner, c.json()["job"]["id"])
    assert j["status"] == "done" and j["result"]["id_conflicts_remapped"] is True and j["result"]["kb_code"] == "COPIE"
    assert j["result"]["embeddings_reused"] > 0                     # même empreinte (fixture) : vecteurs réutilisés
    assert client.get(f"{API}/imports/{iid}", headers=owner).json()["import_map"]["chunks"]
    # archive piégée par HTTP : rejetée en dry-run
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../evil.txt", b"x")
    r = client.post(f"{API}/knowledge-bases/import", headers=owner, files={"file": ("bad.zip", bad.getvalue())})
    wait_job(client, owner, r.json()["job"]["id"])
    rep = client.get(f"{API}/imports/{r.json()['import']['id']}", headers=owner).json()
    assert rep["status"] == "rejected" and rep["report"]["errors"][0]["code"] == "kb.import.integrity_failed"
    assert client.post(f"{API}/imports/{r.json()['import']['id']}/confirm", headers=owner, json={}).status_code == 409


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[float | None, str | None]] = []

    def update(self, progress=None, message=None) -> None:  # noqa: ANN001
        self.events.append((progress, message))


def test_job_progress_is_monotone_and_reported(env):
    from app.knowledge import kbops
    from app.knowledge.ingest import ingest_version
    ws = env.workspace()
    kb = env.kb(ws)
    _, vid = env.add_doc(ws, kb, "loi.txt", ("\n".join(f"Article {i} - Texte {i} sur l'alerte." for i in range(1, 25))).encode(), ingest=False)
    rec = Recorder()
    res = ingest_version(env.rt, rec, vid, embed=True)
    ps = [p for p, _ in rec.events if p is not None]
    assert ps == sorted(ps) and ps[0] <= 0.1 and ps[-1] >= 0.95
    assert any(m and m.startswith("embeddings ") for _, m in rec.events) and res["embedding"]["embedded"] == res["chunks"]
    rec2 = Recorder()
    kbops.reindex_kb(env.rt, rec2, kb)
    assert [p for p, _ in rec2.events] == sorted(p for p, _ in rec2.events)


def test_interrupted_ingest_job_can_be_rerun(env):
    """Reprise : relancer l'ingestion d'une version non publiée repart proprement (pas de doublons de chunks)."""
    from app.knowledge.ingest import ingest_version
    ws = env.workspace()
    kb = env.kb(ws)
    _, vid = env.add_doc(ws, kb, "loi.txt", LAW_FR.encode(), embed=True)
    ingest_version(env.rt, None, vid, embed=True)
    with env.session() as s:
        chunks = s.scalars(select(Chunk).where(Chunk.document_version_id == vid)).all()
        assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    assert env.rt.readiness()["ok"] is True                           # FTS5 resynchronisé (aucun orphelin)


@pytest.mark.model
@pytest.mark.skipif(not os.environ.get("ALERTE_EMBED_BASE_URL"), reason="ALERTE_EMBED_BASE_URL non défini (test de modèle réel)")
def test_real_embedding_server_fr_ar_hybrid(tmp_path):
    from app.core.config import Settings
    from app.knowledge.embedders import build_embedder
    from tests.knowledge.conftest import Env
    st = Settings(data_dir=tmp_path)
    emb = build_embedder(st)
    assert emb.ensure_fingerprint().dimension > 0
    env = Env(tmp_path, embedder=emb)
    ws = env.workspace()
    kb = env.kb(ws)
    env.add_doc(ws, kb, "fr.txt", ("Article 1 - Les opérateurs de téléphonie mobile diffusent les alertes. " + "texte " * 50).encode(), embed=True)
    env.add_doc(ws, kb, "ar.txt", ("المادة 1: يجب على مشغلي الهاتف المحمول بث التنبيهات. " + "نص " * 50).encode(), embed=True)
    with env.session() as s:
        sc = env.rt.ui_scope(s, ws, kb)
    hits = env.rt.search.search(sc, "obligations des opérateurs mobiles pour la diffusion des alertes", 2)
    assert hits and hits[0].signals["dense"] and not hits[0].signals["degraded"]
