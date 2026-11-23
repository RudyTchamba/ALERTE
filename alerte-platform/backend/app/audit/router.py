"""Routes d'audit : lecture filtrée par visibilité, vérification du ledger, ancres, rejeu.

L'appartenance d'un exercice à l'espace du jeton est contrôlée par `ctx.services["exercise_guard"]`
(enregistré par le module simulation) : l'audit ne dépend que de core.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal, require_role
from ..core.context import AppContext, get_ctx, get_session
from ..core.errors import NotFound
from .events import Visibility
from .models import LedgerAnchor, LedgerEvent

router = APIRouter()


class LedgerEventOut(BaseModel):
    seq: int
    type: str
    actor: str
    seat_id: str | None
    sim_time: str | None
    real_time: str
    visibility: str
    payload: dict[str, Any]
    hash: str


class VerifyOut(BaseModel):
    ok: bool
    checked: int
    first_bad_seq: int | None
    reason: str | None
    anchor_mismatch: bool
    truncated_after_anchor: bool
    head_seq: int | None
    head_hash: str | None
    signatures_checked: int = 0
    signatures_ok: bool | None = None
    signature_key_id: str | None = None


def allowed_visibilities(p: Principal) -> set[str]:
    """Visibilités lisibles par rôle (filtre serveur — jamais côté client)."""
    if p.role in ("owner", "facilitator", "auditor"):
        return {Visibility.PUBLIC, Visibility.BOARD, Visibility.SEAT, Visibility.AUDIT}
    if p.role == "player":
        return {Visibility.PUBLIC, Visibility.BOARD, Visibility.SEAT}
    return {Visibility.PUBLIC}  # observer


def guard_exercise(ctx: AppContext, session: Session, p: Principal, exercise_id: str) -> None:
    guard = ctx.services.get("exercise_guard")
    if guard is None:
        raise NotFound("exercice introuvable")
    guard(session, p, exercise_id)  # lève NotFound/Forbidden si l'exercice n'appartient pas à l'espace/jeton


@router.get("/exercises/{exercise_id}/ledger", response_model=list[LedgerEventOut], tags=["audit"])
def read_ledger(exercise_id: str, after: int = 0, limit: int = Query(500, ge=1, le=5000), types: str | None = None,
                p: Principal = Depends(require_role("facilitator", "player", "observer", "auditor")),
                session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    guard_exercise(ctx, session, p, exercise_id)
    ledger = ctx.service("ledger")
    events = ledger.read(session, exercise_id, after_seq=after, limit=limit,
                         types=[t for t in (types or "").split(",") if t] or None,
                         visibilities=allowed_visibilities(p), seat_id=p.seat_id)
    return [LedgerEventOut(seq=e.seq, type=e.type, actor=e.actor, seat_id=e.seat_id, sim_time=e.sim_time,
                           real_time=e.real_time, visibility=e.visibility, payload=e.payload, hash=e.hash)
            for e in events]


@router.get("/exercises/{exercise_id}/ledger/verify", response_model=VerifyOut, tags=["audit"])
def verify_ledger(exercise_id: str, p: Principal = Depends(require_role("facilitator", "auditor")),
                  session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    guard_exercise(ctx, session, p, exercise_id)
    return VerifyOut(**ctx.service("ledger").verify(session, exercise_id))


@router.get("/exercises/{exercise_id}/anchors", tags=["audit"])
def list_anchors(exercise_id: str, p: Principal = Depends(require_role("facilitator", "auditor")),
                 session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    guard_exercise(ctx, session, p, exercise_id)
    rows = session.scalars(select(LedgerAnchor).where(LedgerAnchor.exercise_id == exercise_id)
                           .order_by(LedgerAnchor.seq))
    return [{"seq": a.seq, "hash": a.hash, "kind": a.kind, "signature": a.signature,
             "created_at": a.created_at.isoformat()} for a in rows]


@router.get("/ledger/public-key", tags=["audit"])
def public_key(ctx: AppContext = Depends(get_ctx)):
    """Clé publique Ed25519 de l'instance (PUBLIQUE, sans jeton) : vérification externe des ancres signées.
    Message signé : `ALERTE-ANCHOR-v1|<exercise_id>|<seq>|<hash>` ; signature en base64."""
    signer = getattr(ctx.service("ledger"), "signer", None)
    if signer is None:
        raise NotFound("aucune clé de signature configurée")
    return {"algorithm": "Ed25519", "key_id": signer.key_id(), "public_key_pem": signer.public_pem(),
            "message_format": "ALERTE-ANCHOR-v1|<exercise_id>|<seq>|<hash>"}


@router.get("/exercises/{exercise_id}/llm-calls/{seq}", tags=["audit"])
def llm_call_detail(exercise_id: str, seq: int, p: Principal = Depends(require_role("facilitator", "auditor")),
                    session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    """Prompt et réponse BRUTS d'un appel au modèle (blobs adressés par contenu), avec contrôle d'intégrité.
    Accès borné à l'exercice et aux rôles d'audit : jamais un blob arbitraire par son empreinte."""
    guard_exercise(ctx, session, p, exercise_id)
    ev = session.scalar(select(LedgerEvent).where(LedgerEvent.exercise_id == exercise_id, LedgerEvent.seq == seq,
                                                  LedgerEvent.type == "LLM_CALL"))
    if ev is None:
        raise NotFound("appel au modèle introuvable")
    out: dict[str, Any] = {"seq": ev.seq, "meta": {k: v for k, v in (ev.payload or {}).items()
                                                   if not k.endswith("_blob_sha256")}}
    import hashlib
    for part in ("request", "response"):
        sha = (ev.payload or {}).get(f"{part}_blob_sha256")
        item: dict[str, Any] = {"sha256": sha, "available": False, "intact": None, "content": None}
        if sha:
            try:
                path = ctx.blobs.path_for(sha)
                if path.is_file():
                    data = path.read_bytes()
                    item.update(available=True, intact=hashlib.sha256(data).hexdigest() == sha,
                                content=data[:200_000].decode("utf-8", errors="replace"))
            except ValueError:
                pass
        out[part] = item
    return out


@router.get("/exercises/{exercise_id}/replay-digest", tags=["audit"])
def replay_digest(exercise_id: str, p: Principal = Depends(require_role("facilitator", "auditor")),
                  session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    guard_exercise(ctx, session, p, exercise_id)
    ledger = ctx.service("ledger")
    return {"replay_digest": ledger.replay_digest(session, exercise_id),
            "events": ledger.count(session, exercise_id)}


@router.get("/exercises/{exercise_id}/ledger/export", tags=["audit"])
def export_ledger(exercise_id: str, p: Principal = Depends(require_role("facilitator", "auditor")),
                  session: Session = Depends(get_session), ctx: AppContext = Depends(get_ctx)):
    """JSONL avec empreintes, vérifiable hors ALERTE (scripts/verify_ledger.py)."""
    import json

    from fastapi.responses import PlainTextResponse

    guard_exercise(ctx, session, p, exercise_id)
    rows = session.scalars(select(LedgerEvent).where(LedgerEvent.exercise_id == exercise_id).order_by(LedgerEvent.seq))
    lines = [json.dumps({"seq": e.seq, "prev_hash": e.prev_hash, "hash": e.hash, "canonical": e.canonical.decode("utf-8")},
                        ensure_ascii=False) for e in rows]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="application/x-ndjson")
