"""Screen 4: replay a finished drill from its logbook alone (no AI call) and verify it was not altered."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from alerte.analysis.replay import snapshot, timeline
from alerte.sim.ledger import read_ledger, verify_ledger
from alerte.ui.arena import arena_html, render_arena
from alerte.ui.data_access import run_dataset, runs_list
from alerte.ui.theme import L, bubble, decision_card, esc, event_chips


def page() -> None:
    st.title("⏪ " + L("Replay and audit", "Rejeu et audit"))
    runs = runs_list()
    if not runs:
        st.info(L("No finished drill yet.", "Aucun exercice terminé."))
        return
    run = st.selectbox(L("Drill", "Exercice"), runs, format_func=lambda p: p.name)
    c1, c2 = st.columns([1, 3])
    if c1.button("🔒 " + L("Verify the logbook", "Vérifier le journal"), type="primary"):
        res = verify_ledger(run / "ledger.jsonl")
        (c2.success if res["ok"] else c2.error)(res["message"])
    data = run_dataset(run)
    sc = data["scenario_obj"]
    entries = read_ledger(run / "ledger.jsonl")
    st.caption(L("The logbook is a SHA-256 hash chain: each entry carries the fingerprint of the previous one, so a secret edit breaks the chain "
                 "from that point. Replay rebuilds what every seat knew and did without calling the AI again.",
                 "Le journal est une chaîne de hachage SHA-256 : toute modification secrète casse la chaîne."))
    ids = [e.id for e in sc.events]
    ev_id = st.select_slider(L("Event", "Événement"), ids, value=ids[-1])
    ev = next(e for e in sc.events if e.id == ev_id)
    st.markdown(event_chips(sc.events, ids.index(ev_id) + 1, ids.index(ev_id)), unsafe_allow_html=True)
    msgs = [m for m in data.get("messages", []) if m["event_id"] == ev_id]
    decs = [d for d in data.get("decisions", []) if d["event_id"] == ev_id]
    left, right = st.columns([2.1, 1])
    with left:
        svg = render_arena(data["roles"], msgs, decs, [c for c in ev.to if c in data["roles"]], {"sender": ev.sender, "sim_time": ev.sim_time})
        components.html(arena_html(svg), height=680)
        st.caption(f"**{ev.sim_time}** · {ev.text_in(sc.language)}")
    with right:
        st.markdown("##### " + L("Conversation", "Conversation"))
        for m in msgs:
            if m["type"] != "INFO":
                st.markdown(bubble(m), unsafe_allow_html=True)
    tl = timeline(run)
    first = next((e["seq"] for e in entries if e["type"] == "INJECT" and e["payload"]["event_id"] == ev_id), 1)
    seq = st.slider(L("Logbook entry (fine-grained replay)", "Entrée du journal (rejeu fin)"), 1, tl[-1]["seq"], first)
    snap = snapshot(run, seq)
    st.caption(f"{L('Entry', 'Entrée')} {seq}: {tl[seq - 1]['type']} · {tl[seq - 1]['actor']} · {snap.sim_time}")
    a, b = st.columns([1.4, 1.2])
    with a:
        st.markdown("#### " + L("Decisions so far", "Décisions jusqu'ici"))
        for d in snap.decisions[::-1][:12]:
            st.markdown(decision_card(d), unsafe_allow_html=True)
    with b:
        st.markdown("#### " + L("What each seat knew", "Ce que chaque siège savait"))
        seat = st.selectbox(L("Seat", "Siège"), sorted(snap.inboxes) or ["-"])
        for line in snap.inboxes.get(seat, [])[::-1]:
            st.markdown(f"<div class='bubble INFO'>{esc(line)}</div>", unsafe_allow_html=True)
    st.caption(f"{L('AI model calls up to this point', 'Appels au modèle IA')}: {snap.llm_calls} · {L('errors', 'erreurs')}: {len(snap.errors)}")
    with st.expander(L("Raw logbook entry", "Entrée brute du journal")):
        st.json(entries[seq - 1])
