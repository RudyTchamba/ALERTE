"""Détection PURE : `detect(snapshot, registry, demands, events) -> [GapCandidate]` (aucun modèle, aucune base, aucun LLM).

Entrées indépendantes (doc 09 §9.1) : registre de mandats actifs (validés, sources résolues, dans le snapshot),
demandes + étiquettes d'inject, signaux COORD (événements GAP), hypothèses d'agents. Les « lacunes attendues » n'existent
nulle part dans ce chemin (I2). La recherche négative, la couverture et la cause sont ajoutées ensuite par l'engine
(`scoring.finalize` est ré-appliqué après).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from . import constants as C
from .rules import EXTENSIONS, RULES, RULES_BY_CODE, GapRule
from .scoring import finalize


# --------------------------------------------------------------------------- entrées
@dataclass(frozen=True)
class MandateView:
    id: str
    institution_id: str
    kind: str
    action_code: str | None
    description: str = ""
    procedure_status: str = "unknown"
    has_deadline: bool = False
    dependency_text: str | None = None
    dependency_ready: str | None = None
    depends_on_id: str | None = None
    conflicts_with_id: str | None = None
    validation: str = "validated"
    sources: tuple[dict, ...] = ()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MandateView:
        return cls(id=d["id"], institution_id=d["institution_id"], kind=d["kind"], action_code=d.get("action_code"),
                   description=d.get("description") or "", procedure_status=d.get("procedure_status") or "unknown",
                   has_deadline=bool(d.get("has_deadline")), dependency_text=d.get("dependency_text") or None,
                   dependency_ready=d.get("dependency_ready"), depends_on_id=d.get("depends_on_id"),
                   conflicts_with_id=d.get("conflicts_with_id"), validation=d.get("validation") or "validated",
                   sources=tuple(d.get("sources") or ()))


@dataclass
class Registry:
    """Mandats ACTIFS (validés) + mandats proposés (faibles) + état de revue par institution."""

    mandates: list[MandateView] = field(default_factory=list)
    proposed: list[MandateView] = field(default_factory=list)
    states: dict[str, str] = field(default_factory=dict)

    @classmethod
    def build(cls, mandates: list[dict[str, Any]], states: dict[str, str] | None = None) -> Registry:
        views = [MandateView.from_dict(m) for m in mandates]
        return cls([m for m in views if m.validation == "validated"], [m for m in views if m.validation == "proposed"],
                   dict(states or {}))

    def state(self, institution_id: str) -> str:
        return self.states.get(institution_id, "unreviewed")

    def worst_state(self, institution_ids: list[str]) -> str:
        if not institution_ids:
            return "unreviewed"
        return min((self.state(i) for i in institution_ids), key=lambda s: C.REGISTRY_RANK.get(s, 0))

    def by_id(self, mandate_id: str | None) -> MandateView | None:
        return next((m for m in self.mandates if m.id == mandate_id), None) if mandate_id else None


def _covers(m: MandateView, action: str, rule_match: str, domains: dict[str, str | None]) -> bool:
    if m.action_code == action:
        return True
    dom = domains.get(action)
    return rule_match == "action_or_domain" and bool(dom) and m.action_code is not None and domains.get(m.action_code) == dom


def holders(reg: Registry, action: str, kinds: tuple[str, ...], match: str, domains: dict[str, str | None],
            proposed: bool = False) -> list[MandateView]:
    pool = reg.proposed if proposed else reg.mandates
    return [m for m in pool if m.kind in kinds and _covers(m, action, match, domains)]


@dataclass(frozen=True)
class Demand:
    inject_ref: str
    action_code: str
    seq: int = 0
    sim_time: str | None = None
    derivation: str | None = None
    justification: str | None = None
    recipients: tuple[str, ...] = ()
    tags: frozenset[str] = frozenset()


def demands_from_snapshot(snapshot: dict[str, Any]) -> list[Demand]:
    out = []
    catalog = {a["code"]: a for a in snapshot.get("actions", [])}
    for inj in (snapshot.get("scenario") or {}).get("injects", []):
        for d in inj.get("demands", []):
            code = d["action_code"]
            out.append(Demand(inject_ref=inj["inject_ref"], action_code=code, seq=inj.get("seq", 0),
                              sim_time=inj.get("sim_time"), derivation=d.get("derivation") or catalog.get(code, {}).get("derivation"),
                              justification=d.get("justification") or catalog.get(code, {}).get("justification"),
                              recipients=tuple(inj.get("recipients", [])), tags=frozenset(inj.get("tags", []))))
    return out


# --------------------------------------------------------------------------- sortie
@dataclass
class Ev:
    kind: str
    role: str
    ref: dict[str, Any]
    excerpt: str | None = None
    is_agent: bool = False

    def key(self) -> str:
        return f"{self.kind}|{self.role}|{sorted(self.ref.items(), key=str)}"


@dataclass
class GapCandidate:
    group_key: str
    code: str
    category: str
    title: str
    description: str
    action_code: str | None
    action_key: str | None
    domain: str | None
    institutions: list[str]                 # affichage (réunion règle + signaux)
    core_institutions: list[str]            # base de l'empreinte
    rule_id: str | None = None
    origin: str = "rule"
    basis: str = "inferred"                 # base provisoire (avant recherche négative / couverture)
    absence: bool = False
    needs_negative_search: bool = False
    registry_state: str | None = None
    inject_refs: list[str] = field(default_factory=list)
    tags: frozenset[str] = frozenset()
    base_severity: int = 2
    severity: int = 2
    notes: list[str] = field(default_factory=list)
    evidence: list[Ev] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)
    derivations: set[str] = field(default_factory=set)
    scripted: bool = False
    proposed_mandate: bool = False
    # renseignés par l'engine / scoring
    neg_status: str = "pending"             # pending | ran | unavailable
    strong_hit: bool = False
    corpus_documents: int | None = None
    coverage: float | None = None
    artifact: bool = False
    # sorties de scoring.finalize
    evidence_basis: str = "inferred"
    confidence: str = "low"
    cause: str = "undetermined"
    fingerprint: str = ""

    @property
    def observed_signals(self) -> int:
        return sum(1 for s in self.signals if s.get("observed"))

    def add_evidence(self, ev: Ev) -> None:
        if all(e.key() != ev.key() for e in self.evidence):
            self.evidence.append(ev)

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    @property
    def demand_derivation(self) -> str | None:
        if not self.derivations:
            return None
        return next(iter(self.derivations)) if len(self.derivations) == 1 else "mixed"


def fingerprint(code: str, action_key: str | None, institutions: list[str], domain: str | None) -> str:
    raw = "|".join([code, action_key or "", ",".join(sorted(set(institutions))), domain or ""])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- détection
class _Ctx:
    def __init__(self, snapshot: dict[str, Any], registry: Registry, demands: list[Demand], events: list[dict[str, Any]]):
        self.snap, self.reg, self.demands, self.events = snapshot, registry, demands, events
        self.lang = ((snapshot.get("scenario") or {}).get("language") or "fr")[:2]
        self.lang = self.lang if self.lang in ("fr", "en") else "en"
        self.actions = {a["code"]: a for a in snapshot.get("actions", [])}
        self.domains = {c: a.get("domain") for c, a in self.actions.items()}
        self.institutions = {i["id"]: i for i in snapshot.get("institutions", [])}
        self.seats = {s["code"]: s for s in snapshot.get("seats", [])}
        self.inject_titles = {i.get("inject_ref"): i.get("title") for i in (snapshot.get("scenario") or {}).get("injects", [])}
        self.scripted = ((snapshot.get("exercise") or {}).get("ai_mode") == "scripted")
        self.cands: dict[str, GapCandidate] = {}
        self.inject_seq: dict[str, int] = {}
        for e in events:
            if e["type"] == "INJECT":
                self.inject_seq.setdefault(e["payload"].get("inject_ref"), e["seq"])

    def label(self, action: str | None, ref: str | None = None, institutions: list[str] | None = None) -> str:
        """Libellé lisible : l'action ; sans action, l'inject et les institutions concernées (jamais « ? »)."""
        if action:
            return self.actions.get(action, {}).get("label") or action
        parts = [self.inject_titles.get(ref) or ref, ", ".join(sorted({self.icode(i) for i in institutions or []}))]
        return " — ".join(x for x in parts if x) or ("action non précisée" if self.lang == "fr" else "unspecified action")

    def icode(self, iid: str) -> str:
        return self.institutions.get(iid, {}).get("code", iid)

    def concerned(self, d: Demand | None, extra: list[str] | None = None) -> list[str]:
        ids = sorted(set((d.recipients if d else ()) or ()) | set(extra or ()))
        return ids or sorted(self.institutions)


def _mand_ev(m: MandateView, role: str = "supports") -> Ev:
    src = m.sources[0] if m.sources else {}
    return Ev("mandate", role, {"mandate_id": m.id, "institution_id": m.institution_id, "kind": m.kind,
                                "action_code": m.action_code, "validation": m.validation,
                                "procedure_status": m.procedure_status,
                                "sources": [{k: s.get(k) for k in ("document_version_id", "chunk_id", "article", "page")}
                                            for s in m.sources]}, src.get("quote"))


def _merge(ctx: _Ctx, c: GapCandidate, weaken: bool = True) -> GapCandidate:
    cur = ctx.cands.get(c.group_key)
    if cur is None:
        ctx.cands[c.group_key] = c
        return c
    for attr in ("institutions", "core_institutions", "inject_refs"):
        setattr(cur, attr, sorted(set(getattr(cur, attr)) | set(getattr(c, attr))))
    for n in c.notes:
        cur.note(n)
    for e in c.evidence:
        cur.add_evidence(e)
    cur.signals += c.signals
    cur.derivations |= c.derivations
    cur.proposed_mandate |= c.proposed_mandate
    if c.base_severity > cur.base_severity:
        cur.base_severity, cur.tags = c.base_severity, c.tags
    # occurrences multiples : on garde la base la plus FAIBLE et l'état de registre le plus faible
    if weaken and C.BASIS_RANK[c.basis] > C.BASIS_RANK[cur.basis]:
        cur.basis = c.basis
    if C.REGISTRY_RANK.get(c.registry_state or "", 0) < C.REGISTRY_RANK.get(cur.registry_state or "", 0):
        cur.registry_state = c.registry_state
    return cur


def _new(ctx: _Ctx, rule: GapRule | None, code: str, action: str | None, action_key: str | None, d: Demand | None,
         institutions: list[str], category: str, severity: int, origin: str, basis: str, desc: str,
         absence: bool = False, ref: str | None = None) -> GapCandidate:
    ext = EXTENSIONS.get(code)
    name = (rule.names if rule else ext["names"] if ext else {}).get(ctx.lang, code)
    label = ctx.label(action, ref or (d.inject_ref if d else None), institutions)
    dom = ctx.domains.get(action or "")
    key = f"{code}|{action_key or action or '-'}"
    c = GapCandidate(group_key=key, code=code, category=category, title=f"{name} : {label}", description=desc,
                     action_code=action, action_key=action_key or action, domain=dom, institutions=sorted(set(institutions)),
                     core_institutions=sorted(set(institutions)), rule_id=rule.code if rule else None, origin=origin,
                     basis=basis, absence=absence, needs_negative_search=bool(rule and rule.negative_search),
                     inject_refs=[d.inject_ref] if d else [], tags=d.tags if d else frozenset(), base_severity=severity,
                     severity=severity, scripted=ctx.scripted)
    if d:
        c.derivations.add(d.derivation or "unknown")
    return c


def _evaluate(ctx: _Ctx, rule: GapRule, d: Demand) -> None:
    lang, label = ctx.lang, ctx.label(d.action_code)
    reg = ctx.reg
    tags = d.tags
    cat = rule.category
    if rule.crisis_category_tag and rule.crisis_category_tag in tags:
        cat = "crisis_preparedness_response_gap"
    sev = rule.severity(tags)
    ev_inject = Ev("event", "context", {"inject_ref": d.inject_ref, "seq": ctx.inject_seq.get(d.inject_ref),
                                        "sim_time": d.sim_time})
    if rule.evaluator == "absence":
        found = holders(reg, d.action_code, rule.kinds, rule.match, ctx.domains)
        if found:
            return
        concerned = ctx.concerned(d)
        state = reg.worst_state(concerned)
        prop = holders(reg, d.action_code, rule.kinds, rule.match, ctx.domains, proposed=True)
        c = _new(ctx, rule, rule.code, d.action_code, None, d, concerned, cat, sev, "rule", "documented",
                 rule.texts[lang].format(kinds="/".join(rule.kinds), label=label), absence=True)
        c.registry_state = state
        c.add_evidence(Ev("mandate", "supports", {"registry_check": {
            "action_code": d.action_code, "kinds": list(rule.kinds), "match": rule.match, "found": 0,
            "institutions_checked": concerned, "registry_states": {i: reg.state(i) for i in concerned}}}))
        if state != "reviewed_complete":
            c.basis = "inferred"
            c.note("registre non revu : absence déduite par règle, jamais « documentée »")
        for m in prop:
            c.proposed_mandate = True
            c.basis = "inferred"
            c.add_evidence(_mand_ev(m, "context"))
            c.note("mandat proposé non validé")
        c.add_evidence(ev_inject)
        _merge(ctx, c)
    elif rule.evaluator == "overlap":
        powers = holders(reg, d.action_code, rule.kinds, "action", ctx.domains)
        insts = sorted({m.institution_id for m in powers})
        if len(insts) < 2 or holders(reg, d.action_code, ("lead",), "action", ctx.domains):
            return
        concerned = sorted(set(insts) | set(d.recipients))
        c = _new(ctx, rule, "G2", d.action_code, None, d, insts, cat, sev, "rule", "documented",
                 rule.texts[lang].format(label=label), absence=False)
        c.registry_state = reg.worst_state(concerned)
        if c.registry_state != "reviewed_complete":  # « pas de chef de file » est une absence : intégrité du registre
            c.basis = "inferred"
            c.note("registre non revu : absence de chef de file déduite par règle")
        if holders(reg, d.action_code, ("lead",), "action", ctx.domains, proposed=True):
            c.basis, c.proposed_mandate = "inferred", True
            c.note("mandat proposé non validé")
        for m in powers:
            c.add_evidence(_mand_ev(m))
        c.add_evidence(ev_inject)
        _merge(ctx, c)
    elif rule.evaluator == "procedure":
        hold = holders(reg, d.action_code, rule.kinds, "action", ctx.domains)
        if not hold:
            return
        proc = hold + holders(reg, d.action_code, ("procedure",), "action", ctx.domains)
        no_proc = not any(m.procedure_status == "specific" for m in proc)
        no_deadline = "time_critical" in tags and not any(m.has_deadline for m in hold)
        if not (no_proc or no_deadline):
            return
        insts = sorted({m.institution_id for m in hold})
        if no_proc:
            deadline = " ni délai défini" if lang == "fr" else " nor defined deadline"
            text = rule.texts[lang].format(label=label, deadline=deadline if no_deadline else "")
        else:  # procédure spécifique documentée, mais aucun délai pour une action urgente
            text = (f"L'action « {label} » a une procédure spécifique mais aucun délai défini, alors que la situation est urgente."
                    if lang == "fr" else
                    f"Action \"{label}\" has a specific procedure but no defined deadline, although the situation is time-critical.")
        c = _new(ctx, rule, "G3", d.action_code, None, d, insts, cat, sev, "rule", "documented", text, absence=True)
        c.registry_state = reg.worst_state(insts)
        if c.registry_state != "reviewed_complete":
            c.basis = "inferred"
            c.note("registre non revu : absence de procédure déduite par règle")
        for m in hold:
            c.add_evidence(_mand_ev(m))
        c.add_evidence(ev_inject)
        _merge(ctx, c)
    elif rule.evaluator == "dependency":
        active_ids = {m.id for m in reg.mandates}
        for m in holders(reg, d.action_code, rule.kinds, "action", ctx.domains):
            if not m.dependency_text or m.dependency_ready == "yes" or m.depends_on_id in active_ids:
                continue
            c = _new(ctx, rule, "G4", d.action_code, None, d, [m.institution_id], cat, sev, "rule", "documented",
                     rule.texts[lang].format(label=label, dep=m.dependency_text), absence=True)
            c.registry_state = reg.state(m.institution_id)
            if c.registry_state != "reviewed_complete":
                c.basis = "inferred"
                c.note("registre non revu : dépendance non résolue déduite par règle")
            c.add_evidence(_mand_ev(m))
            c.add_evidence(ev_inject)
            _merge(ctx, c)


def _evaluate_conflicts(ctx: _Ctx, rule: GapRule) -> None:
    by_inject: dict[str, list[Demand]] = {}
    for d in ctx.demands:
        by_inject.setdefault(d.inject_ref, []).append(d)
    seen: set[tuple[str, str, str]] = set()
    for ref, dems in by_inject.items():
        actions = {d.action_code for d in dems}
        tags = frozenset().union(*(d.tags for d in dems))
        for m in ctx.reg.mandates:
            p = ctx.reg.by_id(m.conflicts_with_id)
            if p is None or m.kind not in rule.kinds or p.kind not in rule.kinds:
                continue
            if m.action_code not in actions or p.action_code not in actions:
                continue
            pair = tuple(sorted([m.id, p.id]))
            if (ref, *pair) in seen:
                continue
            seen.add((ref, *pair))
            akey = "|".join(sorted({m.action_code or "", p.action_code or ""}))
            first = next(d for d in dems if d.action_code in (m.action_code, p.action_code))
            label = " / ".join(ctx.label(a) for a in akey.split("|"))
            insts = sorted({m.institution_id, p.institution_id})
            c = _new(ctx, rule, "G5", min(m.action_code or "", p.action_code or "") or None, akey, first, insts,
                     rule.category, rule.severity(tags), "rule", "documented", rule.texts[ctx.lang].format(label=label))
            c.title = f"{rule.names[ctx.lang]} : {label}"
            c.registry_state = ctx.reg.worst_state(insts)
            c.add_evidence(_mand_ev(m))
            c.add_evidence(_mand_ev(p))
            _merge(ctx, c)


# --------------------------------------------------------------------------- signaux et hypothèses
def _seat_info(ctx: _Ctx, seat_code: str | None) -> tuple[str | None, bool]:
    seat = ctx.seats.get(seat_code or "")
    if not seat:
        return None, False
    return seat.get("institution_id"), seat.get("controller") == "agent"


def _signal_candidates(ctx: _Ctx) -> None:
    for e in ctx.events:
        p = e["payload"]
        if e["type"] != "GAP" or p.get("origin_kind") not in ("coordinator_signal", "coordinator"):
            continue
        sig = p.get("signal")
        spec = C.SIGNALS.get(sig)
        if spec is None:
            continue
        action = p.get("action_code")
        insts = list(p.get("institutions") or [])
        ref = p.get("inject_ref")
        d = next((x for x in ctx.demands if x.inject_ref == ref and x.action_code == action), None)
        code, cat = spec["code"], spec["category"]
        if sig == "MISSING_BASIS":
            hold = action and holders(ctx.reg, action, ("power", "duty", "lead"), "action", ctx.domains)
            code, cat = ("G3", "regulatory_gap") if hold else ("G1", "mandate_absent_or_incomplete")
        observed = not ctx.scripted                       # le signal corrobore (jamais « observé » en scripted)
        alone_observed = spec["observed"] and observed    # base du candidat si le signal est SEUL
        rule = RULES_BY_CODE.get(code)
        sev = rule.severity(d.tags if d else frozenset()) if rule else EXTENSIONS[code]["severity"]
        if not rule and d and "life_risk" in d.tags:
            sev = EXTENSIONS[code]["life_bump"]
        key_action = action
        if code == "G5" and action:  # rattacher au candidat de règle dont l'action_key contient l'action
            hit = next((k for k, c in ctx.cands.items() if c.code == "G5" and action in (c.action_key or "").split("|")), None)
            if hit:
                key_action = ctx.cands[hit].action_key
        concerned = insts or ctx.concerned(d)
        c = _new(ctx, rule, code, action, key_action, d, insts or list(d.recipients if d else ()), cat, sev,
                 "coordinator_signal", "observed" if alone_observed else "inferred",
                 f"Signal {sig} émis par le coordinateur" + (f" (inject {ref})" if ref else ""),
                 absence=spec["absence"], ref=ref)
        if not ref and action is None:
            c.group_key += f"|{e['seq']}"
        c.registry_state = ctx.reg.worst_state(concerned)
        c.needs_negative_search = bool(rule and rule.negative_search and spec["absence"])
        sigrec = {"signal": sig, "observed": observed, "scripted": ctx.scripted, "seq": e["seq"], "inject_ref": ref}
        c.signals.append(sigrec)
        if ctx.scripted:
            c.note("signal d'un exercice sans IA (scripted) : jamais « observé »")
        elif sig in ("ORPHAN_REQUEST", "NO_OWNER"):
            c.note("signal seul : base « inferred » tant qu'aucune règle documentaire ne le corrobore")
        c.add_evidence(Ev("coordinator_signal", "supports", {"signal": sig, "seq": e["seq"], "inject_ref": ref,
                                                             "evidence": p.get("evidence") or {}}))
        if d:
            c.add_evidence(Ev("event", "context", {"inject_ref": ref, "seq": ctx.inject_seq.get(ref)}))
        for mid in (p.get("evidence") or {}).get("msg_ids", []):
            c.add_evidence(Ev("message", "context", {"msg_id": mid}))
        existing = ctx.cands.get(c.group_key)
        merged = _merge(ctx, c, weaken=existing is None)
        if existing is not None and merged.basis == "inferred" and observed and merged.origin == "rule":
            merged.basis = "observed"
        # lien vers les décisions de l'inject sur la même action
        for ev in ctx.events:
            if ev["type"] == "DECISION" and ev["payload"].get("inject_ref") == ref and ev["payload"].get("action_code") == action:
                _decision_evidence(ctx, merged, ev)


def _decision_evidence(ctx: _Ctx, c: GapCandidate, ev: dict[str, Any]) -> None:
    p = ev["payload"]
    _inst, is_agent = _seat_info(ctx, p.get("seat_code"))
    is_agent = is_agent or p.get("author") == "agent"
    c.add_evidence(Ev("decision", "context", {"decision_id": p.get("decision_id"), "seat_code": p.get("seat_code"),
                                              "seq": ev["seq"], "outcome": p.get("outcome")},
                      (p.get("rationale") or "")[:300] or None, is_agent=is_agent))


def _hypotheses(ctx: _Ctx) -> None:
    found: dict[tuple, dict[str, Any]] = {}
    for e in ctx.events:
        p, t = e["payload"], e["type"]
        items = []
        if t == "GAP" and (p.get("origin_kind") == "agent_hypothesis" or p.get("signal") == "AGENT_HYPOTHESIS"):
            ev = p.get("evidence") or {}
            items.append((p.get("inject_ref"), p.get("action_code"), ev.get("hint"), ev.get("text") or "",
                          list(p.get("institutions") or []), {"kind": "message", "ref": {"seq": e["seq"]}}))
        elif t == "DECISION":
            inst, _ = _seat_info(ctx, p.get("seat_code"))
            for fl in p.get("gap_flags") or []:
                items.append((p.get("inject_ref"), p.get("action_code"), fl.get("hint"), fl.get("text") or "",
                              [inst] if inst else [], {"kind": "decision", "ref": {"decision_id": p.get("decision_id"),
                                                                                    "seat_code": p.get("seat_code"), "seq": e["seq"]}}))
        elif t == "BOARD" and p.get("msg_type") == "GAP_FLAG":
            inst, _ = _seat_info(ctx, p.get("from"))
            items.append((p.get("inject_ref"), None, None, p.get("body") or "", [inst] if inst else [],
                          {"kind": "message", "ref": {"msg_id": p.get("msg_id"), "seq": e["seq"]}}))
        for ref, action, hint, text, insts, evd in items:
            rec = found.setdefault((ref, action, hint), {"texts": [], "insts": set(), "evs": []})
            if text and text not in rec["texts"]:
                rec["texts"].append(text)
            rec["insts"] |= set(insts)
            rec["evs"].append(evd)
    for (ref, action, hint), rec in sorted(found.items(), key=lambda kv: str(kv[0])):
        code, cat = C.HINTS.get(hint or "", C.DEFAULT_HYPOTHESIS)
        d = next((x for x in ctx.demands if x.inject_ref == ref and x.action_code == action), None)
        text = " ; ".join(rec["texts"])[:600]
        agent_evs = [Ev(x["kind"], "context", x["ref"], text or None, is_agent=True) for x in rec["evs"]]
        existing = ctx.cands.get(f"{code}|{action or '-'}") if code.startswith("G") and action else None
        if existing is not None:  # hypothèse corroborée par un candidat non-agent : simple contexte
            for a in agent_evs:
                existing.add_evidence(a)
            existing.note("hypothèse d'agent concordante (contexte, non comptée comme preuve)")
            continue
        rule = RULES_BY_CODE.get(code)
        sev = rule.severity(d.tags if d else frozenset()) if rule else EXTENSIONS[code]["severity"]
        c = _new(ctx, rule, code, action, None, d, sorted(rec["insts"]), cat, sev, "agent_hypothesis", "hypothesis",
                 f"Hypothèse d'agent : {text}" if text else "Hypothèse d'agent (sans texte)", ref=ref)
        if code.startswith("X") or not action:
            c.group_key = f"{code}|{action or '-'}|{hint or '-'}|{ref or '-'}"
        c.needs_negative_search = False
        c.registry_state = ctx.reg.worst_state(sorted(rec["insts"]))
        c.note("hypothèse d'agent : jamais comptée comme constat (aucune preuve non-agent)")
        for a in agent_evs:
            c.add_evidence(a)
        _merge(ctx, c)


# --------------------------------------------------------------------------- point d'entrée
def detect(snapshot: dict[str, Any], registry: Registry, demands: list[Demand], events: list[dict[str, Any]]) -> list[GapCandidate]:
    ctx = _Ctx(snapshot, registry, demands, events)
    for d in sorted(demands, key=lambda x: (x.seq, x.inject_ref, x.action_code)):
        for rule in RULES:
            if rule.evaluator == "conflict" or not rule.required_tags <= d.tags:
                continue
            _evaluate(ctx, rule, d)
    _evaluate_conflicts(ctx, RULES_BY_CODE["G5"])
    _signal_candidates(ctx)
    _hypotheses(ctx)
    out = []
    for c in ctx.cands.values():
        # décisions de l'inject liées (contexte) pour la chaîne de preuves
        for ev in events:
            p = ev["payload"]
            if ev["type"] == "DECISION" and c.action_code and p.get("action_code") == c.action_code \
                    and p.get("inject_ref") in c.inject_refs:
                _decision_evidence(ctx, c, ev)
        c.severity = c.base_severity
        c.fingerprint = fingerprint(c.code, c.action_key, c.core_institutions, c.domain)
        finalize(c)
        out.append(c)
    return sorted(out, key=lambda c: (-c.severity, c.code, c.group_key))
