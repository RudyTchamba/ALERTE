"""Gap finder: ten simple, checkable rules over the story, the who-does-what map and the drill record.

A gap is kept only if a rule fires on the map, or the drill produced a signal
(a seat found no legal basis, a request went unanswered, decisions conflicted).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from alerte.analysis.precedents import find_precedents
from alerte.i18n import t
from alerte.knowledge.mandates import MandateMap
from alerte.knowledge.store import KnowledgeStore
from alerte.models import Decision, Gap, Message, Scenario
from alerte.sim.brain import action_label, mid

GAP_TYPES = {
    "G1": "Nobody in charge", "G2": "Two in charge", "G3": "No procedure", "G4": "Missing piece",
    "G5": "Conflicting goals", "G6": "Nobody answers for harm", "G7": "People left out",
    "G8": "AI unchecked", "G9": "Channel unprotected", "G10": "Cross-border",
}
GAP_TYPES_FR = {
    "G1": "Personne n'est compétent", "G2": "Deux compétents", "G3": "Pas de procédure", "G4": "Pièce manquante",
    "G5": "Objectifs contradictoires", "G6": "Personne ne répond des dommages", "G7": "Personnes laissées de côté",
    "G8": "IA non contrôlée", "G9": "Canal non protégé", "G10": "Transfrontalier",
}
# Category of the action -> gap type when nobody holds it, or when holders have no procedure
CATEGORY_GAP = {"liability": "G6", "inclusion": "G7", "ai_oversight": "G8", "security": "G9", "cross_border": "G10"}


@dataclass
class DrillSignals:
    no_basis: dict[str, list[str]] = field(default_factory=dict)      # action -> ["DPC@4", ...]
    unanswered: dict[str, list[str]] = field(default_factory=dict)    # action -> ["DPC->OPS@4", ...]
    double_claims: dict[str, list[str]] = field(default_factory=dict)  # action -> seats acting
    outside_role: dict[str, list[str]] = field(default_factory=dict)


def collect_signals(decisions: list[Decision], messages: list[Message]) -> DrillSignals:
    sig = DrillSignals()
    acting: dict[tuple[int, str], set[str]] = {}
    for d in decisions:
        if d.no_legal_basis and d.action:
            sig.no_basis.setdefault(d.action, []).append(f"{d.seat}@{d.event_id}")
        if d.action and not d.no_legal_basis and d.legal_basis:
            acting.setdefault((d.event_id, d.action), set()).add(d.seat)
        if d.outside_role and d.action:
            sig.outside_role.setdefault(d.action, []).append(f"{d.seat}@{d.event_id}")
    for (ev, action), seats in acting.items():
        if len(seats) > 1:
            sig.double_claims.setdefault(action, []).append(f"{'+'.join(sorted(seats))}@{ev}")
    replies = {m.in_reply_to: m for m in messages if m.type.value == "ANSWER"}
    for m in messages:
        if m.type.value == "REQUEST":
            r = replies.get(m.msg_id)
            if r is None or r.status in ("not_our_role", "refused"):
                why = "no answer" if r is None else r.status
                sig.unanswered.setdefault(m.action, []).append(f"{m.sender}->{m.recipient}@{m.event_id} ({why})")
    return sig


def action_gap_type(a, default: str | None = None) -> str | None:
    """Gap type raised when an action is uncovered: explicit override, else by category."""
    return a.gap_type or CATEGORY_GAP.get(a.category, default)


def find_gaps(scenario: Scenario, mm: MandateMap, store: KnowledgeStore, decisions: list[Decision],
              messages: list[Message], lang: str = "en") -> list[Gap]:
    country = scenario.country
    sig = collect_signals(decisions, messages)
    found: dict[tuple[str, str], Gap] = {}

    def texts_checked(action_code: str) -> list[str]:
        a = mm.action(action_code)
        hits = store.search(f"{a.label} {' '.join(a.keywords)}", 5, countries=[country],
                            doc_types=["law", "decree", "strategy", "plan", "report", "guidance", "standard"])
        return sorted({h.chunk.doc_id for h in hits})

    def add(gtype: str, action: str, title: str, desc: str, ev, evidence: list[str], institutions: list[str],
            confirmed: bool, signal: str):
        key = (gtype, action)
        g = found.get(key)
        if g is None:
            g = Gap(gap_id="", type=gtype, title=title, description=desc, action=action, institutions=sorted(set(institutions)),
                    event_ids=[], first_sim_time=ev.sim_time, severity=ev.severity,
                    confidence="confirmed_by_text" if confirmed else "suspected", texts_checked=texts_checked(action) if action else [])
            found[key] = g
        if ev.id not in g.event_ids:
            g.event_ids.append(ev.id)
        g.severity = max(g.severity, ev.severity)
        for e in evidence:
            if e not in g.evidence:
                g.evidence.append(e)
        if signal not in g.signals:
            g.signals.append(signal)
        g.institutions = sorted(set(g.institutions) | set(institutions))

    for ev in scenario.events:
        req = ev.required_actions
        for code in req:
            a = mm.action(code)
            label = action_label(a, lang)
            holders = mm.holders(code, country)
            cat_gap = action_gap_type(a)
            for other in a.conflicts_with:
                if other in req:
                    b = mm.action(other)
                    add("G5", code, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)['G5']}: {label}",
                        t("gap_conflict", lang, a=mid(label), b=mid(action_label(b, lang))), ev,
                        [f"Event {ev.id} requires both '{code}' and '{other}'"], list(ev.to),
                        confirmed=False, signal="rule:G5")
            if not holders:
                gtype = cat_gap or "G1"
                add(gtype, code, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)[gtype]}: {label}",
                    t("gap_no_holder", lang, label=mid(label)), ev,
                    [f"Who-does-what map ({country}): no institution holds '{code}'"], list(ev.to),
                    confirmed=True, signal=f"rule:{gtype}")
                continue
            insts = sorted({ln.institution for ln in holders})
            leads = [ln for ln in holders if ln.kind == "lead"]
            if len(insts) > 1 and not leads:
                add("G2", code, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)['G2']}: {label}",
                    t("gap_overlap", lang, label=mid(label)), ev,
                    [f"{ln.line_id}: {ln.institution} {ln.kind} ({ln.evidence})" for ln in holders], insts,
                    confirmed=all(ln.evidence == "documented" for ln in holders), signal="rule:G2")
            for ln in holders:
                if ln.dependency_ready in ("no", "unknown") and ln.depends_on:
                    add("G4", code, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)['G4']}: {label}",
                        t("gap_dependency", lang, label=mid(label), dep=ln.depends_on), ev,
                        [f"{ln.line_id}: depends on '{ln.depends_on}' (ready: {ln.dependency_ready})"], [ln.institution],
                        confirmed=ln.evidence == "documented" and ln.dependency_ready == "no", signal="rule:G4")
            if not any(ln.procedure for ln in holders):
                gtype = cat_gap if (a.gap_type or a.category in ("security", "ai_oversight", "inclusion", "liability")) else "G3"
                add(gtype, code, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)[gtype]}: {label}",
                    t("gap_no_proc", lang, label=mid(label)), ev,
                    [f"{ln.line_id}: {ln.institution} {ln.kind}, procedure: none found ({ln.evidence})" for ln in holders],
                    insts, confirmed=all(ln.evidence == "documented" for ln in holders), signal=f"rule:{gtype}")

    # Signals from the drill itself
    ev_by_id = {e.id: e for e in scenario.events}
    for action, refs in list(sig.no_basis.items()) + list(sig.unanswered.items()):
        evs = sorted({int(r.split("@")[1].split()[0]) for r in refs})
        existing = [g for (gt, ac), g in found.items() if ac == action]
        for g in existing:
            for r in refs:
                tag = f"drill:{r}"
                if tag not in g.evidence:
                    g.evidence.append(tag)
            if "agent" not in " ".join(g.signals):
                g.signals.append("agent/board signal")
        if not existing and evs:
            ev = ev_by_id[evs[0]]
            a = mm.action(action)
            add("G3", action, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)['G3']}: {action_label(a, lang)}",
                t("gap_no_proc", lang, label=mid(action_label(a, lang))), ev, [f"drill:{r}" for r in refs],
                [r.split("@")[0].split("->")[0] for r in refs], confirmed=False, signal="agent/board signal")
    for action, refs in sig.double_claims.items():
        ev = ev_by_id[int(refs[0].split("@")[1])]
        a = mm.action(action)
        add("G2", action, f"{(GAP_TYPES_FR if lang == 'fr' else GAP_TYPES)['G2']}: {action_label(a, lang)}",
            t("gap_overlap", lang, label=mid(action_label(a, lang))), ev, [f"drill: {r} both acted" for r in refs],
            [s for r in refs for s in r.split("@")[0].split("+")], confirmed=False, signal="board:double_claim")

    if scenario.gap_rules:   # a scenario profile may activate only some rules (core profile: G1,G2,G3,G6,G7,G8,G9)
        found = {k: g for k, g in found.items() if g.type in scenario.gap_rules}
    gaps = sorted(found.values(), key=lambda g: (-g.severity, g.event_ids[0], g.type))
    for i, g in enumerate(gaps, 1):
        g.gap_id = f"{g.type}-{i:02d}"
        g.status = "confirmed" if g.confidence == "confirmed_by_text" else "suspected"
        g.precedents = find_precedents(mm.action(g.action) if g.action else None, g.type, store, exclude_country=country)
    return gaps


def expected_gap_coverage(scenario: Scenario, gaps: list[Gap]) -> dict:
    """Test T3: share of the gaps the story was designed to reveal that the drill found."""
    found = {(e, g.type) for g in gaps for e in g.event_ids}
    total, hit, misses = 0, 0, []
    for ev in scenario.events:
        for gt in ev.expected_gaps:
            total += 1
            if (ev.id, gt) in found:
                hit += 1
            else:
                misses.append(f"event {ev.id}: {gt}")
    return {"expected": total, "found": hit, "rate": round(hit / total, 3) if total else 1.0, "missed": misses}
