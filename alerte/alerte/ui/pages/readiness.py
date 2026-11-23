"""ITU AI Readiness scorecard and twin-country comparison (UAE vs Cameroon, or before/after a change of law)."""

from __future__ import annotations

import streamlit as st

from alerte.analysis.compare import compare_runs
from alerte.ui.data_access import runs_list
from alerte.ui.theme import L


def page() -> None:
    st.title("📊 " + L("Readiness and country comparison", "Préparation et comparaison de pays"))
    st.caption(L("ITU AI Readiness Report 2.0, 13 dimensions. 5 = no gap found in this drill, 0 = many serious gaps. "
                 "Not an official rating of any country.", "13 dimensions du rapport 2.0. Pas une notation officielle."))
    runs = runs_list()
    if len(runs) < 1:
        st.info(L("No finished drill yet.", "Aucun exercice terminé."))
        return
    a = st.selectbox(L("Drill A", "Exercice A"), runs, format_func=lambda p: p.name)
    b = st.selectbox(L("Drill B (optional)", "Exercice B (facultatif)"), [None] + [r for r in runs if r != a],
                     format_func=lambda p: "-" if p is None else p.name)
    if b is None:
        from alerte.analysis.report import load_run
        rows = load_run(a).get("scorecard", [])
        st.dataframe([{"#": r["dimension_id"], "Dimension": r["name"], "Score": None if r["score"] < 0 else r["score"],
                       L("Evidence", "Preuves"): "; ".join(r["evidence"][:3])} for r in rows],
                     column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=5, format="%.1f")},
                     hide_index=True, use_container_width=True)
        return
    c = compare_runs(a, b)
    A, B = c["a"]["country"], c["b"]["country"]
    if A == B:
        A, B = f"{A} (A)", f"{B} (B)"
    st.dataframe([{"#": r["dimension_id"], "Dimension": r["name"], A: None if r["a"] < 0 else r["a"], B: None if r["b"] < 0 else r["b"]}
                  for r in c["scorecard"]],
                 column_config={A: st.column_config.ProgressColumn(A, min_value=0, max_value=5, format="%.1f"),
                                B: st.column_config.ProgressColumn(B, min_value=0, max_value=5, format="%.1f")},
                 hide_index=True, use_container_width=True)
    st.markdown("#### " + L("Gaps by type", "Lacunes par type"))
    st.dataframe([{"Type": f"{r['type']} {r['name']}", A: r["a"], B: r["b"]} for r in c["gaps_by_type"]], hide_index=True, use_container_width=True)
    k1, k2 = st.columns(2)
    k1.markdown(f"**{L('Only in', 'Seulement dans')} {A}**\n" + "\n".join(f"- {x}" for x in c["only_in_a"]))
    k2.markdown(f"**{L('Only in', 'Seulement dans')} {B}**\n" + "\n".join(f"- {x}" for x in c["only_in_b"]))
