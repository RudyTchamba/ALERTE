"""États de traitement, historique, reprise et accès aux originaux — logique UNIQUE utilisée par l'API, les jobs et la CLI.

Chaque version de document (un PDF importé) a son propre état (`processing_state`), son historique (`document_event`) et peut
être relancée individuellement. L'ancien `status` (`processing|ready|needs_review|failed|retired`) est DÉRIVÉ de l'état détaillé :
il n'y a jamais deux vérités.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ...core.errors import Conflict, NotFound
from ..models import (
    IN_FLIGHT_STATES,
    LEGACY_STATUS,
    PROCESSING_STATES,
    DocumentEvent,
    DocumentVersion,
    KBVersionItem,
    KnowledgeBase,
)
from . import sources as S

log = logging.getLogger("alerte.knowledge.pipeline")

# Ordre normal d'un traitement réussi (affiché dans l'interface comme progression).
STEPS = ("uploaded", "queued", "extracting", "ocr_processing", "structuring", "chunking", "embedding", "indexing", "ready")


def kb_scope(kb: KnowledgeBase) -> str:
    """Dossier (relatif à `blobs/knowledge_sources`) du périmètre d'une base : `CM`, `GL` ou `organizations/ITU`."""
    return S.scope_relpath(kb.scope_kind, kb.code)


def original_path(rt: Any, version: DocumentVersion) -> Path:
    """Chemin du fichier original d'une version : emplacement de référence si connu, sinon ancien stockage par contenu
    (`blobs/<sha[:2]>/<sha>`, versions importées avant cette organisation ou depuis une archive)."""
    if version.storage_path:
        return S.resolve(rt.settings.sources_dir, version.storage_path)
    return rt.blobs.path_for(version.blob_sha256)


def original_exists(rt: Any, version: DocumentVersion) -> bool:
    try:
        return original_path(rt, version).is_file()
    except (ValueError, S.SourceError):
        return False


def set_state(session: Session, version: DocumentVersion | str, state: str, message: str | None = None, *,
              job_id: str | None = None, error: str | None = None) -> DocumentVersion:
    """Change l'état d'une version, dérive l'ancien `status`, journalise. `error` n'est conservé que pour `failed`."""
    if state not in PROCESSING_STATES:
        raise ValueError(f"état de traitement inconnu : {state}")
    v = session.get(DocumentVersion, version) if isinstance(version, str) else version
    if v is None:
        raise NotFound("version de document introuvable", code="kb.version.not_found")
    v.processing_state = state
    v.status = LEGACY_STATUS[state]
    v.processing_error = (error or message) if state == "failed" else None
    session.add(DocumentEvent(workspace_id=v.workspace_id, kb_id=v.kb_id, document_id=v.document_id, document_version_id=v.id,
                              state=state, message=(message or error or None) and (message or error)[:500], job_id=job_id))
    return v


def mark_queued(session: Session, version: DocumentVersion, job_id: str | None = None) -> None:
    set_state(session, version, "queued", "traitement en file d'attente", job_id=job_id)


def events(session: Session, version_id: str, limit: int = 200) -> list[dict]:
    rows = session.scalars(select(DocumentEvent).where(DocumentEvent.document_version_id == version_id)
                           .order_by(DocumentEvent.created_at, DocumentEvent.id).limit(limit)).all()
    return [{"state": e.state, "message": e.message, "job_id": e.job_id, "at": e.created_at.isoformat()} for e in rows]


def recover_interrupted(factory: sessionmaker[Session]) -> int:
    """À appeler au démarrage et par la CLI : une version restée dans un état « en cours » alors qu'aucun job ne tourne
    (arrêt du serveur, plantage) passe en `failed` avec un message explicite — elle pourra être relancée individuellement."""
    n = 0
    with factory() as s:
        for v in s.scalars(select(DocumentVersion).where(DocumentVersion.processing_state.in_(IN_FLIGHT_STATES))).all():
            set_state(s, v, "failed", "traitement interrompu par un arrêt du serveur : relancer le traitement",
                      error="traitement interrompu par un arrêt du serveur : relancer le traitement")
            n += 1
        s.commit()
    if n:
        log.warning("%s version(s) de document interrompue(s) marquée(s) failed (relançables)", n)
    return n


def is_published(session: Session, version_id: str) -> bool:
    return session.scalar(select(KBVersionItem.document_version_id).where(KBVersionItem.document_version_id == version_id)) is not None


def prepare_reprocess(session: Session, ws: str, version_id: str) -> DocumentVersion:
    """Contrôles avant une relance INDIVIDUELLE : version existante, non retirée, non publiée (immuable). Remet l'état à
    `queued` ; la ré-ingestion recrée proprement chunks/FTS/vecteurs de CETTE version (aucune duplication, autres documents intacts)."""
    v = session.get(DocumentVersion, version_id)
    if v is None or v.workspace_id != ws:
        raise NotFound("version de document introuvable", code="kb.version.not_found")
    if v.processing_state == "retired":
        raise Conflict("document retiré : rien à relancer", code="kb.reprocess.retired")
    if v.processing_state in IN_FLIGHT_STATES and v.processing_state not in ("uploaded", "queued"):  # en attente ≠ en cours
        raise Conflict("traitement déjà en cours", code="kb.reprocess.running")
    if is_published(session, v.id):
        raise Conflict("version publiée : immuable ; importez une nouvelle version du document", code="kb.reprocess.published")
    set_state(session, v, "queued", "relance demandée")
    return v


def latest_ids(kb_id: str):  # noqa: ANN202
    """Sous-requête : id de la DERNIÈRE version (numéro le plus élevé) de chaque document de la base. Un document importé mais pas
    encore traité n'a pas de `current_version_id` (posé en fin de traitement) : il doit pourtant être suivi, compté et traité."""
    last = (select(DocumentVersion.document_id.label("d"), func.max(DocumentVersion.version_no).label("n"))
            .where(DocumentVersion.kb_id == kb_id).group_by(DocumentVersion.document_id).subquery())
    return (select(DocumentVersion.id).join(last, (last.c.d == DocumentVersion.document_id) & (last.c.n == DocumentVersion.version_no))
            .where(DocumentVersion.kb_id == kb_id))


def latest_versions(session: Session, kb_id: str) -> list[DocumentVersion]:
    """Dernière version de chaque document d'UNE base (y compris les documents pas encore traités)."""
    return list(session.scalars(select(DocumentVersion).where(DocumentVersion.id.in_(latest_ids(kb_id)))
                                .order_by(DocumentVersion.created_at, DocumentVersion.id)))


def pending_versions(session: Session, kb_id: str) -> list[DocumentVersion]:
    """Dernières versions d'UNE base qui attendent un traitement (importées, en file, échouées, interrompues)."""
    return [v for v in latest_versions(session, kb_id) if v.processing_state in ("uploaded", "queued", "failed")]


def counts_by_state(session: Session, kb_id: str) -> dict[str, int]:
    out = {st: 0 for st in PROCESSING_STATES}
    for v in latest_versions(session, kb_id):
        out[v.processing_state] = out.get(v.processing_state, 0) + 1
    return {k: v for k, v in out.items() if v}


def latest_version(session: Session, doc_id: str) -> DocumentVersion | None:
    """Dernière version d'un document (celle que l'interface doit montrer : en cours, en échec ou prête)."""
    return session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
                          .order_by(DocumentVersion.version_no.desc()).limit(1))
