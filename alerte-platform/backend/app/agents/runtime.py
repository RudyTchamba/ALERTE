"""Runtime d'agents : boucle d'activation contrôlée par le backend (doc 08 §8.3-8.6).

Le runtime ne parle ni au ledger ni à la base d'exercice : il renvoie un `ActivationResult` (événements `ToolEvent`,
messages postés, décision) que la simulation écrit dans SA transaction. L'identité (scope) vient du `SeatContext`,
jamais d'un paramètre du modèle."""
from __future__ import annotations

import json
import re
import threading
import unicodedata
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from ..contracts import (
    MAX_ROUNDS,
    ActivationResult,
    LLMMessage,
    PostedMessage,
    RawCompletion,
    SearchScope,
    SeatContext,
    ToolEvent,
)
from ..core.config import Settings
from ..core.db import session_scope
from ..core.ids import new_id
from . import envelope as env
from .citations import check_citations
from .prompt import build_legal_messages, build_messages
from .providers import ProviderUnavailable, provider_for, request_bytes, sanitize_endpoint  # noqa: F401

CLOSING = "For exercise purposes only; confirm with a qualified lawyer."
FINAL_TOOLS = ("decide",)  # au pas final : décider (un `post` final terminerait l'activation SANS décision)
SEARCH_K = 8  # résultats par recherche : assez pour atteindre la loi derrière les documents généraux
DEFAULT_LIMITS = {"max_steps": 4, "max_search_calls": 3, "max_legal_calls": 2}



LANG_NAMES = {"fr": "French", "en": "English", "es": "Spanish", "pt": "Portuguese", "ar": "Arabic", "ru": "Russian",
              "sw": "Swahili", "de": "German", "it": "Italian"}
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
_CJK_LANGS = ("zh", "ja", "ko")


def wrong_script(text: str, language: str | None) -> str | None:
    """Un exercice dans une langue sans idéogrammes ne doit pas recevoir de texte chinois, japonais ou coréen
    (dérive observée des petits modèles multilingues). Renvoie le motif de rejet, ou None."""
    lang = (language or "").lower()[:2]
    if not lang or lang in _CJK_LANGS or not _CJK.search(text or ""):
        return None
    return f"text must be written in {LANG_NAMES.get(lang, lang)} only (no Chinese, Japanese or Korean characters)"

class _Outage(Exception):
    pass


class _Budget(Exception):
    pass


def clean(text: Any) -> str:
    s = unicodedata.normalize("NFC", str(text if text is not None else ""))
    return "".join(c for c in s if unicodedata.category(c) not in ("Cf",) and (unicodedata.category(c) != "Cc" or c in "\n\t"))


def _norm_query(q: str) -> str:
    return " ".join(q.casefold().split())


def _hit_dict(h: Any) -> dict[str, Any]:
    g = (lambda k, d=None: h.get(k, d)) if isinstance(h, dict) else (lambda k, d=None: getattr(h, k, d))
    return {"chunk_id": g("chunk_id"), "doc_code": g("doc_code", ""), "article": g("article"), "page": g("page"),
            "text": g("text", "") or g("snippet", ""), "score": float(g("score", 0.0) or 0.0),
            "signals": g("signals", {}) or {}}


class _Run:
    def __init__(self, ctx: SeatContext) -> None:
        self.ctx = ctx
        self.events: list[ToolEvent] = []
        self.messages: list[PostedMessage] = []
        self.retrieved: dict[str, dict[str, Any]] = {}
        self.notes: list[str] = []
        self.search_cache: dict[str, list[str]] = {}
        self.searches = 0
        self.legals = 0
        self.calls = 0
        self.force_final = False
        self.cite_retry_used = False
        self.provider: Any = None
        self.legal_provider: Any = None
        self.decision: dict[str, Any] | None = None

    def ev(self, type_: str, payload: dict[str, Any], visibility: str = "audit") -> None:
        self.events.append(ToolEvent(type_, payload, visibility))

    def tool_call(self, tool: str, args: dict[str, Any], rationale: str, ok: bool, error: str | None = None) -> None:
        self.ev("TOOL_CALL", {"tool": tool, "args": args, "rationale": clean(rationale), "ok": ok, "error": error}, "seat")

    def error(self, component: str, message: str, next_action: str) -> None:
        self.ev("ERROR", {"component": component, "message": message, "next_action": next_action}, "audit")


class AgentRuntime:
    """Implémente `contracts.AgentRuntimePort`."""

    def __init__(self, settings: Settings, blobs: Any, services: dict[str, Any], session_factory: Any = None,
                 provider_factory: Callable[[Any, Settings], Any] | None = None) -> None:
        self.settings, self.blobs, self.services, self._sf = settings, blobs, services, session_factory
        self._factory = provider_factory or (lambda profile, s: provider_for(profile, s, blobs=blobs))
        self._calls: dict[str, int] = {}
        self._lock = threading.Lock()

    # ----- budget
    def calls_used(self, exercise_id: str) -> int:
        return self._calls.get(exercise_id, 0)

    def set_calls_used(self, exercise_id: str, n: int) -> None:
        """Reprise après redémarrage : la simulation recompte les LLM_CALL du ledger."""
        with self._lock:
            self._calls[exercise_id] = n

    def _reserve(self, run: _Run) -> bool:
        """Réserve un appel au modèle. Le budget de l'EXERCICE fait foi : le moteur transmet `budget_remaining`
        (plafond de l'exercice + extension - appels déjà consommés) et l'activation ne peut pas le dépasser.
        Sans `budget_remaining` (appel hors moteur, ex. conseiller d'un siège humain), on retombe sur le plafond
        serveur `ALERTE_MAX_LLM_CALLS` appliqué au compteur du processus. `_calls` reste un compteur d'observation."""
        exercise_id = run.ctx.exercise_id
        remaining = run.ctx.agent.get("budget_remaining")
        with self._lock:
            used = self._calls.get(exercise_id, 0)
            if remaining is not None:
                if run.calls >= int(remaining):
                    return False
            elif used >= self.settings.max_llm_calls:
                return False
            self._calls[exercise_id] = used + 1
            return True

    @contextmanager
    def _session(self) -> Iterator[Any]:
        if self._sf is None:
            yield None
        else:
            with session_scope(self._sf) as s:
                yield s

    def _svc(self, name: str) -> Any:
        return self.services.get(name)

    # ----- LLM
    def _llm(self, run: _Run, messages: list[LLMMessage], schema: dict[str, Any] | None, key: str, *, retried: bool,
             legal: bool = False) -> tuple[RawCompletion, dict[str, Any]]:
        if not self._reserve(run):
            raise _Budget()
        run.calls += 1
        profile = run.ctx.agent.get("model_profile") or {"provider": self.settings.llm_mode}
        if legal and (run.ctx.agent.get("legal_adviser") or {}).get("model_profile"):
            profile = run.ctx.agent["legal_adviser"]["model_profile"]
        attr = "legal_provider" if legal else "provider"
        try:
            if getattr(run, attr) is None:
                setattr(run, attr, self._factory(profile, self.settings))
            prov = getattr(run, attr)
            req_sha = self.blobs.put_bytes(request_bytes(messages, schema))
            kwargs: dict[str, Any] = {"schema": schema, "temperature": float(profile.get("temperature") or 0.0),
                                      "max_tokens": profile.get("max_tokens")}
            if getattr(prov, "uses_step_key", False):
                kwargs["step_key"] = key
            raw = prov.complete(messages, **kwargs)
        except ProviderUnavailable as exc:
            run.error("llm_provider", clean(str(exc))[:300], "fallback decide")
            raise _Outage(str(exc)) from exc
        resp_sha = self.blobs.put_bytes(raw.text.encode("utf-8"))
        payload = {"provider": raw.provider, "model": raw.model, "endpoint": raw.endpoint, "step_key": key,
                   "request_blob_sha256": req_sha, "response_blob_sha256": resp_sha, "tokens_in": raw.tokens_in,
                   "tokens_out": raw.tokens_out, "ms": raw.ms, "valid": True, "retried": retried}
        run.ev("LLM_CALL", payload, "audit")
        return raw, payload

    def _ask(self, run: _Run, base: list[LLMMessage], schema: dict[str, Any], key: str, allowed: list[str]
             ) -> tuple[Any, str]:
        """Un pas : appel, validation, 1 relance. Renvoie (action, 'ok') ou (None, 'invalid'|'cut')."""
        tools = list(run.ctx.agent.get("tools") or [])
        raw, pl = self._llm(run, base, schema, key, retried=False)
        act, err = env.parse_envelope(raw.text)
        if act is not None and (bad := wrong_script(act.model_dump_json(), run.ctx.inject.get("language"))):
            act, err = None, bad
        if act is not None and act.action in tools and act.action not in allowed:
            err = f"action '{act.action}' is not allowed now; allowed actions: {', '.join(allowed)}"
            kind = "cut"
            act = None
        else:
            kind = "invalid"
        if act is not None:
            return act, "ok"
        pl["valid"] = False
        run.error("agent_output", f"invalid output: {err}"[:300], "retry once")
        retry_msgs = base + [LLMMessage("assistant", raw.text[:1500]),
                             LLMMessage("user", f"Your reply was rejected: {err}. Reply again with one valid JSON object.")]
        raw2, pl2 = self._llm(run, retry_msgs, schema, key + ":r", retried=True)
        act2, err2 = env.parse_envelope(raw2.text)
        if act2 is not None and (bad2 := wrong_script(act2.model_dump_json(), run.ctx.inject.get("language"))):
            act2, err2 = None, bad2
        if act2 is not None and act2.action in tools and act2.action not in allowed:
            err2, act2, kind = f"action '{act2.action}' is not allowed now", None, "cut"
        if act2 is None:
            pl2["valid"] = False
            run.error("agent_output", f"invalid output after retry: {err2}"[:300], "not recorded" if kind == "invalid" else "fallback")
            run.last_error = err2  # type: ignore[attr-defined]
            return None, kind
        return act2, "ok"

    # ----- décisions
    def _decision_payload(self, run: _Run, did: str, dec: env.Decision | None, rationale: str, status: str, author: str,
                          basis: list[dict[str, Any]]) -> dict[str, Any]:
        ctx = run.ctx
        base = {"decision_id": did, "seat_code": ctx.seat_code, "inject_ref": ctx.inject.get("inject_ref"),
                "round": ctx.round, "rationale": clean(rationale), "status": status, "author": author}
        if dec is None:
            return {**base, "action": None, "action_code": None, "outcome": None, "confidence": None,
                    "options_considered": [], "gap_flags": [], "evidence_tag": None, "legal_basis": []}
        return {**base, "action": clean(dec.action), "action_code": dec.action_code, "outcome": dec.outcome,
                "confidence": dec.confidence, "options_considered": [clean(o) for o in dec.options_considered],
                "gap_flags": [{"hint": f.hint, "text": clean(f.text)} for f in dec.gap_flags],
                "evidence_tag": dec.evidence_tag, "legal_basis": basis}

    def _fallback(self, run: _Run, reason: str) -> ActivationResult:
        did = new_id()
        dec = env.Decision.model_construct(action="Refer: no automated decision available", action_code=None,
                                           outcome="refer", confidence="low", evidence_tag="assumed", legal_basis=[],
                                           options_considered=[], gap_flags=[])
        run.decision = self._decision_payload(run, did, dec, f"fallback: {reason}", "recorded", "fallback", [])
        run.ev("DECISION", run.decision, "public")
        return self._result(run, "fallback", "fallback")

    def _result(self, run: _Run, status: str, author: str = "agent") -> ActivationResult:
        return ActivationResult(decision=run.decision, messages=run.messages, events=run.events, llm_calls=run.calls,
                                status=status, author=author)

    def _check(self, run: _Run, did: str, dec: env.Decision) -> list[Any]:
        with self._session() as s:
            res = check_citations(self._svc("knowledge"), s, [b.model_dump() for b in dec.legal_basis],
                                  scope=run.ctx.scope, retrieval_set=set(run.retrieved))
        run.ev("CITATION_CHECK", {"decision_id": did, "citations": [
            {"chunk_id": r.chunk_id, "pass": r.passed, "reason": r.reason} for r in res]}, "audit")
        return res

    @staticmethod
    def _cite_hint(run: _Run, r: Any) -> str:
        """Consigne de correction précise pour une citation refusée (valeurs attendues tirées des seuls blocs récupérés)."""
        hit = run.retrieved.get(r.chunk_id)
        if r.reason == "article_mismatch" and hit is not None:
            art = hit.get("article")
            return (f'chunk {r.chunk_id}: set "article" to ' + (f'"{art}"' if art else "null")
                    + " (the article attribute of that retrieved_document).")
        if r.reason in ("unknown_chunk", "not_in_retrieval_set", "out_of_scope"):
            ids = ", ".join(run.retrieved) or "(none: call search_kb first)"
            return f"chunk {r.chunk_id or '(empty)'}: not a retrieved chunk_id. Use one of: {ids}."
        if r.reason in ("quote_not_in_chunk", "quote_too_short"):
            return (f'chunk {r.chunk_id}: "quote" must be 20+ consecutive characters copied exactly from the text of '
                    "that retrieved_document.")
        return f"chunk {r.chunk_id}: {r.reason}."

    def _action_code_ok(self, run: _Run, code: str | None) -> bool:
        mandates = self._svc("mandates")
        if not code or mandates is None or not hasattr(mandates, "action_exists"):
            return True
        try:
            with self._session() as s:
                return bool(mandates.action_exists(s, run.ctx.workspace_id, code))
        except Exception:  # noqa: BLE001 - service optionnel : ne bloque pas l'activation
            return True

    def _handle_decide(self, run: _Run, act: env.DecideAction, base: list[LLMMessage], key: str) -> None:
        did, dec = new_id(), act.decision
        rationale = act.rationale
        run.tool_call("decide", {"decision": dec.model_dump()}, rationale, True)
        if not self._action_code_ok(run, dec.action_code):
            run.error("decision", f"unknown action_code '{dec.action_code}' nulled", "continue")
            dec = dec.model_copy(update={"action_code": None})
        res = self._check(run, did, dec)
        if any(not r.passed for r in res) and not run.cite_retry_used:
            run.cite_retry_used = True
            fails = "; ".join(f"{r.chunk_id}: {r.reason}" for r in res if not r.passed)
            hints = "\n".join(f"- {self._cite_hint(run, r)}" for r in res if not r.passed)
            submitted = json.dumps({"action": "decide", "rationale": rationale, "decision": dec.model_dump()},
                                   ensure_ascii=False)
            msgs = base + [LLMMessage("assistant", submitted[:3000]),
                           LLMMessage("user", f"Citation check failed: {fails}.\n{hints}\nReply with a corrected decide action: "
                                              "cite only chunks you retrieved, with exact quotes, or use outcome "
                                              "no_legal_basis_found.")]
            try:
                raw, pl = self._llm(run, msgs, env.envelope_schema(["decide"]), key + ":c", retried=True)
            except _Outage:
                raw = None
            if raw is not None:
                act2, err = env.parse_envelope(raw.text)
                if isinstance(act2, env.DecideAction):
                    dec, rationale = act2.decision, act2.rationale
                    res = self._check(run, did, dec)
                else:
                    pl["valid"] = False
        status = "recorded" if all(r.passed for r in res) else "not_verified"
        run.decision = self._decision_payload(run, did, dec, rationale, status, "agent", [r.as_basis() for r in res])
        run.ev("DECISION", run.decision, "public")

    # ----- outils
    def _do_search(self, run: _Run, act: env.SearchAction) -> None:
        ctx, limits = run.ctx, {**DEFAULT_LIMITS, **(run.ctx.agent.get("limits") or {})}
        q = act.query
        args = {"query": q}
        nq = _norm_query(q)
        if nq in run.search_cache:
            run.force_final = True
            run.notes.append(f"search_kb({q!r}): duplicate query, results unchanged (ids: {', '.join(run.search_cache[nq])}). "
                             "Do not repeat searches; decide or post now.")
            run.tool_call("search_kb", args, act.rationale, True, "duplicate_query")
            return
        if run.searches >= limits["max_search_calls"]:
            run.notes.append("search_kb refused: search budget exhausted.")
            run.tool_call("search_kb", args, act.rationale, False, "search_budget_exhausted")
            return
        if ctx.scope.is_empty or self._svc("search") is None:
            run.notes.append("search_kb: no knowledge base is granted to you.")
            run.tool_call("search_kb", args, act.rationale, False, "no_knowledge_granted")
            return
        run.searches += 1
        try:
            hits = [_hit_dict(h) for h in self._svc("search").search(ctx.scope, q, k=SEARCH_K)]
        except Exception as exc:  # noqa: BLE001 - la recherche peut refuser (index incohérent…)
            run.error("search", clean(str(exc))[:300], "continue")
            run.notes.append("search_kb: search unavailable.")
            run.tool_call("search_kb", args, act.rationale, False, "search_unavailable")
            return
        run.search_cache[nq] = [h["chunk_id"] for h in hits]
        for h in hits:
            run.retrieved[h["chunk_id"]] = h
        sig = {k: any(bool(h["signals"].get(k)) for h in hits) for k in ("lexical", "dense", "degraded")}
        run.ev("RETRIEVAL", {"query": q, "scope_hash": ctx.scope.scope_hash(), "results": [
            {"chunk_id": h["chunk_id"], "score": h["score"], "rank": i + 1} for i, h in enumerate(hits)],
            "signals": sig}, "seat")
        run.notes.append(f"search_kb({q!r}): {len(hits)} result(s): {', '.join(h['chunk_id'] for h in hits) or 'none'}.")
        run.tool_call("search_kb", args, act.rationale, True)

    def _do_legal(self, run: _Run, act: env.AskLegalAction) -> None:
        ctx, limits = run.ctx, {**DEFAULT_LIMITS, **(run.ctx.agent.get("limits") or {})}
        args = {"question": act.question}
        if run.legals >= limits["max_legal_calls"]:
            run.notes.append("ask_legal refused: legal adviser budget exhausted.")
            run.tool_call("ask_legal", args, act.rationale, False, "legal_budget_exhausted")
            return
        run.legals += 1
        n = run.legals
        scope: SearchScope = ctx.agent.get("legal_scope") if isinstance(ctx.agent.get("legal_scope"), SearchScope) else ctx.scope
        hits: list[dict[str, Any]] = []
        if not scope.is_empty and self._svc("search") is not None:
            try:
                hits = [_hit_dict(h) for h in self._svc("search").search(scope, act.question, k=5)]
            except Exception as exc:  # noqa: BLE001
                run.error("search", clean(str(exc))[:300], "continue")
            run.ev("RETRIEVAL", {"query": act.question, "scope_hash": scope.scope_hash(), "results": [
                {"chunk_id": h["chunk_id"], "score": h["score"], "rank": i + 1} for i, h in enumerate(hits)],
                "signals": {k: any(bool(h["signals"].get(k)) for h in hits) for k in ("lexical", "dense", "degraded")}}, "seat")
        msgs = build_legal_messages(act.question, hits, mission=(ctx.agent.get("legal_adviser") or {}).get("instructions", ""))
        key = f"{ctx.step_key}:l{n}"
        raw, pl = self._llm(run, msgs, env.LEGAL_SCHEMA, key, retried=False, legal=True)
        ans, err = env.parse_legal(raw.text)
        if ans is None:
            pl["valid"] = False
            raw, pl = self._llm(run, msgs + [LLMMessage("assistant", raw.text[:1500]),
                                             LLMMessage("user", f"Rejected: {err}. Reply again with one valid JSON object.")],
                                env.LEGAL_SCHEMA, key + ":r", retried=True, legal=True)
            ans, err = env.parse_legal(raw.text)
            if ans is None:
                pl["valid"] = False
                run.error("legal_adviser", f"invalid output after retry: {err}"[:300], "continue")
                run.notes.append("ask_legal: the adviser gave no valid answer.")
                run.tool_call("ask_legal", args, act.rationale, False, "legal_invalid_output")
                return
        answer_id = new_id()
        ids = {h["chunk_id"] for h in hits}
        all_cites = [c.model_dump() for cl in ans.what_the_texts_say for c in cl.cites] + \
                    [c.model_dump() for p in ans.what_others_do for c in p.cites]
        with self._session() as s:
            results = check_citations(self._svc("knowledge"), s, all_cites, scope=scope, retrieval_set=ids)
        run.ev("CITATION_CHECK", {"answer_id": answer_id, "citations": [
            {"chunk_id": r.chunk_id, "pass": r.passed, "reason": r.reason} for r in results]}, "audit")
        ok = {(r.chunk_id, r.quote) for r in results if r.passed}

        def verified(cites: list[env.LegalBasisItem]) -> bool:
            return bool(cites) and all((c.chunk_id, c.quote) in ok for c in cites)

        says = [c for c in ans.what_the_texts_say if verified(c.cites)]
        others = [p for p in ans.what_others_do if verified(p.cites)]
        removed = (len(ans.what_the_texts_say) - len(says)) + (len(ans.what_others_do) - len(others))
        to_check = list(ans.what_to_check) + ([f"{removed} claim(s) removed: citation could not be verified"] if removed else [])
        for r in results:
            if r.passed and r.chunk_id in {h["chunk_id"] for h in hits}:
                run.retrieved.setdefault(r.chunk_id, next(h for h in hits if h["chunk_id"] == r.chunk_id))
        lines = ["What the texts say:"] + [f"- {clean(c.claim)} " + " ".join(
            f"[{x.chunk_id}" + (f" art. {x.article}" if x.article else "") + "]" for x in c.cites) for c in says]
        lines += ["What the texts do not say (queries run: " + "; ".join([act.question[:120]]) + "):"] + \
                 [f"- {clean(g.point)}" for g in ans.what_they_do_not_say]
        lines += ["What others do:"] + [f"- {clean(p.jurisdiction)} / {clean(p.instrument)}: {clean(p.summary)}" for p in others]
        lines += ["What to check:"] + [f"- {clean(t)}" for t in to_check] + [CLOSING]
        run.notes.append('<legal_adviser_answer untrusted="true">\n' + "\n".join(lines) + "\n</legal_adviser_answer>")
        run.tool_call("ask_legal", args, act.rationale, True)
        run.legal_answers = getattr(run, "legal_answers", []) + [  # type: ignore[attr-defined]
            {"answer_id": answer_id, "what_the_texts_say": [c.model_dump() for c in says],
             "what_they_do_not_say": [{"point": g.point, "searched_queries": [act.question]} for g in ans.what_they_do_not_say],
             "what_others_do": [p.model_dump() for p in others], "what_to_check": to_check, "closing": CLOSING}]

    def _do_post(self, run: _Run, act: env.PostAction) -> bool:
        ctx = run.ctx
        args = act.model_dump(exclude={"rationale", "action"})
        err = None
        if ctx.round >= MAX_ROUNDS:
            err = "round_limit"
        elif act.msg_type == "REQUEST" and ctx.round >= MAX_ROUNDS - 1:
            err = "request_too_late"  # sa réponse tomberait au dernier tour, où l'on ne peut plus poster : demande orpheline assurée
        elif act.to not in ctx.seat_codes:
            err = "unknown_recipient"
        elif act.to == ctx.seat_code:
            err = "self_recipient"
        elif act.reply_status is not None:
            ref = next((m for m in [*ctx.board, *ctx.inbox] if m.get("msg_id") == act.in_reply_to), None) if act.in_reply_to else None
            if ref is None or (ref.get("msg_type") or ref.get("type")) != "REQUEST":
                err = "reply_status_requires_request"
        if err:
            run.notes.append(f"post refused: {err}.")
            run.tool_call("post", args, act.rationale, False, err)
            return False
        run.messages.append(PostedMessage(to=act.to, msg_type=act.msg_type, body=clean(act.message),
                                          in_reply_to=act.in_reply_to, reply_status=act.reply_status))
        run.notes.append(f"post to {act.to} ({act.msg_type}): sent.")
        run.tool_call("post", args, act.rationale, True)
        return True

    # ----- activation
    def ask_legal(self, ctx: SeatContext, question: str) -> dict[str, Any]:
        """Question d'un siège HUMAIN au conseiller juridique (même pipeline et mêmes contrôles que pour un agent).

        Renvoie `{answer, structured, retrieved_chunk_ids, events, llm_calls, ok}` ; la simulation écrit les événements."""
        run = _Run(ctx)
        try:
            self._do_legal(run, env.AskLegalAction(action="ask_legal", rationale="human question", question=question))
        except _Budget:
            run.error("budget", f"LLM call budget reached ({self.settings.max_llm_calls})", "refuse")
            return {"ok": False, "reason": "budget_exhausted", "answer": None, "structured": None,
                    "retrieved_chunk_ids": [], "events": run.events, "llm_calls": run.calls}
        except _Outage:
            return {"ok": False, "reason": "model_unavailable", "answer": None, "structured": None,
                    "retrieved_chunk_ids": [], "events": run.events, "llm_calls": run.calls}
        structured = (getattr(run, "legal_answers", None) or [None])[-1]
        tc = [e for e in run.events if e.type == "TOOL_CALL" and e.payload.get("tool") == "ask_legal"]
        ok = bool(structured) and all(e.payload.get("ok") for e in tc)
        events = [e for e in run.events if e.type != "TOOL_CALL"]  # le TOOL_CALL est écrit par la simulation
        return {"ok": ok, "reason": None if ok else (tc[-1].payload.get("error") if tc else "no_answer"),
                "answer": run.notes[-1] if ok else None, "structured": structured,
                "retrieved_chunk_ids": sorted(run.retrieved), "events": events, "llm_calls": run.calls}

    def activate(self, ctx: SeatContext) -> ActivationResult:
        run = _Run(ctx)
        if ctx.agent.get("role_kind") == "ai_system":  # joué par `inject.system_output`, jamais par un LLM
            return ActivationResult()
        tools = list(ctx.agent.get("tools") or [])
        limits = {**DEFAULT_LIMITS, **(ctx.agent.get("limits") or {})}
        if ctx.inject.get("fault_mode") == "llm_outage" and ctx.round == 1:
            run.error("llm_provider", "simulated outage (fault_mode=llm_outage)", "fallback decide")
            return self._fallback(run, "model unavailable")
        try:
            return self._loop(run, tools, limits)
        except _Outage:
            return self._fallback(run, "model unavailable")
        except _Budget:
            run.error("budget", f"LLM call budget reached ({self.settings.max_llm_calls})", "pause")
            return self._result(run, "budget_exhausted")

    def _loop(self, run: _Run, tools: list[str], limits: dict[str, int]) -> ActivationResult:
        ctx = run.ctx
        max_steps = limits["max_steps"]
        for step in range(1, max_steps + 1):
            final = step == max_steps or run.force_final
            allowed = [t for t in tools if not final or t in FINAL_TOOLS]
            if ctx.round >= MAX_ROUNDS:  # dernier tour : un message ne serait livré à personne -> on ne peut que décider
                allowed = [t for t in allowed if t != "post"]
            if not allowed:
                break
            base = build_messages(ctx, retrieved=list(run.retrieved.values()), notes=run.notes, allowed_now=allowed)
            key = f"{ctx.step_key}:s{step}"
            act, kind = self._ask(run, base, env.envelope_schema(allowed), key, allowed)
            if act is None:
                if kind == "invalid":
                    return self._not_recorded(run, getattr(run, "last_error", "invalid output"))
                run.error("agent_loop", f"step limit reached without a valid final action (max_steps={max_steps})", "fallback decide")
                return self._fallback(run, "step limit reached")
            if act.action not in tools:
                run.notes.append(f"{act.action} refused: tool not allowed for this seat.")
                run.tool_call(act.action, {}, act.rationale, False, "tool_not_allowed")
                continue
            if act.action == "search_kb":
                self._do_search(run, act)
            elif act.action == "ask_legal":
                self._do_legal(run, act)
            elif act.action == "post":
                ok = self._do_post(run, act)
                if ok and final:
                    return self._result(run, "ok")
            elif act.action == "decide":
                self._handle_decide(run, act, base, key)
                return self._result(run, "ok")
        if run.messages and any(e.type == "TOOL_CALL" and e.payload["tool"] == "post" and e.payload["ok"] for e in run.events):
            return self._result(run, "ok")
        run.error("agent_loop", "no decision produced within max_steps", "fallback decide")
        return self._fallback(run, "step limit reached")

    def _not_recorded(self, run: _Run, err: str) -> ActivationResult:
        did = new_id()
        run.decision = self._decision_payload(run, did, None, "not recorded: invalid model output after retry",
                                              "not_recorded", "agent", [])
        run.ev("DECISION", run.decision, "public")
        return self._result(run, "not_recorded")
