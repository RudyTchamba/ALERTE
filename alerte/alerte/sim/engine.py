"""The drill engine: delivers events one by one to the right seats, lets each seat decide,
runs the coordination rounds, and writes everything to the logbook.

    drill = Drill("cm01", brain="offline")
    while not drill.done:
        drill.step()
    result = drill.finish()
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from alerte import __version__, config
from alerte.knowledge.ingest import ensure_index
from alerte.knowledge.mandates import MandateMap, load_mandates
from alerte.knowledge.store import KnowledgeStore, get_store
from alerte.models import Citation, Decision, Message, MessageType, RoleCard, Scenario
from alerte.sim.brain import DecisionDraft, LLMBrain, OfflineBrain, Request, SeatContext, make_brain
from alerte.sim.citations import check_all
from alerte.sim.ledger import Ledger
from alerte.sim.scenario import load_roles, load_scenario
from alerte.textutil import shorten

log = logging.getLogger(__name__)

NON_PLAYING = {"COORD", "LEGAL"}


@dataclass
class SeatState:
    role: RoleCard
    human: bool = False
    inbox: list[str] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)


@dataclass
class StepResult:
    event_id: int
    sim_time: str
    recipients: list[str]
    decisions: list[Decision]
    messages: list[Message]
    seconds: float


class Drill:
    def __init__(self, scenario: str | Scenario, brain: str | None = None, lang: str | None = None,
                 human_seats: set[str] | list[str] | None = None, run_dir: Path | None = None,
                 store: KnowledgeStore | None = None, mandates: MandateMap | None = None, run_id: str | None = None,
                 brain_obj: OfflineBrain | None = None):
        ensure_index()
        self.scenario = scenario if isinstance(scenario, Scenario) else load_scenario(scenario)
        self.roles = load_roles(self.scenario)
        self.lang = (lang or self.scenario.language or config.settings.language).lower()
        self.store = store or get_store()
        self.mm = mandates or load_mandates()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.brain_name = (brain or config.settings.brain or "offline").lower()
        self.run_id = run_id or f"{self.scenario.id}-{self.brain_name}-{stamp}-{uuid.uuid4().hex[:4]}"
        self.run_dir = Path(run_dir or (config.settings.runs_dir / self.run_id))
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.run_dir / "ledger.jsonl")
        self.brain = brain_obj or make_brain(self.brain_name, self.store, self.mm, recorder=self._record)
        if brain_obj is not None and isinstance(brain_obj, LLMBrain):
            brain_obj.recorder = self._record
        humans = set(human_seats or [])
        self.seats = {code: SeatState(role, human=code in humans) for code, role in self.roles.items()
                      if code not in NON_PLAYING}
        self.decisions: list[Decision] = []
        self.messages: list[Message] = []
        self.index = 0
        self._consulted: set[tuple[str, str]] = set()
        self.legal_answers: list[dict[str, Any]] = []
        self.status = "ready"
        self.started = time.time()
        self.model_info = {"brain": self.brain.name}
        if isinstance(self.brain, LLMBrain):
            self.model_info.update({"model": self.brain.client.model, "base_url": self.brain.client.base_url})
        self.ledger.append("START", "FACILITATOR", {
            "run_id": self.run_id, "scenario": self.scenario.id, "title": self.scenario.title,
            "country": self.scenario.country, "language": self.lang, "brain": self.model_info,
            "human_seats": sorted(humans), "seats": {c: s.role.name for c, s in self.seats.items()},
            "fictional_notice": self.scenario.fictional_notice, "alerte_version": __version__,
            "index": self.store.stats()})

    # ------------------------------------------------------------------ helpers
    def _record(self, kind: str, data: dict[str, Any]) -> None:
        ev = self.scenario.events[self.index] if self.index < len(self.scenario.events) else None
        self.ledger.append(kind, data.get("actor", "SYSTEM"), data, ev.sim_time if ev else "")

    def _msg(self, ev, type_: MessageType, sender: str, text: str, recipient: str = "ALL", action: str = "",
             in_reply_to: str = "", status: str = "", round_: int = 0, author: str = "") -> Message:
        m = Message(msg_id=f"m{len(self.messages) + 1:04d}", event_id=ev.id, round=round_, type=type_, sender=sender,
                    recipient=recipient, text=text, action=action, in_reply_to=in_reply_to, status=status, author=author)
        self.messages.append(m)
        self.ledger.append("BOARD", sender, m.model_dump(mode="json"), ev.sim_time)
        return m

    @property
    def done(self) -> bool:
        return self.index >= len(self.scenario.events)

    @property
    def next_event(self):
        return None if self.done else self.scenario.events[self.index]

    def pending_humans(self) -> list[str]:
        ev = self.next_event
        return [] if ev is None else [c for c in ev.to if c in self.seats and self.seats[c].human]

    def seat_search(self, seat: SeatState, query: str, k: int | None = None):
        r = seat.role
        return self.store.search(query, k or config.settings.top_k,
                                 countries=r.kb_countries or None, institutions=r.kb_institutions or None,
                                 include_fictional=r.kind == "ai_system")

    def _context(self, seat: SeatState, ev) -> SeatContext:
        actions = [self.mm.action(a) for a in ev.required_actions]
        query = ev.text_in(self.lang) + " " + " ".join(f"{a.label} {' '.join(a.keywords)}" for a in actions)
        hits = self.seat_search(seat, query)
        if seat.role.kind == "ai_system" and seat.role.model_card:
            card = [c for c in self.store.doc_chunks(seat.role.model_card)]
            hit_ids = {h.chunk.chunk_id for h in hits}
            passages = [c for c in card if c.chunk_id not in hit_ids] + [h.chunk for h in hits]
        else:
            passages = [h.chunk for h in hits]
        self.ledger.append("RETRIEVAL", seat.role.code, {
            "event_id": ev.id, "query": shorten(query, 400),
            "filters": {"countries": seat.role.kb_countries, "institutions": seat.role.kb_institutions},
            "results": [{"chunk_id": h.chunk.chunk_id, "doc_id": h.chunk.doc_id, "article": h.chunk.article,
                         "score": h.score} for h in hits]}, ev.sim_time)
        return SeatContext(role=seat.role, country=self.scenario.country, lang=self.lang, event=ev,
                           inbox=list(seat.inbox), passages=passages,
                           own_lines=self.mm.institution_lines(seat.role.code, self.scenario.country),
                           seats_in_drill=set(self.seats))

    def _human_decision(self, seat: SeatState, ev, data: dict[str, Any]) -> DecisionDraft:
        cites = []
        if data.get("doc_id"):
            cites.append(Citation(doc_id=data["doc_id"], article=data.get("article", ""), quote=data.get("quote", "")))
        dec = Decision(seat=seat.role.code, event_id=ev.id, sim_time=ev.sim_time,
                       situation=shorten(ev.text_in(self.lang), 300),
                       known=[x for x in [data.get("known", "")] if x], unknown=[x for x in [data.get("unknown", "")] if x],
                       decision=data.get("decision") or "(no decision)", action=data.get("action", ""),
                       legal_basis=cites, no_legal_basis=bool(data.get("no_legal_basis")) or not cites,
                       confidence=data.get("confidence", "medium"),
                       gap_flags=[x for x in [data.get("gap_flag", "")] if x],
                       reasoning_summary=data.get("reasoning", ""), author="human")
        reqs = [Request(r["to"], r.get("action", ""), r.get("text", "")) for r in data.get("requests", [])
                if r.get("to") in self.seats]
        return DecisionDraft(dec, reqs)

    def _check(self, dec: Decision) -> Decision:
        if dec.legal_basis:
            dec.legal_basis = check_all(dec.legal_basis, self.store)
            self.ledger.append("CITATION_CHECK", dec.seat, {
                "event_id": dec.event_id, "results": [c.model_dump() for c in dec.legal_basis]}, dec.sim_time)
        return dec

    def _record_decision(self, seat: SeatState, draft: DecisionDraft, ev) -> Decision:
        dec = self._check(draft.decision)
        failed = [c for c in dec.legal_basis if c.verified is False]
        if failed and isinstance(self.brain, LLMBrain) and dec.author == "ai":
            seat.inbox.append("SYSTEM: your citation(s) " + ", ".join(f"{c.doc_id} {c.article}" for c in failed)
                              + " could not be verified. Cite only the passages given, quoting exact words.")
            retry = self.brain.decide(self._context(seat, ev))
            retry.decision = self._check(retry.decision)
            if sum(c.verified is False for c in retry.decision.legal_basis) < len(failed):
                draft, dec = retry, retry.decision
        seat.decisions.append(dec)
        self.decisions.append(dec)
        self.ledger.append("DECISION", seat.role.code, dec.model_dump(mode="json"), ev.sim_time)
        said = dec.statement or (dec.decision + (f" Why: {shorten(dec.reasoning_summary, 200)}" if dec.reasoning_summary else ""))
        self._msg(ev, MessageType.DECISION, seat.role.code, said, action=dec.action, author=dec.author)
        for flag in dec.gap_flags:
            self._msg(ev, MessageType.GAP_FLAG, seat.role.code, flag, action=dec.action, author=dec.author)
        self._consult_legal(seat, dec, ev)
        return dec

    def _consult_legal(self, seat: SeatState, dec: Decision, ev) -> None:
        """A seat that found no legal basis asks the Legal Adviser agent (the 4th tool of each agent).
        The adviser answers from the national texts and global precedents; it never gives a final opinion."""
        key = (seat.role.code, dec.action)
        if (not dec.action or not (dec.no_legal_basis or dec.gap_flags) or key in self._consulted
                or len(self._consulted) >= config.settings.legal_consult_max or "LEGAL" not in self.roles):
            return
        from alerte.sim.adviser import ask
        self._consulted.add(key)
        label = self.mm.action(dec.action).label
        question = f"What legal basis exists for this institution to: {label.lower()}?"
        who = "ai" if isinstance(self.brain, LLMBrain) else "rules"
        req = self._msg(ev, MessageType.REQUEST, seat.role.code, question, recipient="LEGAL", action=dec.action, round_=1, author=dec.author)
        ans = ask(question, country=self.scenario.country, lang=self.lang, brain=self.brain, store=self.store,
                  mm=self.mm, action_code=dec.action)
        self.legal_answers.append({"event_id": ev.id, "seat": seat.role.code, "action": dec.action,
                                   **ans.model_dump(mode="json")})
        self.ledger.append("LEGAL", "LEGAL", {"event_id": ev.id, "asked_by": seat.role.code, "action": dec.action,
                                              "answer": ans.model_dump(mode="json")}, ev.sim_time)
        where = ", ".join(sorted({p.jurisdiction for p in ans.elsewhere})) or "none found"
        text = (f"{shorten(ans.national, 260)} | Missing: {shorten(ans.missing, 160)} | Examples elsewhere: {where}. "
                f"{ans.disclaimer}")
        self._msg(ev, MessageType.ANSWER, "LEGAL", text, recipient=seat.role.code, action=dec.action,
                  in_reply_to=req.msg_id, status="accepted", round_=1, author=who)

    def _deliberate(self, ev, start: int) -> None:
        """Discussion round (AI mode): every seat that decided reads what the others decided and agrees, objects or asks.
        The rule engine does not deliberate, so nothing is posted in that mode."""
        mine = [d for d in self.decisions[start:] if d.seat in self.seats and self.seats[d.seat].role.kind != "ai_system"
                and d.author in ("ai", "fallback", "human")]
        seats = sorted({d.seat for d in mine})
        if len(seats) < 2 or not isinstance(self.brain, LLMBrain):
            return
        for code in seats:
            seat = self.seats[code]
            if seat.human:
                continue
            others = [d for d in mine if d.seat != code]
            digest = "\n".join(
                f"- {d.seat}: {shorten(d.statement or d.decision, 240)} [action: {d.action or 'none'}; "
                + ("no legal basis found" if d.no_legal_basis else
                   "cites " + ", ".join(f"{c.doc_id} {c.article}".strip() + (" (verified)" if c.verified else " (NOT verified)" if c.verified is False else "")
                                        for c in d.legal_basis) if d.legal_basis else "no citation")
                + f"; confidence {d.confidence}]" for d in others)
            r = self.brain.react(self._context(seat, ev), digest)
            if not r or not r["text"]:
                continue
            target = r["to"] if r["to"] in self.seats and r["to"] != code else "ALL"
            typ = MessageType.OBJECTION if r["stance"] == "object" else MessageType.INFO
            self._msg(ev, typ, code, r["text"], recipient=target, status=r["stance"], round_=3, author="ai")
            if target in self.seats:
                self.seats[target].inbox.append(f"[{ev.sim_time}] {r['stance'].upper()} from {code}: {r['text']}")

    # ------------------------------------------------------------------ main loop
    def step(self, human_inputs: dict[str, dict[str, Any]] | None = None) -> StepResult:
        if self.done:
            raise RuntimeError("The drill has no more events; call finish()")
        t0 = time.time()
        self.status = "running"
        ev = self.scenario.events[self.index]
        n_dec, n_msg = len(self.decisions), len(self.messages)
        recipients = [c for c in ev.to if c in self.seats]
        self.ledger.append("INJECT", ev.sender, {"event_id": ev.id, "act": ev.act, "to": recipients,
                                                 "text": ev.text_in(self.lang), "public": ev.public,
                                                 "failure_mode": ev.failure_mode}, ev.sim_time)
        line = f"[{ev.sim_time}] from {ev.sender}: {ev.text_in(self.lang)}"
        for code in recipients:
            self.seats[code].inbox.append(line)
        drafts: list[tuple[SeatState, DecisionDraft]] = []
        for code in recipients:
            seat = self.seats[code]
            if seat.human and human_inputs and code in human_inputs:
                draft = self._human_decision(seat, ev, human_inputs[code])
            else:
                draft = self.brain.decide(self._context(seat, ev))
                if seat.human:
                    draft.decision.author = "ai (human seat timed out)"
                    self.ledger.append("HUMAN", code, {"event_id": ev.id, "note": "no human input; AI took the seat"}, ev.sim_time)
            self._record_decision(seat, draft, ev)
            for extra in draft.more:
                self._record_decision(seat, DecisionDraft(extra), ev)
            drafts.append((seat, draft))

        # Coordination room: requests and answers, then the drill leader closes the round
        # One request per (target, action); skip if the target already acted on it for this event
        decided = {(d.seat, d.action) for d in self.decisions[n_dec:] if d.action and not d.no_legal_basis}
        pending, seen = [], set()
        for seat, d in drafts:
            for r in d.requests:
                if (r.to, r.action) in seen or (r.to, r.action) in decided:
                    continue
                seen.add((r.to, r.action))
                pending.append((seat.role.code, r))
        unanswered = []
        for rnd in range(1, config.settings.max_board_rounds + 1):
            if not pending:
                break
            nxt = []
            for sender, req in pending:
                m = self._msg(ev, MessageType.REQUEST, sender, req.text, recipient=req.to, action=req.action, round_=rnd,
                              author=self.brain.name if self.brain.name == "llm" else "rules")
                target = self.seats.get(req.to)
                if target is None:
                    unanswered.append(m)
                    continue
                target.inbox.append(f"[{ev.sim_time}] REQUEST from {sender}: {req.text}")
                reply = self.brain.reply(self._context(target, ev), req.action, sender)
                reply.legal_basis = check_all(reply.legal_basis, self.store)
                self._msg(ev, MessageType.ANSWER, req.to, reply.text, recipient=sender, action=req.action,
                          in_reply_to=m.msg_id, status=reply.status, round_=rnd, author=reply.author)
                if reply.status == "accepted":
                    dec = Decision(seat=req.to, event_id=ev.id, sim_time=ev.sim_time,
                                   situation=f"Request from {sender}", decision=reply.text, action=req.action,
                                   legal_basis=reply.legal_basis, confidence="medium", author=reply.author,
                                   statement=reply.text if reply.author == "ai" else "",
                                   reasoning_summary=f"Accepted request {m.msg_id} from {sender}")
                    target.decisions.append(dec)
                    self.decisions.append(dec)
                    self.ledger.append("DECISION", req.to, dec.model_dump(mode="json"), ev.sim_time)
                else:
                    unanswered.append(m)
            pending = nxt
        self._deliberate(ev, n_dec)
        for m in unanswered:
            self._msg(ev, MessageType.GAP_FLAG, "COORD",
                      f"Request {m.msg_id} from {m.sender} to {m.recipient} ('{m.action}') was not taken up by anyone.",
                      action=m.action)
        new_dec = self.decisions[n_dec:]
        self._msg(ev, MessageType.INFO, "COORD",
                  f"Round closed for event {ev.id}: {len(new_dec)} decisions, "
                  f"{sum(1 for m in self.messages[n_msg:] if m.type == MessageType.REQUEST)} requests, "
                  f"{len(unanswered)} not taken up.", author="system")
        self.index += 1
        if self.done:
            self.status = "finished"
        return StepResult(ev.id, ev.sim_time, recipients, new_dec, self.messages[n_msg:], round(time.time() - t0, 3))

    def run(self, progress: Callable[[StepResult], None] | None = None) -> "DrillResult":
        while not self.done:
            res = self.step()
            if progress:
                progress(res)
        return self.finish()

    def pause(self) -> None:
        self.status = "paused"
        self.ledger.append("CONTROL", "FACILITATOR", {"action": "pause", "next_event": self.index + 1})

    def resume(self) -> None:
        self.status = "running"
        self.ledger.append("CONTROL", "FACILITATOR", {"action": "resume", "next_event": self.index + 1})

    def inject_surprise(self, text: str, to: list[str], required_actions: list[str] | None = None,
                        sim_time: str | None = None, severity: int = 2) -> None:
        """Facilitator adds an unplanned event, played next."""
        from alerte.models import Event
        new_id = max(e.id for e in self.scenario.events) + 1
        ev = Event(id=new_id, sim_time=sim_time or (self.next_event.sim_time if self.next_event else "END"),
                   to=[c for c in to if c in self.seats], sender="FACILITATOR", text={self.lang: text},
                   required_actions=required_actions or [], severity=severity)
        self.scenario.events.insert(self.index, ev)
        self.ledger.append("CONTROL", "FACILITATOR", {"action": "surprise_event", "event": ev.model_dump(mode="json")})

    def finish(self) -> "DrillResult":
        from alerte.analysis.report import write_outputs
        result = write_outputs(self)
        self.status = "finished"
        return result


@dataclass
class DrillResult:
    run_id: str
    run_dir: Path
    summary: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({"run_id": self.run_id, "run_dir": str(self.run_dir), **self.summary}, indent=2, default=str)
