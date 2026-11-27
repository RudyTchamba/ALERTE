"""COORD : règles déterministes en code (doc 08 §8.11). Aucune IA ; jamais de « conclusion » de lacune.

`evaluate` est PURE (données simples en entrée) : testable avec des décisions factices.
Signaux : R-ORPHAN, R-NOTOURROLE, R-OVERLAP, R-CONFLICT, R-NOBASIS, R-CITEFAIL, R-SILENT, R-AIFLAG.
Les décisions de repli (`author=fallback`) n'attestent d'aucun comportement d'institution : exclues.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Msg:
    msg_id: str
    from_seat: str
    to_seat: str
    msg_type: str
    body: str = ""
    in_reply_to: str | None = None
    reply_status: str | None = None
    round: int = 1


@dataclass(frozen=True)
class Dec:
    decision_id: str
    seat_code: str
    round: int = 1
    action_code: str | None = None
    outcome: str | None = None
    status: str = "recorded"
    author: str = "agent"
    gap_flags: tuple = ()


@dataclass
class Signal:
    signal: str
    rule: str
    action_code: str | None
    institutions: list[str]
    evidence: dict[str, Any] = field(default_factory=dict)
    seats: tuple[str, ...] = ()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def evaluate(*, inject: dict, seat_institution: dict[str, str], recipients: list[str], messages: list[Msg],
             decisions: list[Dec]) -> list[Signal]:
    """`seat_institution` : code de siège -> institution_id ; `recipients` : codes de sièges destinataires activables."""
    sigs: list[Signal] = []
    inst = lambda codes: sorted({seat_institution[c] for c in codes if c in seat_institution})  # noqa: E731
    real = [d for d in decisions if d.author != "fallback"]
    # Un siège peut décider PLUSIEURS fois sur un même inject (décision provisoire au tour 1, révisée après la réponse reçue) : pour les
    # règles de POSITION (chevauchement, conflit, absence de base, citation), seule sa DERNIÈRE décision porteuse d'une issue (ordre du
    # journal) fait foi ; sinon il serait en conflit avec lui-même et sa décision provisoire produirait de faux signaux. Les hypothèses
    # (gap_flags) levées dans n'importe laquelle de ses décisions restent comptées (`real`).
    latest: dict[str, Dec] = {}
    for d in real:
        if d.outcome is not None:
            latest[d.seat_code] = d
    positions = list(latest.values())
    demands = [d.get("action_code") for d in inject.get("demands", []) if d.get("action_code")]

    def infer_action(seat: str) -> str | None:
        own = [d.action_code for d in real if d.seat_code == seat and d.action_code]
        return own[-1] if own else (demands[0] if len(demands) == 1 else None)

    # R-ORPHAN / R-NOTOURROLE : demandes (REQUEST) groupées par (émetteur, texte) = une demande multi-destinataires
    groups: dict[tuple[str, str], list[Msg]] = {}
    for m in messages:
        if m.msg_type == "REQUEST":
            groups.setdefault((m.from_seat, _norm(m.body)), []).append(m)
    for (sender, _), reqs in groups.items():
        replies = {r.msg_id: [x for x in messages if x.in_reply_to == r.msg_id] for r in reqs}
        if any(x.reply_status == "accepted" for rs in replies.values() for x in rs):
            continue
        targets = [r.to_seat for r in reqs]
        ev = {"rule": "R-ORPHAN", "sender": sender, "recipients": targets, "request_ids": [r.msg_id for r in reqs]}
        if all(any(x.reply_status == "not_our_role" for x in replies[r.msg_id]) for r in reqs):
            ev["rule"] = "R-NOTOURROLE"
            sigs.append(Signal("NO_OWNER", "R-NOTOURROLE", infer_action(sender), inst([sender, *targets]), ev,
                               (sender, *targets)))
        else:
            sigs.append(Signal("ORPHAN_REQUEST", "R-ORPHAN", infer_action(sender), inst([sender, *targets]), ev,
                               (sender, *targets)))
    # R-OVERLAP : >= 2 sièges `act` sur la même action sans chef de file
    by_action: dict[str, list[Dec]] = {}
    for d in positions:
        if d.action_code:
            by_action.setdefault(d.action_code, []).append(d)
    for code, ds in by_action.items():
        claimers = sorted({d.seat_code for d in ds if d.outcome == "act"})
        if len(claimers) >= 2:
            lead = any((m.reply_status == "accepted" or m.msg_type == "DECISION") and m.from_seat in claimers
                       and m.to_seat in claimers and m.to_seat != m.from_seat for m in messages)
            if not lead:
                sigs.append(Signal("CLAIM_OVERLAP", "R-OVERLAP", code, inst(claimers),
                                   {"rule": "R-OVERLAP", "claimers": claimers}, tuple(claimers)))
    # R-CONFLICT : issues opposées (act vs decline) sur la même action
    for code, ds in by_action.items():
        acts = sorted({d.seat_code for d in ds if d.outcome == "act"})
        decl = sorted({d.seat_code for d in ds if d.outcome == "decline"})
        if acts and decl:
            sigs.append(Signal("CONFLICTING_DECISIONS", "R-CONFLICT", code, inst(acts + decl),
                               {"rule": "R-CONFLICT", "act": acts, "decline": decl}, tuple(acts + decl)))
    for d in positions:
        if d.outcome == "no_legal_basis_found":
            sigs.append(Signal("MISSING_BASIS", "R-NOBASIS", d.action_code, inst([d.seat_code]),
                               {"rule": "R-NOBASIS", "decision_id": d.decision_id, "seat": d.seat_code}, (d.seat_code,)))
        if d.status == "not_verified":
            sigs.append(Signal("UNSUPPORTED_DECISION", "R-CITEFAIL", d.action_code, inst([d.seat_code]),
                               {"rule": "R-CITEFAIL", "decision_id": d.decision_id, "seat": d.seat_code}, (d.seat_code,)))
    # R-SILENT : destinataire sans aucune ligne de décision
    have = {d.seat_code for d in decisions}
    for code in recipients:
        if code not in have:
            sigs.append(Signal("NO_RESPONSE", "R-SILENT", None, inst([code]),
                               {"rule": "R-SILENT", "seat": code}, (code,)))
    # R-AIFLAG : hypothèses d'agents (jamais un constat)
    for d in real:
        for f in d.gap_flags:
            sigs.append(Signal("AGENT_HYPOTHESIS", "R-AIFLAG", d.action_code, inst([d.seat_code]),
                               {"rule": "R-AIFLAG", "decision_id": d.decision_id, "seat": d.seat_code,
                                "hint": f.get("hint"), "text": f.get("text")}, (d.seat_code,)))
    for m in messages:
        if m.msg_type == "GAP_FLAG":
            sigs.append(Signal("AGENT_HYPOTHESIS", "R-AIFLAG", infer_action(m.from_seat), inst([m.from_seat]),
                               {"rule": "R-AIFLAG", "msg_id": m.msg_id, "seat": m.from_seat, "text": m.body},
                               (m.from_seat,)))
    return sigs
