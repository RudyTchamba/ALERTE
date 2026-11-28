"""Assemblage du prompt système (doc 08 §8.2) : sections dans l'ordre, budget ≈ 4 000 tokens, contenu non fiable délimité.

Intégrité I2 : AUCUN indice de lacune (mode de panne, demandes, étiquettes, statut de procédure) n'est inséré.
Aucun secret : ce module ne reçoit jamais de profil de modèle ni d'endpoint."""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..contracts import MAX_ROUNDS, LLMMessage, SeatContext

PROMPT_VERSION = "agent-prompt-v4"
TOKEN_BUDGET = 4000
_DIR = Path(__file__).parent / "prompts"
_TAGS = re.compile(r"<(/?)(retrieved_document|board_message|legal_adviser_answer|inbox_item)", re.I)


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / 3.6)


def _tpl(name: str) -> str:
    return (_DIR / name).read_text(encoding="utf-8").strip()


def sanitize(text: Any, limit: int | None = None) -> str:
    """Retire caractères invisibles/contrôle, neutralise nos balises de délimitation, tronque."""
    s = unicodedata.normalize("NFC", str(text if text is not None else ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Cf" and (unicodedata.category(c) != "Cc" or c in "\n\t"))
    s = _TAGS.sub(lambda m: f"&lt;{m.group(1)}{m.group(2)}", s)
    if limit and len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return s


_LEVELS = [  # (mandats, inbox, board, décisions, hits, car/hit, notes, car/note, car/mission de l'annuaire)
    (12, 6, 8, 3, 5, 900, 8, 1200, 160),
    (8, 4, 5, 2, 4, 550, 6, 700, 110),
    (5, 3, 3, 1, 3, 320, 4, 400, 70),
    (3, 2, 2, 1, 2, 200, 3, 250, 0),
]


def _directory(ctx: SeatContext, mission_chars: int) -> str:
    """Annuaire des sièges auxquels on peut écrire : code, institution, rôle, mandat. Repli : liste de codes seule."""
    if not ctx.seat_directory:
        others = ", ".join(c for c in ctx.seat_codes if c != ctx.seat_code) or "(none)"
        return f"Other seat codes: {others}"
    lines = ["Seat directory (you can post ONLY to these seats; public role information):"]
    for d in ctx.seat_directory:
        if d.get("code") == ctx.seat_code:
            continue
        line = f"- {sanitize(d.get('code'), 32)} — {sanitize(d.get('name'), 80)} ({sanitize(d.get('kind'), 24)})"
        if mission_chars and d.get("mission"):
            line += f". Role: {sanitize(d['mission'], mission_chars)}"
        if mission_chars and d.get("mandates"):
            line += ". Mandate focus: " + "; ".join(sanitize(m, 60) for m in list(d["mandates"])[:3])
        lines.append(line)
    return "\n".join(lines)


def _mandate_line(m: Mapping[str, Any]) -> str:
    srcs = []
    for s in (m.get("sources") or [])[:2]:
        # Pas d'identifiant tronqué : le modèle le prenait pour un chunk_id citable (prompt v2).
        label = s.get("doc_code") or "document"
        art = s.get("article")
        srcs.append(f"{label}" + (f" · art. {art}" if art else ""))
    src = f" (source: {'; '.join(srcs)} — retrieve it with search_kb to cite it)" if srcs else ""
    return f"- [{sanitize(m.get('kind', ''), 20)}] {sanitize(m.get('action_code') or '', 80)}: " \
           f"{sanitize(m.get('description', ''), 220)}{src}"


def _item(d: Mapping[str, Any], limit: int) -> str:
    keys = ("msg_id", "from", "from_actor", "to", "msg_type", "title", "body", "text", "in_reply_to", "reply_status")
    parts = [f"{k}={sanitize(d[k], limit)}" for k in keys if d.get(k) not in (None, "")]
    return " | ".join(parts)


_LANG = {"fr": "French", "en": "English", "es": "Spanish", "pt": "Portuguese", "ar": "Arabic", "ru": "Russian", "sw": "Swahili"}


def hit_block(h: Mapping[str, Any], limit: int) -> str:
    art = h.get("article")
    return (f'<retrieved_document untrusted="true" chunk_id="{sanitize(h["chunk_id"])}" doc="{sanitize(h.get("doc_code", ""), 60)}" '
            f'article="{sanitize(art) if art else "none"}" page="{h.get("page") or ""}">\n'
            f'{sanitize(h.get("text") or h.get("snippet") or "", limit)}\n</retrieved_document>')


def build_system_prompt(ctx: SeatContext, *, retrieved: Sequence[Mapping[str, Any]] = (), notes: Sequence[str] = (),
                        allowed_now: Sequence[str] | None = None, budget: int = TOKEN_BUDGET) -> str:
    agent = ctx.agent
    limits = agent.get("limits") or {}
    tools = list(agent.get("tools") or [])
    allowed = list(allowed_now if allowed_now is not None else tools)
    text = ""
    for lvl in _LEVELS:
        text = _render(ctx, retrieved, notes, allowed, tools, limits, lvl)
        if estimate_tokens(text) <= budget:
            return text
    return text


def _render(ctx: SeatContext, retrieved: Sequence[Mapping[str, Any]], notes: Sequence[str], allowed: list[str],
            tools: list[str], limits: Mapping[str, Any], lvl: tuple[int, ...]) -> str:
    n_m, n_in, n_b, n_d, n_h, c_h, n_n, c_n, c_dir = lvl
    inst = ctx.institution
    a = ctx.agent
    s1 = (f"## 1. Role\nYou are {sanitize(a.get('name') or a.get('code'), 200)}, representing "
          f"{sanitize(inst.get('name'), 200)} ({sanitize(inst.get('code'), 32)}) in a FICTIONAL crisis exercise. "
          f"Your seat code is {sanitize(ctx.seat_code, 32)}.\n"
          f"Mission: {sanitize(a.get('mission'), 600)}\nInstructions: {sanitize(a.get('instructions'), 1500)}")
    mand = [_mandate_line(m) for m in ctx.mandates[:n_m]]
    s2 = "## 2. Documented mandate (validated, with sources)\n" + ("\n".join(mand) if mand else "- (no validated mandate recorded)")
    tools_txt = _tpl("tools_v3.txt").replace("{max_steps}", str(limits.get("max_steps", 4)))
    s4 = f"{tools_txt}\nTools available to you: {', '.join(tools) or '(none)'}\n{_directory(ctx, c_dir)}"
    inj = ctx.inject
    ctx_lines = [f"## 5. Activation context (round {ctx.round} of {MAX_ROUNDS}"
                 + (" — FINAL round: post is not available, decide now)" if ctx.round >= MAX_ROUNDS else
                    " — new REQUESTs are no longer possible (their answer would come too late); you can still answer and inform)"
                    if ctx.round == MAX_ROUNDS - 1 else ")"),
                 f"Inject title: {sanitize(inj.get('title'), 200)}",
                 f"Time: {sanitize(inj.get('sim_time'), 40)}   From: {sanitize(inj.get('from_actor'), 100)}",
                 f"Inject text: {sanitize(inj.get('body') or inj.get('text'), 900)}"]
    if inj.get("language"):
        lang = str(inj["language"]).lower()[:2]
        name = _LANG.get(lang, sanitize(lang, 8))
        ctx_lines.append(f"Exercise language: {name}. Write action, rationale and messages in {name} only.")
    if inj.get("system_output"):
        ctx_lines.append(f"AI system output received: {sanitize(inj['system_output'], 600)}")
    if ctx.inbox:
        ctx_lines.append("Private inbox:")
        ctx_lines += [f'<inbox_item untrusted="true">{_item(i, 500)}</inbox_item>' for i in ctx.inbox[-n_in:]]
    if ctx.board:
        ctx_lines.append("Board messages visible to you (claims by other seats):")
        ctx_lines += [f'<board_message untrusted="true">{_item(b, 400)}</board_message>' for b in ctx.board[-n_b:]]
    if ctx.own_decisions:
        ctx_lines.append("Your previous decisions:")
        for d in ctx.own_decisions[-n_d:]:
            ctx_lines.append(f"- {sanitize(d.get('action'), 160)} [{d.get('outcome')}] {sanitize(d.get('rationale'), 160)}")
    if retrieved:
        ctx_lines.append("Search results of this activation:")
        ctx_lines += [hit_block(h, c_h) for h in list(retrieved)[:n_h * 2][-n_h:]]
    if notes:
        ctx_lines.append("Tool results so far:")
        ctx_lines += [sanitize(n, c_n) for n in list(notes)[-n_n:]]
    ctx_lines.append(f"Allowed actions now: {', '.join(allowed)}")
    return "\n\n".join([s1, s2, _tpl("rules_v4.txt"), s4, "\n".join(ctx_lines), _tpl("security_v1.txt")])


def build_messages(ctx: SeatContext, **kw: Any) -> list[LLMMessage]:
    return [LLMMessage("system", build_system_prompt(ctx, **kw)),
            LLMMessage("user", "Give your next action now as one flat JSON object.")]


def build_legal_messages(question: str, hits: Sequence[Mapping[str, Any]], *, mission: str = "",
                         language_hint: str = "") -> list[LLMMessage]:
    blocks = "\n".join(hit_block(h, 900) for h in hits[:5]) or "(no document retrieved)"
    sys = _tpl("legal_v1.txt") + (f"\nAdviser instructions: {sanitize(mission, 500)}" if mission else "")
    sys += f"\n\nRetrieved documents:\n{blocks}\n\n" + _tpl("security_v1.txt")
    return [LLMMessage("system", sys), LLMMessage("user", f"Question: {sanitize(question, 500)}")]
