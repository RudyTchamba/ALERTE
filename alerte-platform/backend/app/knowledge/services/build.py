"""Construction, vérification et état d'UNE base de connaissances — logique unique (API, jobs, CLI).

Règle d'isolation : toute opération prend un **périmètre explicite** (identifiant de base, ou pays/code résolu en UNE base) et ne
lit ni n'écrit que les documents, chunks, lignes FTS, vecteurs et versions de cette base. Sans périmètre : refus explicite.
Aucune construction globale n'existe.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.db import utcnow
from ...core.errors import NotFound
from ..models import (
    IN_FLIGHT_STATES,
    Chunk,
    ChunkEmbedding,
    Document,
    DocumentVersion,
    KBVersion,
    KnowledgeBase,
)
from . import pipeline as PL
from . import sources as S

log = logging.getLogger("alerte.knowledge.build")
DEFAULT_STEPS = ("process", "embed", "index")
ALL_STEPS = ("process", "embed", "index", "check")


def resolve_scope(session: Session, ws: str, *, country: str | None = None, kb_id: str | None = None) -> KnowledgeBase:
    """Une base, ou une erreur claire. Aucun périmètre ⇒ refus (jamais « toutes les bases »)."""
    if not country and not kb_id:
        raise S.SourceError("un périmètre explicite est obligatoire : indiquez un pays (--country CM) ou une base (--kb-id <ID>) ; "
                            "aucune construction globale n'est lancée", "build.scope_required")
    if kb_id:
        kb = session.get(KnowledgeBase, kb_id)
        if kb is None or kb.workspace_id != ws:
            raise NotFound("base de connaissances introuvable", code="kb.not_found")
        return kb
    code = (country or "").strip()
    from ...workspaces.models import Country
    cands = list(session.scalars(select(KnowledgeBase).where(KnowledgeBase.workspace_id == ws, KnowledgeBase.archived_at.is_(None))))
    iso = {c.id: (c.iso2 or "").upper() for c in session.scalars(select(Country).where(Country.workspace_id == ws))}
    hits = [k for k in cands if k.code.upper() == code.upper() or (k.country_id and iso.get(k.country_id) == code.upper())]
    if not hits:
        raise NotFound(f"aucune base pour le périmètre {code!r} (codes disponibles : {', '.join(sorted(k.code for k in cands)) or 'aucun'})",
                       code="build.scope_unknown")
    if len(hits) > 1:
        raise S.SourceError(f"périmètre ambigu : {code!r} correspond à plusieurs bases ({', '.join(k.code for k in hits)}) ; "
                            "utilisez --kb-id", "build.scope_ambiguous")
    return hits[0]


def kb_status(rt: Any, session: Session, kb: KnowledgeBase) -> dict:
    """État synthétique d'une base : documents par état, chunks, vecteurs, index, version active, dernière construction."""
    ws = kb.workspace_id
    states = PL.counts_by_state(session, kb.id)
    docs = session.scalar(select(func.count()).select_from(Document).where(Document.kb_id == kb.id, Document.workspace_id == ws)) or 0
    chunks = session.scalar(select(func.count()).select_from(Chunk).where(Chunk.kb_id == kb.id)) or 0
    emb = 0
    if kb.embedder_key:
        emb = session.scalar(select(func.count()).select_from(ChunkEmbedding).join(Chunk, Chunk.id == ChunkEmbedding.chunk_id)
                             .where(Chunk.kb_id == kb.id, ChunkEmbedding.embedder_key == kb.embedder_key)) or 0
    from sqlalchemy import text
    fts = session.execute(text("SELECT count(*) FROM chunk_fts WHERE kb_id = :k"), {"k": kb.id}).scalar() or 0
    last = session.scalar(select(KBVersion).where(KBVersion.kb_id == kb.id).order_by(KBVersion.version_no.desc()).limit(1))
    failed = states.get("failed", 0)
    waiting = sum(states.get(x, 0) for x in ("uploaded", "queued"))
    running = sum(states.get(x, 0) for x in IN_FLIGHT_STATES) - waiting
    ready = states.get("ready", 0) + states.get("needs_review", 0)
    if docs == 0:
        general = "empty"
    elif failed:
        general = "errors"
    elif waiting or running:
        general = "pending"
    elif chunks and emb < chunks:
        general = "lexical_only" if not emb else "vectors_incomplete"
    else:
        general = "ready"
    return {
        "kb_id": kb.id, "code": kb.code, "name": kb.name, "scope_kind": kb.scope_kind, "scope_path": PL.kb_scope(kb),
        "country_id": kb.country_id, "documents": docs, "documents_by_state": states,
        "documents_ready": ready, "documents_waiting": waiting, "documents_running": running, "documents_failed": failed,
        "documents_needing_review": states.get("needs_review", 0), "chunks": chunks,
        "embeddings": {"embedded": emb, "chunks": chunks, "embedder_key": kb.embedder_key, "complete": bool(chunks) and emb == chunks},
        "lexical_index": {"rows": fts, "chunks": chunks, "complete": fts == chunks},
        "vector_index": {"status": ("complete" if chunks and emb == chunks else "incomplete" if emb else "absent")},
        "active_version": last.version_no if last else None, "last_build_at": last.created_at.isoformat() if last else None,
        "general_status": general,
    }


def check_coherence(rt: Any, session: Session, kb: KnowledgeBase, *, verify_files: bool = True) -> dict:
    """Cohérence documents ↔ fichiers ↔ chunks ↔ FTS ↔ vecteurs d'UNE base (aucune réparation, rapport seulement)."""
    checks: list[dict] = []

    def add(cid: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "ok": bool(ok), "detail": detail})

    vers = PL.latest_versions(session, kb.id)
    usable = [v for v in vers if v.processing_state in ("ready", "needs_review")]
    nochunk = [v.original_name for v in usable
               if not session.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_version_id == v.id))]
    add("documents_have_chunks", not nochunk, "tous les documents prêts ont des chunks" if not nochunk else f"sans chunk : {nochunk[:5]}")
    stuck = [v.original_name for v in vers if v.processing_state in IN_FLIGHT_STATES]
    add("no_stuck_processing", not stuck, "aucun document bloqué en cours de traitement" if not stuck else f"en cours/bloqués : {stuck[:5]}")
    st = kb_status(rt, session, kb)
    add("lexical_index_complete", st["lexical_index"]["complete"], f"FTS {st['lexical_index']['rows']}/{st['chunks']} chunks")
    ek = kb.embedder_key
    if ek:
        other = session.scalar(select(func.count()).select_from(ChunkEmbedding).join(Chunk, Chunk.id == ChunkEmbedding.chunk_id)
                               .where(Chunk.kb_id == kb.id, ChunkEmbedding.embedder_key != ek)) or 0
        add("embeddings_single_model", other == 0 or kb.embedder_fingerprint is not None,
            "un seul modèle d'embedding actif" if other == 0 else f"{other} vecteur(s) d'un ancien modèle conservé(s) (reembed en cours)")
        add("embeddings_complete", st["embeddings"]["complete"], f"vecteurs {st['embeddings']['embedded']}/{st['chunks']} ({ek})")
    else:
        add("embeddings_complete", False, "aucun embedding calculé : recherche lexicale seule (dégradée)")
    if verify_files:
        bad = []
        for v in vers:
            if v.processing_state == "retired":
                continue
            try:
                p = PL.original_path(rt, v)
            except Exception:  # noqa: BLE001
                bad.append(f"{v.original_name} (chemin invalide)")
                continue
            if not p.is_file():
                bad.append(f"{v.original_name} (fichier absent)")
            elif S.sha256_file(p) != v.blob_sha256:
                bad.append(f"{v.original_name} (SHA-256 différent)")
        add("source_files_intact", not bad, "fichiers sources présents et intègres" if not bad else f"à vérifier : {bad[:5]}")
    return {"kb_id": kb.id, "ok": all(c["ok"] for c in checks if c["id"] != "embeddings_complete") , "checks": checks, "status": st}


def build_kb(rt: Any, job: Any, kb_id: str, *, steps: tuple[str, ...] = DEFAULT_STEPS, reembed: bool = False,
             publish: bool = False, note: str | None = None) -> dict:
    """Construit UNE base : traite SES documents en attente (un par un, un échec n'arrête pas les autres), calcule SES embeddings
    manquants, met à jour SON index lexical, vérifie la cohérence, publie si demandé et si tout est prêt.

    Incrémental : seuls les documents en attente et les chunks sans vecteur sont traités. Les autres bases, et la dernière version
    publiée de celle-ci, ne sont jamais modifiées par cette opération."""
    from ..ingest import ingest_version
    from ..kbops import embed_kb, publish_kb, reindex_kb
    unknown = set(steps) - set(ALL_STEPS)
    if unknown:
        raise S.SourceError(f"étape inconnue : {sorted(unknown)} (valides : {', '.join(ALL_STEPS)})", "build.bad_step")
    report: dict[str, Any] = {"kb_id": kb_id, "steps": list(steps), "documents": [], "started_at": utcnow().isoformat(timespec="seconds")}

    def prog(p: float, msg: str) -> None:
        if job:
            job.update(p, msg)

    if "process" in steps:
        with rt.factory() as s:
            todo = [(v.id, v.original_name) for v in PL.pending_versions(s, kb_id)]
        for i, (vid, name) in enumerate(todo):
            prog(0.05 + 0.5 * i / max(1, len(todo)), f"traitement {i + 1}/{len(todo)} : {name}")
            try:
                with rt.factory() as s:
                    PL.set_state(s, vid, "queued", "traitement lancé par la construction de la base")
                    s.commit()
                r = ingest_version(rt, None, vid, embed=False)
                report["documents"].append({"version_id": vid, "name": name, "status": r["status"], "chunks": r["chunks"]})
            except Exception as exc:  # noqa: BLE001 - un document en échec n'arrête pas les autres
                with rt.factory() as s:
                    v = s.get(DocumentVersion, vid)
                    if v is not None and v.processing_state != "failed":
                        PL.set_state(s, vid, "failed", f"échec : {str(exc)[:300]}", error=str(exc)[:500])
                        s.commit()
                report["documents"].append({"version_id": vid, "name": name, "status": "failed", "error": str(exc)[:300]})
    if "embed" in steps:
        prog(0.6, "embeddings manquants")
        try:
            report["embedding"] = embed_kb(rt, None, kb_id, reembed=reembed)
        except Exception as exc:  # noqa: BLE001
            report["embedding_error"] = str(exc)[:300]
    if "index" in steps:
        prog(0.8, "index lexical")
        report["index"] = reindex_kb(rt, None, kb_id)
    with rt.factory() as s:
        kb = s.get(KnowledgeBase, kb_id)
        report["check"] = check_coherence(rt, s, kb)
        failed = [d for d in report["documents"] if d["status"] == "failed"]
        report["result"] = "partial" if failed or report.get("embedding_error") else "ok"
        if publish:
            if failed or not report["check"]["ok"]:
                report["published"] = None
                report["publish_refused"] = "des documents sont en échec ou la cohérence n'est pas validée : version précédente conservée"
            else:
                kv = publish_kb(s, kb.workspace_id, kb_id, note or "construction")
                s.commit()
                report["published"] = {"version_no": kv.version_no, "manifest_sha256": kv.manifest_sha256}
    prog(1.0, f"construction terminée ({report['result']})")
    return report
