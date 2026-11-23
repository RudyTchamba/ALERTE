"""Ledger SHA-256 chaîné (ajout seul), ancres de tête et vérification (doc 10 §10.3).

hash(e) = SHA256( prev_hash || 0x0A || canonical_bytes(e) ), canonical_bytes = JSON canonique de
{exercise_id, seq, type, actor, seat_id, sim_time, real_time, visibility, payload}.
Le premier `prev_hash` (genèse) est SHA256("ALERTE-LEDGER-v1:" || exercise_id) ; l'empreinte du snapshot est liée
par le premier événement `SNAPSHOT`. Le hash est calculé sur les OCTETS CANONIQUES STOCKÉS, jamais recalculé depuis
d'autres colonnes (les colonnes sont des copies indexées, vérifiées contre ces octets).

Limite assumée : un administrateur qui contrôle la base, les fichiers d'ancre et une éventuelle clé de signature
peut réécrire le journal ; toute modification ou suppression de fin est détectable à partir de la dernière ancre
exportée ou publiée. On ne dit jamais « infalsifiable ».
"""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
from pathlib import Path
from typing import Any

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from ..core.canonical_json import canonical_bytes, sha256_hex
from ..core.db import utcnow
from .events import NON_DETERMINISTIC_KEYS, EventType, Visibility
from .models import LedgerAnchor, LedgerEvent

GENESIS_PREFIX = "ALERTE-LEDGER-v1:"
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def genesis_hash(exercise_id: str) -> str:
    return sha256_hex(GENESIS_PREFIX + exercise_id)


def _iso_now() -> str:
    return utcnow().isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _lock_for(exercise_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(exercise_id, threading.Lock())


def _hold_until_transaction_ends(session: Session, exercise_id: str) -> None:
    """Le verrou d'écriture d'un exercice est tenu jusqu'au commit/rollback de la transaction (seq sans trou)."""
    held: set[str] = session.info.setdefault("ledger_locks", set())
    if exercise_id in held:
        return
    lock = _lock_for(exercise_id)
    if not lock.acquire(timeout=30):  # évite un blocage mutuel avec le verrou d'écriture SQLite
        raise RuntimeError("verrou du ledger indisponible (transaction concurrente trop longue)")
    held.add(exercise_id)

    def _release(*_a: Any) -> None:
        if exercise_id in held:
            held.discard(exercise_id)
            try:
                lock.release()
            except RuntimeError:  # pragma: no cover - déjà libéré
                pass

    event.listen(session, "after_commit", _release, once=True)
    event.listen(session, "after_rollback", _release, once=True)


def event_core(exercise_id: str, seq: int, type_: str, actor: str, seat_id: str | None, sim_time: str | None,
               real_time: str, visibility: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {"exercise_id": exercise_id, "seq": seq, "type": type_, "actor": actor, "seat_id": seat_id,
            "sim_time": sim_time, "real_time": real_time, "visibility": visibility, "payload": payload}


def chain_hash(prev_hash: str, canonical: bytes) -> str:
    return sha256_hex(prev_hash.encode("ascii") + b"\n" + canonical)


class Ledger:
    """Écriture/lecture/vérification. Instancié avec le dossier des ancres (fichiers JSONL d'ajout seul)."""

    def __init__(self, anchors_dir: Path | None = None, signer: Any = None) -> None:
        self.anchors_dir = Path(anchors_dir) if anchors_dir else None
        self.signer = signer  # AnchorSigner (Ed25519) ou None

    # ------------------------------------------------------------------ écriture
    def append(self, session: Session, exercise_id: str, type: str, actor: str, payload: dict[str, Any], *,
               seat_id: str | None = None, sim_time: str | None = None, visibility: str = Visibility.AUDIT,
               real_time: str | None = None) -> int:
        """Ajoute un événement dans la transaction de l'appelant ; renvoie son `seq`."""
        if type not in EventType.ALL:
            raise ValueError(f"type d'événement inconnu : {type}")
        if visibility not in Visibility.ALL:
            raise ValueError(f"visibilité inconnue : {visibility}")
        if visibility == Visibility.SEAT and not seat_id:
            raise ValueError("visibilité 'seat' : seat_id requis")
        _hold_until_transaction_ends(session, exercise_id)
        last = session.execute(
            select(LedgerEvent.seq, LedgerEvent.hash).where(LedgerEvent.exercise_id == exercise_id)
            .order_by(LedgerEvent.seq.desc()).limit(1)).first()
        seq = 1 if last is None else last.seq + 1
        prev = genesis_hash(exercise_id) if last is None else last.hash
        rt = real_time or _iso_now()
        canon = canonical_bytes(event_core(exercise_id, seq, type, actor, seat_id, sim_time, rt, visibility, payload))
        session.add(LedgerEvent(exercise_id=exercise_id, seq=seq, type=type, actor=actor, seat_id=seat_id,
                                sim_time=sim_time, real_time=rt, visibility=visibility, payload=payload,
                                canonical=canon, prev_hash=prev, hash=chain_hash(prev, canon)))
        session.flush()
        return seq

    # ------------------------------------------------------------------ ancres
    def head(self, session: Session, exercise_id: str) -> tuple[int, str] | None:
        row = session.execute(select(LedgerEvent.seq, LedgerEvent.hash).where(LedgerEvent.exercise_id == exercise_id)
                              .order_by(LedgerEvent.seq.desc()).limit(1)).first()
        return None if row is None else (row.seq, row.hash)

    def write_anchor(self, session: Session, exercise_id: str, kind: str = "round_close") -> LedgerAnchor | None:
        head = self.head(session, exercise_id)
        if head is None:
            return None
        seq, h = head
        sig = self.signer.sign(exercise_id, seq, h) if self.signer else None
        anchor = LedgerAnchor(exercise_id=exercise_id, seq=seq, hash=h, kind=kind, signature=sig)
        session.add(anchor)
        session.flush()
        if self.anchors_dir:
            self.anchors_dir.mkdir(parents=True, exist_ok=True)
            line = json.dumps({"exercise_id": exercise_id, "seq": seq, "hash": h, "kind": kind, "signature": sig,
                               "at": _iso_now()}, ensure_ascii=False, sort_keys=True)
            with (self.anchors_dir / f"{exercise_id}.jsonl").open("a", encoding="utf-8", newline="\n") as fh:
                fh.write(line + "\n")
        return anchor

    def _file_anchors(self, exercise_id: str) -> list[dict[str, Any]]:
        if not self.anchors_dir:
            return []
        p = self.anchors_dir / f"{exercise_id}.jsonl"
        if not p.is_file():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    # ------------------------------------------------------------------ vérification
    def verify(self, session: Session, exercise_id: str) -> dict[str, Any]:
        """Renvoie {ok, checked, first_bad_seq, reason, anchor_mismatch, truncated_after_anchor, head_seq, head_hash}."""
        result: dict[str, Any] = {"ok": True, "checked": 0, "first_bad_seq": None, "reason": None,
                                  "anchor_mismatch": False, "truncated_after_anchor": False,
                                  "head_seq": None, "head_hash": None,
                                  "signatures_checked": 0, "signatures_ok": None, "signature_key_id": None}

        def bad(seq: int | None, reason: str) -> dict[str, Any]:
            if result["ok"]:
                result.update(ok=False, first_bad_seq=seq, reason=reason)
            return result

        prev = genesis_hash(exercise_id)
        expected_seq = 1
        by_seq: dict[int, str] = {}
        for ev in session.scalars(select(LedgerEvent).where(LedgerEvent.exercise_id == exercise_id)
                                  .order_by(LedgerEvent.seq)):
            result["checked"] += 1
            if ev.seq != expected_seq:
                bad(expected_seq, "trou ou doublon de séquence")
                expected_seq = ev.seq
            if ev.prev_hash != prev:
                bad(ev.seq, "chaîne rompue (prev_hash)")
            if chain_hash(ev.prev_hash, ev.canonical) != ev.hash:
                bad(ev.seq, "hash invalide (contenu canonique modifié)")
            recomputed = canonical_bytes(event_core(ev.exercise_id, ev.seq, ev.type, ev.actor, ev.seat_id, ev.sim_time,
                                                    ev.real_time, ev.visibility, ev.payload))
            if recomputed != ev.canonical:
                bad(ev.seq, "colonnes incohérentes avec les octets canoniques")
            by_seq[ev.seq] = ev.hash
            prev = ev.hash
            expected_seq = ev.seq + 1
            result["head_seq"], result["head_hash"] = ev.seq, ev.hash

        db_anchors = list(session.scalars(select(LedgerAnchor).where(LedgerAnchor.exercise_id == exercise_id)))
        anchors: list[tuple[int, str]] = [(a.seq, a.hash) for a in db_anchors]
        signed = [a for a in db_anchors if a.signature]
        if signed and self.signer is not None:
            result["signature_key_id"] = self.signer.key_id()
            result["signatures_checked"] = len(signed)
            result["signatures_ok"] = True
            for a in signed:
                if not self.signer.verify(exercise_id, a.seq, a.hash, a.signature):
                    result["signatures_ok"] = False
                    bad(a.seq, "signature d'ancre invalide (ancre modifiée ou clé différente)")
        anchors += [(a["seq"], a["hash"]) for a in self._file_anchors(exercise_id)]
        head_seq = result["head_seq"] or 0
        for seq, h in anchors:
            if seq > head_seq:
                result["truncated_after_anchor"] = True
                bad(head_seq + 1, "journal tronqué après la dernière ancre")
            elif by_seq.get(seq) != h:
                result["anchor_mismatch"] = True
                bad(seq, "ancre incompatible avec l'événement correspondant")
        return result

    # ------------------------------------------------------------------ lecture
    def read(self, session: Session, exercise_id: str, *, after_seq: int = 0, limit: int = 500,
             types: list[str] | None = None, visibilities: set[str] | None = None,
             seat_id: str | None = None) -> list[LedgerEvent]:
        """Lit des événements filtrés par visibilité ; `seat_id` ajoute les événements privés de ce siège."""
        q = select(LedgerEvent).where(LedgerEvent.exercise_id == exercise_id, LedgerEvent.seq > after_seq)
        if types:
            q = q.where(LedgerEvent.type.in_(types))
        if visibilities is not None:
            cond = LedgerEvent.visibility.in_(sorted(visibilities - {Visibility.SEAT}))
            if Visibility.SEAT in visibilities:
                cond = cond | ((LedgerEvent.visibility == Visibility.SEAT) &
                               (LedgerEvent.seat_id == seat_id if seat_id else LedgerEvent.seat_id.is_not(None)))
            q = q.where(cond)
        return list(session.scalars(q.order_by(LedgerEvent.seq).limit(limit)))

    def count(self, session: Session, exercise_id: str, type: str | None = None) -> int:
        q = select(func.count()).select_from(LedgerEvent).where(LedgerEvent.exercise_id == exercise_id)
        if type:
            q = q.where(LedgerEvent.type == type)
        return session.scalar(q) or 0

    # ------------------------------------------------------------------ rejeu
    def replay_digest(self, session: Session, exercise_id: str) -> str:
        """Empreinte de rejeu : chaîne sur la PROJECTION STABLE des événements. Deux exécutions du même
        snapshot avec la même cassette doivent produire la même empreinte (la tête de chaîne, elle, diffère)."""
        ordinals: dict[str, int] = {}
        digest = sha256_hex("ALERTE-REPLAY-v1")
        for ev in session.scalars(select(LedgerEvent).where(LedgerEvent.exercise_id == exercise_id)
                                  .order_by(LedgerEvent.seq)):
            proj = {"seq": ev.seq, "type": ev.type, "actor": _stable_value(ev.actor, ordinals),
                    "seat": _stable_value(ev.seat_id, ordinals), "sim_time": ev.sim_time,
                    "visibility": ev.visibility, "payload": _stable_payload(ev.payload, ordinals)}
            digest = sha256_hex(digest.encode("ascii") + b"\n" + canonical_bytes(proj))
        return digest


def _stable_value(value: Any, ordinals: dict[str, int]) -> Any:
    if isinstance(value, str) and _ULID.match(value):
        return f"#{ordinals.setdefault(value, len(ordinals) + 1)}"
    if isinstance(value, str):
        return _ULID_IN_TEXT.sub(lambda m: f"#{ordinals.setdefault(m.group(0), len(ordinals) + 1)}", value)
    return value


_ULID_IN_TEXT = re.compile(r"\b[0-9A-HJKMNP-TV-Z]{26}\b")


def _stable_payload(obj: Any, ordinals: dict[str, int]) -> Any:
    if isinstance(obj, dict):
        return {k: _stable_payload(v, ordinals) for k, v in obj.items() if k not in NON_DETERMINISTIC_KEYS}
    if isinstance(obj, list):
        return [_stable_payload(v, ordinals) for v in obj]
    return _stable_value(obj, ordinals)


def iso_to_datetime(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
