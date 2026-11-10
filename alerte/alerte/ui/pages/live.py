"""Screen 1: the live exercise. Agents, messages and decisions, event by event."""

from __future__ import annotations

import time

import streamlit as st
import streamlit.components.v1 as components

from alerte import config
from alerte.sim.engine import Drill
from alerte.sim.scenario import list_scenarios, load_roles, load_scenario
from alerte.ui.arena import arena_html, render_arena
from alerte.ui.data_access import role_dicts
from alerte.ui.theme import L, author_label, badge, bubble, decision_card, esc, event_chips, lang


def _draw(drill: Drill, event_id: int, arena_ph, feed_ph, cards_ph=None) -> None:
    ev = next(e for e in drill.scenario.events if e.id == event_id)
    msgs = [m.model_dump(mode="json") for m in drill.messages if m.event_id == event_id]
    decs = [d.model_dump(mode="json") for d in drill.decisions if d.event_id == event_id]
    svg = render_arena(role_dicts(drill.scenario), msgs, decs, [c for c in ev.to if c in drill.seats],
                       {"sender": ev.sender, "sim_time": ev.sim_time})
    with arena_ph.container():
        components.html(arena_html(svg), height=680, scrolling=False)
        st.caption(f"**{ev.sim_time}** · {L('act', 'acte')} {ev.act} · {ev.text_in(drill.lang)}")
    with feed_ph.container():
        st.markdown("##### " + L("Conversation", "Conversation"))
        shown = [m for m in msgs if m["type"] != "INFO"]
        for m in shown or msgs:
            st.markdown(bubble(m), unsafe_allow_html=True)
    if cards_ph is not None:
        with cards_ph.container():
            for d in decs:
                st.markdown(decision_card(d, show_detail=True), unsafe_allow_html=True)


BRAIN_HELP = {
    "offline": ("Rule engine (no AI, instant)", "Moteur de règles (sans IA, instantané)"),
    "llm": ("AI model (agents reason and discuss)", "Modèle IA (les agents raisonnent et discutent)"),
}


def _llm_status() -> tuple[bool, str]:
    """Is an AI model reachable? Cached for 20 seconds so the page stays fast."""
    import time as _t
    cache = st.session_state.get("_llm_status")
    if cache and _t.time() - cache[0] < 20:
        return cache[1]
    from alerte.sim.llm_client import LLMClient
    c = LLMClient()
    ok, msg = c.health(timeout=3)
    res = (ok, f"{c.model} at {c.base_url}: {msg}")
    st.session_state["_llm_status"] = (_t.time(), res)
    return res


def _mode_box(drill: Drill | None = None, brain: str | None = None) -> None:
    """Say plainly what is producing the agents' words."""
    name = drill.brain_name if drill else brain
    if name == "offline":
        st.warning(L("**RULE ENGINE MODE: no AI model is running.** The institutions' words are assembled from the who-does-what table "
                     "with fixed sentence templates, so they look alike and no agent reasons or discusses. This mode is for fast, "
                     "reproducible tests. To see agents think, discuss and disagree, choose “AI model” (needs a model, see docs/AGENTS.md).",
                     "**MODE MOTEUR DE RÈGLES : aucun modèle IA n'est utilisé.** Les paroles des institutions sont assemblées à partir du tableau "
                     "« qui fait quoi » avec des phrases types : elles se ressemblent et aucun agent ne raisonne ni ne discute. "
                     "Ce mode sert aux tests rapides et reproductibles. Pour voir les agents penser, discuter et s'opposer, choisissez « Modèle IA »."))
    elif drill is not None:
        fallbacks = sum(1 for d in drill.decisions if d.author == "fallback")
        box = st.error if fallbacks else st.success
        box(L(f"**AI MODEL MODE** · {drill.model_info.get('model', '?')} · {getattr(drill.brain, 'calls', 0)} model calls so far · "
              f"{fallbacks} decision(s) fell back to the rule engine because the model failed (they are labelled).",
              f"**MODE MODÈLE IA** · {drill.model_info.get('model', '?')} · {getattr(drill.brain, 'calls', 0)} appels au modèle · "
              f"{fallbacks} décision(s) reprise(s) par le moteur de règles car le modèle a échoué (elles sont étiquetées)."))


def _setup() -> None:
    st.title("🚨 " + L("Live exercise", "Exercice en direct"))
    st.write(L("AI agents play the institutions of a country during a flood in which an AI warning system fails. "
               "Each agent sees only its own inbox and its own legal powers; every decision cites an article or says "
               "“no legal basis found”.",
               "Des agents IA jouent les institutions d'un pays lors d'une inondation où un système d'alerte IA échoue. "
               "Chaque agent ne voit que sa boîte et ses propres pouvoirs ; chaque décision cite un article ou dit "
               "« aucune base légale trouvée »."))
    scen = list_scenarios()
    ids = [s["id"] for s in scen]
    c1, c2, c3 = st.columns([2.2, 1, 1])
    sid = c1.selectbox(L("Crisis story", "Scénario"), ids, index=ids.index("ae-core") if "ae-core" in ids else 0,
                       format_func=lambda i: next(f"{s['title']} · {s['events']} events" for s in scen if s["id"] == i))
    llm_ok, llm_msg = _llm_status()
    brain = c2.selectbox(L("Who thinks", "Qui réfléchit"), ["offline", "llm"], index=1 if (llm_ok or config.settings.brain == "llm") else 0,
                         format_func=lambda b: L(*BRAIN_HELP[b]),
                         help=L("Rule engine = fixed rules and sentence templates, no AI. AI model = the open model set in .env (Ollama, vLLM, sandbox).",
                                "Moteur de règles = règles et phrases types, sans IA. Modèle IA = le modèle ouvert défini dans .env."))
    dlang = c3.radio(L("Drill language", "Langue"), ["en", "fr"], horizontal=True, index=0 if lang() == "en" else 1)
    sc = load_scenario(sid)
    roles = load_roles(sc)
    if brain == "llm":
        (st.success if llm_ok else st.error)(("✔ " if llm_ok else "✘ ") + L("AI model: ", "Modèle IA : ") + llm_msg)
        if not llm_ok:
            st.info(L("No AI model answers at this address. Start one (for example `ollama serve` and `ollama pull qwen2.5:7b-instruct`) "
                      "or edit ALERTE_LLM_BASE_URL in .env. See docs/AGENTS.md. Until then, choose the rule engine.",
                      "Aucun modèle IA ne répond à cette adresse. Lancez-en un (par exemple `ollama serve` puis `ollama pull qwen2.5:7b-instruct`) "
                      "ou modifiez ALERTE_LLM_BASE_URL dans .env. Voir docs/AGENTS.md."))
    else:
        _mode_box(None, "offline")
    playable = [c for c, r in roles.items() if c not in ("COORD", "LEGAL", "HYDRO")]
    humans = st.multiselect(L("Seats played by a human (the others are AI)", "Sièges tenus par un humain (les autres sont IA)"), playable)
    st.markdown(event_chips(sc.events, 0), unsafe_allow_html=True)
    st.caption(sc.summary)
    if st.button("▶ " + L("Start the drill", "Démarrer l'exercice"), type="primary", disabled=(brain == "llm" and not llm_ok)):
        with st.spinner(L("Preparing the knowledge base and the agents…", "Préparation de la base et des agents…")):
            st.session_state["drill"] = Drill(sid, brain=brain, lang=dlang, human_seats=humans)
            st.session_state["result"] = None
            st.session_state["view_event"] = None
        st.rerun()


def _human_forms(drill: Drill) -> dict:
    inputs: dict = {}
    pend = drill.pending_humans()
    if not pend or drill.done:
        return inputs
    ev = drill.next_event
    st.info(L(f"Event {ev.id} at {ev.sim_time} needs a decision from: ", f"L'événement {ev.id} à {ev.sim_time} attend une décision de : ") + ", ".join(pend))
    st.markdown(f"> {ev.text_in(drill.lang)}")
    docs = sorted(drill.store.documents)
    for code in pend:
        seat = drill.seats[code]
        with st.expander(L("Decision form: ", "Formulaire : ") + seat.role.name, expanded=True):
            for h in drill.seat_search(seat, ev.text_in(drill.lang) + " " + " ".join(ev.required_actions), 4):
                st.markdown(f"- **{h.chunk.doc_id} {h.chunk.article}**: {h.chunk.text[:220]}…")
            k = f"{code}{ev.id}"
            inputs[code] = {
                "known": st.text_input(L("What I know", "Ce que je sais"), key=f"k{k}"),
                "unknown": st.text_input(L("What I don't know", "Ce que j'ignore"), key=f"u{k}"),
                "decision": st.text_area(L("My decision", "Ma décision"), key=f"d{k}"),
                "action": st.selectbox(L("It concerns", "Elle concerne"), [""] + ev.required_actions, key=f"a{k}"),
                "doc_id": st.selectbox(L("Legal basis: document", "Base légale : document"), [""] + docs, key=f"doc{k}"),
                "article": st.text_input(L("Article (if any)", "Article"), key=f"art{k}"),
                "quote": st.text_input(L("Exact words quoted (optional)", "Mots exacts cités"), key=f"q{k}"),
                "no_legal_basis": st.checkbox(L("No legal basis found", "Aucune base légale trouvée"), key=f"n{k}"),
                "confidence": st.select_slider(L("Confidence", "Confiance"), ["low", "medium", "high"], "medium", key=f"c{k}"),
                "gap_flag": st.text_input(L("Gap I noticed (optional)", "Lacune constatée"), key=f"g{k}"),
            }
    return {k: v for k, v in inputs.items() if v.get("decision")}


def page() -> None:
    drill: Drill | None = st.session_state.get("drill")
    if drill is None:
        _setup()
        return
    sc = drill.scenario
    total = len(sc.events)
    st.title("🚨 " + sc.title)
    st.caption(f"Run `{drill.run_id}` · brain: " + (drill.model_info.get("model") or drill.model_info.get("brain", ""))
               + f" · {L('legal consultations', 'consultations juridiques')}: {len(drill.legal_answers)}")
    _mode_box(drill)
    st.progress(drill.index / total, text=f"{drill.index} / {total} " + L("events played", "événements joués"))
    cur = (st.session_state.get("view_event") or (drill.scenario.events[drill.index - 1].id if drill.index else None))
    st.markdown(event_chips(sc.events, drill.index, drill.index if not drill.done else None), unsafe_allow_html=True)

    human_inputs = _human_forms(drill)
    pend = drill.pending_humans()
    b1, b2, b3, b4, b5 = st.columns([1, 1.3, 1, 1.2, 1])
    delay = b2.slider(L("Autoplay pause (s)", "Pause (s)"), 0.0, 6.0, 1.5, 0.5, label_visibility="collapsed",
                      help=L("Pause between events during autoplay", "Pause entre événements"))
    nxt = b1.button("▶ " + L("Next event", "Suivant"), disabled=drill.done, type="primary", use_container_width=True)
    auto = b3.button("⏵⏵ " + L("Autoplay", "Auto"), disabled=drill.done or bool(pend), use_container_width=True)
    fin = b4.button("■ " + L("Finish and analyse", "Terminer et analyser"), disabled=not drill.done or st.session_state.get("result") is not None,
                    use_container_width=True)
    new = b5.button("↺ " + L("New drill", "Nouveau"), use_container_width=True)

    left, right = st.columns([2.1, 1])
    arena_ph, feed_ph, cards_ph = left.empty(), right.empty(), st.empty()

    if new:
        st.session_state["drill"] = None
        st.session_state["result"] = None
        st.rerun()
    if nxt:
        with st.spinner(L("Institutions are thinking…", "Les institutions réfléchissent…")):
            res = drill.step(human_inputs or None)
        st.session_state["view_event"] = res.event_id
        st.rerun()
    if auto:
        while not drill.done and not drill.pending_humans():
            res = drill.step()
            st.session_state["view_event"] = res.event_id
            _draw(drill, res.event_id, arena_ph, feed_ph)
            time.sleep(delay)
        st.rerun()
    if fin:
        with st.spinner(L("Finding gaps and global examples…", "Recherche des lacunes et exemples mondiaux…")):
            st.session_state["result"] = drill.finish()
        st.rerun()

    if cur is not None:
        played_ids = [e.id for e in sc.events[:drill.index]]
        if len(played_ids) > 1:
            cur = left.select_slider(L("Look back at event", "Revoir l'événement"), played_ids, value=cur if cur in played_ids else played_ids[-1],
                                     key="view_event_slider")
        _draw(drill, cur, arena_ph, feed_ph, cards_ph)
    else:
        with arena_ph.container():
            svg = render_arena(role_dicts(sc), [], [], [], {"sender": "", "sim_time": ""})
            components.html(arena_html(svg), height=680)
            st.info(L("Press “Next event” to release the first event to its recipients.", "Appuyez sur « Suivant » pour livrer le premier événement."))

    with st.expander(L("Facilitator: add a surprise event", "Animateur : événement surprise")):
        txt = st.text_area(L("Event text", "Texte de l'événement"))
        to = st.multiselect(L("Send to", "Envoyer à"), list(drill.seats))
        acts = st.multiselect(L("Actions it requires", "Actions requises"), sorted(drill.mm.actions))
        if st.button(L("Add as next event", "Ajouter comme prochain événement")) and txt and to:
            drill.inject_surprise(txt, to, acts)
            st.success(L("Added. It will be played next.", "Ajouté. Il sera joué ensuite."))

    res = st.session_state.get("result")
    if res is not None:
        s = res.summary
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(L("Gaps found", "Lacunes"), s["gaps"], f"{s['confirmed_gaps']} " + L("confirmed by text", "confirmées par le texte"), delta_color="off")
        m2.metric(L("Planned gaps found", "Lacunes prévues trouvées"), f"{s['expected_gap_coverage']['found']}/{s['expected_gap_coverage']['expected']}")
        m3.metric(L("Quotes verified", "Citations vérifiées"), f"{s['citations']['verified']}/{s['citations']['citations']}")
        m4.metric(L("Logbook", "Journal"), L("intact", "intact") if s["ledger"]["ok"] else "BROKEN")
        by = s.get("decisions_by_author", {})
        st.caption(L("Who wrote the decisions: ", "Qui a écrit les décisions : ") + ", ".join(
            f"{author_label(k)[0] or k} {v}" for k, v in by.items())
            + (L(f" · {s['discussion_messages']} discussion messages between agents", f" · {s['discussion_messages']} messages de discussion entre agents")
               if s.get("discussion_messages") else ""))
        d1, d2, d3 = st.columns(3)
        d1.download_button(L("Report (HTML)", "Rapport (HTML)"), (res.run_dir / "report.html").read_text(encoding="utf-8"),
                           file_name=f"{res.run_id}.html", mime="text/html")
        d2.download_button(L("Report (Markdown)", "Rapport (Markdown)"), (res.run_dir / "report.md").read_text(encoding="utf-8"), file_name=f"{res.run_id}.md")
        d3.download_button(L("Logbook (JSONL)", "Journal (JSONL)"), (res.run_dir / "ledger.jsonl").read_text(encoding="utf-8"),
                           file_name=f"{res.run_id}-ledger.jsonl")
        st.success(L("Open “Gap report” to explore the gaps, or “Replay and audit” to replay this drill.",
                     "Ouvrez « Rapport des lacunes » pour explorer, ou « Rejeu et audit » pour rejouer."))
