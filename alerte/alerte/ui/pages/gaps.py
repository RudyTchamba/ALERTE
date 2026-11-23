"""Screen 3: the gap report, with global precedents, and the 13-dimension readiness table."""

from __future__ import annotations

import json

import streamlit as st

from alerte.analysis.gaps import GAP_TYPES, GAP_TYPES_FR
from alerte.sim.ledger import Ledger
from alerte.ui.data_access import run_dataset, runs_list
from alerte.ui.theme import L, badge, lang


def readiness_table(rows: list[dict]) -> None:
    st.dataframe([{"#": r["dimension_id"], L("Dimension", "Dimension"): r["name"],
                   L("Score (0-5)", "Score (0-5)"): None if r["score"] < 0 else r["score"],
                   L("Evidence", "Preuves"): "; ".join(r["evidence"][:3])} for r in rows],
                 column_config={L("Score (0-5)", "Score (0-5)"): st.column_config.ProgressColumn(L("Score (0-5)", "Score (0-5)"), min_value=0, max_value=5, format="%.1f")},
                 hide_index=True, use_container_width=True)


def page() -> None:
    st.title("🧭 " + L("Gap report", "Rapport des lacunes"))
    runs = runs_list()
    if not runs:
        st.info(L("No finished drill yet.", "Aucun exercice terminé."))
        return
    run = st.selectbox(L("Drill", "Exercice"), runs, format_func=lambda p: p.name)
    data = run_dataset(run)
    gaps = data.get("gaps", [])
    cc = data.get("summary", {}).get("country", "")
    names = GAP_TYPES_FR if lang() == "fr" else GAP_TYPES
    st.warning(L("Each gap is suspected until an expert confirms it. It is a finding about the domain, not a recommendation to a government. "
                 "“Not found” means not found in the documents checked (often summaries).",
                 "Chaque lacune est présumée jusqu'à confirmation par un expert. C'est un constat sur le domaine, pas une recommandation à un gouvernement."))
    tab_gaps, tab_ready, tab_assume = st.tabs([L("Gaps", "Lacunes"), L("13-dimension readiness table", "Tableau de préparation (13 dimensions)"),
                                               L("Assumptions", "Hypothèses")])
    with tab_gaps:
        c1, c2, c3 = st.columns(3)
        types = c1.multiselect("Type", sorted({g["type"] for g in gaps}, key=lambda x: int(x[1:])), format_func=lambda x: f"{x} {names.get(x, x)}")
        insts = c2.multiselect(L("Institution", "Institution"), sorted({i for g in gaps for i in g["institutions"]}))
        min_sev = c3.slider(L("Minimum severity", "Gravité minimale"), 1, 3, 1)
        shown = [g for g in gaps if (not types or g["type"] in types) and (not insts or set(insts) & set(g["institutions"])) and g["severity"] >= min_sev]
        st.caption(f"{len(shown)} / {len(gaps)}")
        for g in shown:
            sev = {1: "green", 2: "amber", 3: "red"}[g["severity"]]
            with st.expander(f"{g['gap_id']} · {g['title']}"):
                st.markdown(badge(f"{L('severity', 'gravité')} {g['severity']}", sev)
                            + badge(g["status"], "green" if g["status"] == "confirmed" else "amber")
                            + "".join(badge(i, "blue") for i in g["institutions"]), unsafe_allow_html=True)
                st.markdown(f"**{L('What is missing', 'Ce qui manque')}:** {g['description']}")
                st.markdown(f"**{L('When', 'Quand')}:** {L('events', 'événements')} {', '.join(map(str, g['event_ids']))} ({g['first_sim_time']})")
                st.markdown(f"**{L('Texts checked', 'Textes vérifiés')}:** {', '.join(g['texts_checked']) or L('none', 'aucun')}")
                st.markdown(f"**{L('Evidence', 'Preuves')}:**\n" + "\n".join(f"- {e}" for e in g["evidence"]))
                st.markdown(f"**{L('How others handle it', 'Comment font les autres')}:**")
                fit = L("Note (some written for Cameroon)", "Note (certaines rédigées pour le Cameroun)")
                for p in g["precedents"]:
                    link = f"[{p['instrument']}{(', ' + p['article']) if p['article'] else ''}]({p['url']})" if p["url"] else p["instrument"]
                    st.markdown(f"- **{p['jurisdiction']}**: {link}. {p['what_it_does']} *{fit}:* {p['fit_note']}")
                st.markdown("---")
                k1, k2, k3 = st.columns([1, 2, 1])
                opts = ["confirmed", "disputed", "rejected", "suspected"]
                new_status = k1.selectbox(L("Expert review", "Revue d'expert"), opts, index=opts.index(g["status"]), key=f"s{g['gap_id']}")
                note = k2.text_input(L("Reason / note", "Motif / note"), g.get("review_note", ""), key=f"n{g['gap_id']}")
                if k3.button(L("Save review", "Enregistrer"), key=f"b{g['gap_id']}"):
                    g["status"], g["review_note"] = new_status, note
                    (run / "gaps.json").write_text(json.dumps(gaps, ensure_ascii=False, indent=1), encoding="utf-8")
                    Ledger(run / "ledger.jsonl").append("REVIEW", "EXPERT", {"gap_id": g["gap_id"], "status": new_status, "note": note})
                    st.success(L("Saved and written to the logbook.", "Enregistré dans le journal."))
    with tab_ready:
        st.caption(L("ITU AI Readiness Report 2.0, 13 dimensions. 5 = no gap found in this drill, 0 = many serious gaps. "
                     "“Not assessed” = the story did not probe it. This is not an official rating of any country.",
                     "Rapport 2.0 de l'UIT, 13 dimensions. 5 = aucune lacune trouvée, 0 = nombreuses lacunes graves. Ce n'est pas une notation officielle."))
        readiness_table(data.get("scorecard", []))
    with tab_assume:
        a = data.get("assumptions", {})
        st.markdown("**" + L("Mandate lines that are not fully documented", "Lignes de mandat non entièrement documentées") + "**")
        st.dataframe(a.get("mandate_lines", []), hide_index=True, use_container_width=True)
        st.markdown("**" + L("Documents that are summaries only", "Documents qui ne sont que des résumés") + f":** {', '.join(a.get('summary_documents', [])) or '-'}")
