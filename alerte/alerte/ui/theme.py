"""Look and feel: CSS, small HTML helpers, EN/FR labels."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

CSS = """
<style>
.block-container{padding-top:1.2rem;max-width:1500px}
.banner{background:#b3261e;color:#fff;padding:.4rem .9rem;border-radius:8px;font-weight:600;margin-bottom:.7rem;font-size:.92rem}
.card{border:1px solid rgba(128,128,128,.35);border-radius:12px;padding:.65rem .8rem;margin-bottom:.6rem;background:rgba(255,255,255,.02)}
.card h4{margin:0 0 .25rem 0;font-size:1rem}
.badge{display:inline-block;padding:.04rem .5rem;border-radius:999px;font-size:.76rem;margin:0 .25rem .2rem 0;border:1px solid}
.b-red{color:#b3261e;border-color:#b3261e;background:rgba(179,38,30,.07)}
.b-amber{color:#9a6700;border-color:#9a6700;background:rgba(154,103,0,.08)}
.b-green{color:#1a7f37;border-color:#1a7f37;background:rgba(26,127,55,.08)}
.b-blue{color:#1d4ed8;border-color:#1d4ed8;background:rgba(29,78,216,.07)}
.b-purple{color:#7c3aed;border-color:#7c3aed;background:rgba(124,58,237,.07)}
.b-grey{color:#64748b;border-color:#94a3b8}
.small{font-size:.84rem;opacity:.85}
.bubble{border-radius:12px;padding:.45rem .65rem;margin:.3rem 0;font-size:.88rem;border-left:5px solid #94a3b8;background:rgba(148,163,184,.12)}
.bubble .who{font-weight:700;font-size:.8rem;letter-spacing:.02em}
.bubble.REQUEST{border-left-color:#d97706}.bubble.ANSWER{border-left-color:#16a34a}.bubble.GAP_FLAG{border-left-color:#dc2626;background:rgba(220,38,38,.08)}
.bubble.DECISION{border-left-color:#2563eb}.bubble.INFO{border-left-color:#0f766e;opacity:.8}.bubble.LEGAL{border-left-color:#7c3aed;background:rgba(124,58,237,.09)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin:.3rem 0 .6rem 0}
.chip{min-width:34px;text-align:center;padding:.18rem .4rem;border-radius:8px;font-size:.78rem;border:1px solid #94a3b8;color:#64748b}
.chip.done{background:#16a34a;color:#fff;border-color:#16a34a}.chip.now{background:#2563eb;color:#fff;border-color:#2563eb}
.chip.act2{border-style:dashed}
</style>
"""


def lang() -> str:
    return st.session_state.get("lang", "en")


def L(en: str, fr: str) -> str:
    return fr if lang() == "fr" else en


def esc(x: Any) -> str:
    return html.escape(str(x))


def badge(text: str, kind: str = "grey") -> str:
    return f"<span class='badge b-{kind}'>{esc(text)}</span>"


def author_label(author: str) -> tuple[str, str]:
    """(text, badge colour) saying who wrote a sentence: never present rule-engine output as thinking."""
    a = (author or "").split(" ")[0]
    return {"rules": (L("rule engine (no AI)", "moteur de règles (sans IA)"), "amber"),
            "ai": (L("AI model", "modèle IA"), "green"),
            "fallback": (L("AI failed: rules used", "IA en échec : règles utilisées"), "red"),
            "scripted": (L("scripted", "scénarisé"), "grey"),
            "human": (L("human", "humain"), "blue"),
            "system": ("", "grey")}.get(a, (author, "grey"))


def decision_card(d: dict[str, Any], show_detail: bool = False) -> str:
    conf = {"high": "green", "medium": "amber", "low": "red"}.get(d.get("confidence"), "grey")
    basis = ""
    for c in d.get("legal_basis", []):
        ok = c.get("verified")
        label = f"{c.get('doc_id')} {c.get('article', '')}".strip()
        basis += badge(label + (" ✓ verified" if ok else " ✗ not verified" if ok is False else ""), "green" if ok else "red")
    if d.get("no_legal_basis"):
        basis += badge(L("no legal basis found", "aucune base légale trouvée"), "red")
    flags = "".join(f"<div class='small'>⚠ {esc(f)}</div>" for f in d.get("gap_flags", []))
    extra = ""
    if show_detail:
        for key, label in (("known", L("Known", "Connu")), ("unknown", L("Unknown", "Inconnu")), ("options", L("Options", "Options"))):
            vals = d.get(key) or []
            if vals:
                extra += f"<div class='small'><b>{label}:</b> " + "; ".join(esc(v) for v in vals) + "</div>"
        quotes = "".join(f"<div class='small'>“{esc(c.get('quote', ''))}”</div>" for c in d.get("legal_basis", []) if c.get("quote"))
        extra += quotes
        if d.get("reasoning_summary"):
            extra += f"<div class='small'><b>{L('Reasoning', 'Raisonnement')}:</b> {esc(d['reasoning_summary'])}</div>"
    return (f"<div class='card'><h4>{esc(d['seat'])} · {esc(d['sim_time'])} · {L('event', 'événement')} {d['event_id']}</h4>"
            f"<div>{esc(d['decision'])}</div><div style='margin-top:.3rem'>{badge(d.get('confidence', ''), conf)}{basis}"
            f"{badge(*author_label(d.get('author', '')))}</div>{flags}{extra}</div>")


def bubble(m: dict[str, Any]) -> str:
    kind = "LEGAL" if m.get("sender") == "LEGAL" else m.get("type", "INFO")
    icon = {"REQUEST": "➜", "ANSWER": "↩", "DECISION": "✔", "GAP_FLAG": "⚠", "INFO": "ℹ", "OBJECTION": "✋", "LEGAL": "⚖"}.get(kind, "")
    if m.get("type") == "OBJECTION":
        kind = "GAP_FLAG"          # same red styling as a flag
    to = f" → {esc(m['recipient'])}" if m.get("recipient") not in (None, "", "ALL") else ""
    status = f", {esc(m['status'])}" if m.get("status") else ""
    who_text, who_col = author_label(m.get("author", ""))
    tag = badge(who_text, who_col) if who_text else ""
    return (f"<div class='bubble {kind}'><div class='who'>{icon} {esc(m['sender'])}{to} "
            f"<span class='small'>({esc(m['type'])}{status})</span> {tag}</div>{esc(m['text'])}</div>")


def event_chips(events: list[Any], played: int, current: int | None = None) -> str:
    chips = []
    for i, ev in enumerate(events):
        cls = "now" if current is not None and i == current else ("done" if i < played else "")
        chips.append(f"<span class='chip {cls} {'act2' if ev.act == 2 else ''}' title='{esc(ev.sim_time)} · act {ev.act}'>{ev.id}</span>")
    return "<div class='chips'>" + "".join(chips) + "</div>"
