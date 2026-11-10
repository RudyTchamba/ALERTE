"""Screen 2: decisions, each with the article it relies on (or "no legal basis found")."""

from __future__ import annotations

import streamlit as st

from alerte.knowledge.store import get_store
from alerte.ui.data_access import ai_calls, run_dataset, runs_list
from alerte.ui.theme import L, author_label, badge, decision_card, esc


def page() -> None:
    st.title("⚖️ " + L("Decisions and cited articles", "Décisions et articles cités"))
    st.caption(L("Every decision is a structured record: what the seat knew, what it did not know, the options, the choice, "
                 "the legal basis and a confidence level. Quotes are checked against the library; an unsupported quote is rejected.",
                 "Chaque décision est un enregistrement structuré : connu, inconnu, options, choix, base légale, confiance. "
                 "Les citations sont vérifiées dans la bibliothèque."))
    runs = runs_list()
    if not runs:
        st.info(L("No finished drill yet. Run one on the “Live exercise” page and press “Finish and analyse”.",
                  "Aucun exercice terminé. Lancez-en un dans « Exercice en direct »."))
        return
    run = st.selectbox(L("Drill", "Exercice"), runs, format_func=lambda p: p.name)
    data = run_dataset(run)
    decs = data.get("decisions", [])
    seats = sorted({d["seat"] for d in decs})
    c1, c2, c3, c4 = st.columns([1.4, 1.2, 1, 1])
    f_seat = c1.multiselect(L("Seat", "Siège"), seats)
    f_event = c2.multiselect(L("Event", "Événement"), sorted({d["event_id"] for d in decs}))
    only_nb = c3.checkbox(L("No legal basis only", "Sans base légale"))
    only_bad = c4.checkbox(L("Unverified quotes only", "Citations non vérifiées"))
    shown = [d for d in decs if (not f_seat or d["seat"] in f_seat) and (not f_event or d["event_id"] in f_event)
             and (not only_nb or d.get("no_legal_basis")) and (not only_bad or any(c.get("verified") is False for c in d.get("legal_basis", [])))]
    ok = sum(1 for d in decs for c in d.get("legal_basis", []) if c.get("verified"))
    tot = sum(len(d.get("legal_basis", [])) for d in decs)
    m1, m2, m3 = st.columns(3)
    m1.metric(L("Decisions", "Décisions"), len(decs))
    m2.metric(L("Citations verified", "Citations vérifiées"), f"{ok}/{tot}")
    m3.metric(L("“No legal basis found”", "« Aucune base légale »"), sum(1 for d in decs if d.get("no_legal_basis")))
    st.caption(f"{len(shown)} / {len(decs)}")
    store = get_store()
    calls = ai_calls(run)
    by_author = {}
    for d in decs:
        by_author[d.get("author", "")] = by_author.get(d.get("author", ""), 0) + 1
    st.caption(L("Who wrote the decisions: ", "Qui a écrit les décisions : ") + ", ".join(f"{author_label(k)[0] or k} {v}" for k, v in by_author.items())
               + f" · {len(calls)} " + L("AI model calls in this run", "appels au modèle IA dans cet exercice"))
    for d in shown:
        st.markdown(decision_card(d, show_detail=True), unsafe_allow_html=True)
        with st.expander(L("How was this decided?", "Comment cette décision a-t-elle été prise ?")):
            who = (d.get("author") or "").split(" ")[0]
            if who == "ai":
                st.markdown(L("**An AI model wrote this.** It was given the institution's role card and perspective, its powers from the who-does-what map, "
                              "its inbox, the event and the passages below. Its exact prompt and raw answer:",
                              "**Un modèle IA a écrit ceci.** Il a reçu la fiche de rôle et la perspective de l'institution, ses pouvoirs, sa boîte, l'événement et les passages. "
                              "Son prompt exact et sa réponse brute :"))
                mine = [c for c in calls if c.get("actor") == d["seat"] and c.get("event_id") == d["event_id"] and c.get("kind") in ("decide", "reply")]
                for c in mine:
                    st.caption(f"{c.get('kind')} · {c.get('model')} · {c.get('seconds')} s")
                    with st.expander(L("Prompt sent to the model", "Prompt envoyé au modèle")):
                        st.code(c.get("system", "") + "\n\n" + c.get("prompt", ""), language="text")
                    with st.expander(L("Raw answer of the model", "Réponse brute du modèle")):
                        st.code(c.get("answer", ""), language="json")
                if not mine:
                    st.caption(L("The model call for this decision was not found in the logbook.", "Appel au modèle introuvable dans le journal."))
            elif who == "fallback":
                st.markdown(L("**The AI model failed for this decision**, so the rule engine answered instead (see the logbook entry of type ERROR). "
                              "The words below are template text, not model reasoning.", "**Le modèle IA a échoué**, le moteur de règles a répondu à sa place."))
            elif who == "rules":
                st.markdown(L("**No AI was involved.** This sentence is a template filled from the who-does-what map: the institution found (or did not find) "
                              "a line giving it the power or duty, and the template turned that into text. The line it used:",
                              "**Aucune IA.** Cette phrase est un modèle rempli à partir du tableau « qui fait quoi » : la ligne utilisée est indiquée ci-dessous."))
            elif who == "scripted":
                st.markdown(L("**Scripted.** HydroSense is the fictional AI system under test: its output is part of the scenario, it never calls a model.",
                              "**Scénarisé.** HydroSense est le système IA fictif testé : sa sortie fait partie du scénario."))
            else:
                st.markdown(L("Written by a human participant.", "Écrit par un participant humain."))
            st.markdown(f"**{L('Reasoning recorded', 'Raisonnement enregistré')}:** {d.get('reasoning_summary') or '-'}")
        for c in d.get("legal_basis", []):
            chunk = next((x for x in store.doc_chunks(c["doc_id"]) if x.chunk_id == c.get("chunk_id")), None)
            if chunk is not None:
                with st.expander(f"{L('Source passage', 'Passage source')}: {c['doc_id']} {c.get('article', '')} · {chunk.reliability}"):
                    st.write(chunk.text)
                    st.caption(f"{chunk.title} · {chunk.url or L('no link', 'pas de lien')}")
