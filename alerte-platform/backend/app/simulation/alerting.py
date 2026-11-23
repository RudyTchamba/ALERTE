"""Alerte au public : ce que la population reçoit (ou ne reçoit pas) pendant l'exercice.

Une décision devient une alerte publique si elle est un acte (`outcome=act`) qui alerte la population
(code d'action d'alerte, ou libellé qui parle d'alerte, d'avertissement, d'évacuation ou de diffusion).
- `issued` : décision consignée avec une base légale vérifiée → diffusée au public, au format CAP 1.2
  (OASIS, repris par la Recommandation UIT-T X.1303), avec `status=Exercise`.
- `blocked` : base légale non vérifiée → l'alerte n'est PAS diffusée (garde-fou), mais on la montre à l'animateur.

Le délai d'alerte se mesure en temps simulé : du premier événement du scénario (le danger) à l'événement
auquel répond la première alerte diffusée.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.models import LedgerEvent
from ..core.auth import Principal
from .models import Decision, ExerciseSnapshot
from .service import exercise_guard, seat_rows

ALERT_CODES = frozenset({"issue_flood_warning", "broadcast_public_alert", "issue_warning", "public_alert", "evacuation_order"})
ALERT_RE = re.compile(r"(alert|avertiss|warning|avis de crue|[ée]vacu|broadcast|diffus)", re.IGNORECASE)
TERMINAL = ("completed", "stopped", "failed", "archived")
CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"
_SIM_DAY = re.compile(r"^\s*[JD]\s*(\d+)\s+(\d{1,2})[:h](\d{2})\s*$", re.IGNORECASE)
_SIM_HM = re.compile(r"^\s*(\d{1,2})[:h](\d{2})\s*$")


def sim_minutes(sim: str | None) -> int | None:
    """« J2 06:30 » → minutes depuis J1 00:00 ; « 06:30 » → minutes du jour ; sinon None."""
    if not sim:
        return None
    if m := _SIM_DAY.match(sim):
        return (int(m[1]) - 1) * 1440 + int(m[2]) * 60 + int(m[3])
    if m := _SIM_HM.match(sim):
        return int(m[1]) * 60 + int(m[2])
    return None


def is_alert(action: str | None, action_code: str | None, outcome: str | None) -> bool:
    if outcome != "act":
        return False
    if action_code and action_code in ALERT_CODES:
        return True
    return bool(ALERT_RE.search(f"{action_code or ''} {action or ''}"))


def cap_xml(*, identifier: str, sender: str, sent: str, sender_name: str, event: str, headline: str,
            description: str, instruction: str, area: str) -> str:
    ET.register_namespace("", CAP_NS)
    root = ET.Element(f"{{{CAP_NS}}}alert")

    def sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
        el = ET.SubElement(parent, f"{{{CAP_NS}}}{tag}")
        if text is not None:
            el.text = text
        return el

    for tag, text in (("identifier", identifier), ("sender", sender), ("sent", sent), ("status", "Exercise"),
                      ("msgType", "Alert"), ("scope", "Public")):
        sub(root, tag, text)
    info = sub(root, "info")
    for tag, text in (("language", "fr-FR"), ("category", "Met"), ("event", event), ("urgency", "Immediate"),
                      ("severity", "Severe"), ("certainty", "Likely"), ("senderName", sender_name),
                      ("headline", headline[:160]), ("description", description), ("instruction", instruction)):
        sub(info, tag, text)
    sub(sub(info, "area"), "areaDesc", area)
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _sent(real_time: str | None) -> str:
    """CAP exige « AAAA-MM-JJThh:mm:ss±hh:mm » (pas de « Z » ni de fractions)."""
    if not real_time:
        return "1970-01-01T00:00:00+00:00"
    base = real_time.split(".")[0].replace("Z", "")
    base = re.sub(r"[+-]\d{2}:\d{2}$", "", base)
    return f"{base}+00:00"


def public_alerts(session: Session, p: Principal, ex_id: str) -> dict[str, Any]:
    ex = exercise_guard(session, p, ex_id)
    snap = session.get(ExerciseSnapshot, ex.id)
    payload = snap.payload if snap else {}
    injects = (payload.get("scenario") or {}).get("injects") or []
    by_ref = {i.get("inject_ref"): i for i in injects}
    inst = {i["id"]: i for i in payload.get("institutions") or []}
    seats = {s.id: s for s in seat_rows(session, ex.id)}
    timed = [(sim_minutes(i.get("sim_time")), i) for i in injects]
    timed = [(m, i) for m, i in timed if m is not None]
    hazard_inj = min(timed, key=lambda x: x[0])[1] if timed else (injects[0] if injects else None)
    hazard_min = sim_minutes(hazard_inj.get("sim_time")) if hazard_inj else None
    area = (payload.get("scenario") or {}).get("title") or ex.title

    decisions = list(session.scalars(select(Decision).where(Decision.exercise_id == ex.id).order_by(Decision.ledger_seq)))
    seqs = [d.ledger_seq for d in decisions if d.ledger_seq is not None]
    real = dict(session.execute(select(LedgerEvent.seq, LedgerEvent.real_time).where(
        LedgerEvent.exercise_id == ex.id, LedgerEvent.seq.in_(seqs))).all()) if seqs else {}

    alerts = []
    for d in decisions:
        if not is_alert(d.action, d.action_code, d.outcome) or d.status == "not_recorded":
            continue
        seat = seats.get(d.seat_id)
        institution = inst.get(seat.institution_id) if seat else None
        inj = by_ref.get(d.inject_ref) or {}
        at = sim_minutes(inj.get("sim_time"))
        issued = d.status == "recorded"
        item = {
            "seq": d.ledger_seq, "seat": seat.code if seat else None,
            "institution": (institution or {}).get("name") or (seat.code if seat else ""),
            "action": d.action or d.action_code or "", "action_code": d.action_code,
            "status": "issued" if issued else "blocked", "author": d.author,
            "sim_time": inj.get("sim_time"), "inject_title": inj.get("title"),
            "delay_minutes": at - hazard_min if at is not None and hazard_min is not None else None,
            "real_time": real.get(d.ledger_seq),
        }
        if issued:
            item["cap_xml"] = cap_xml(
                identifier=f"ALERTE-{ex.code}-{d.ledger_seq}", sender=f"{item['seat'] or 'seat'}@alerte.exercise",
                sent=_sent(item["real_time"]), sender_name=item["institution"],
                event=inj.get("title") or "Alerte", headline=item["action"],
                description=inj.get("body") or item["action"],
                instruction=(d.rationale or item["action"])[:500], area=area)
        alerts.append(item)

    first = next((a for a in alerts if a["status"] == "issued"), None)
    if first:
        verdict = "alerted"
    elif ex.state in TERMINAL:
        verdict = "silent"
    else:
        verdict = "waiting" if ex.state in ("running", "paused", "interrupted") else "not_started"
    return {"exercise_id": ex.id, "code": ex.code, "title": ex.title, "state": ex.state,
            "hazard": {"sim_time": (hazard_inj or {}).get("sim_time"), "title": (hazard_inj or {}).get("title"),
                       "body": (hazard_inj or {}).get("body"), "area": area} if hazard_inj else None,
            "verdict": verdict, "first_alert": first, "alerts": alerts}
