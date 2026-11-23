"""About: the architecture diagram, the Y.3172 mapping and how ALERTE answers the hackathon."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from alerte import __version__, config
from alerte.ui.architecture import architecture_svg
from alerte.ui.theme import L

Y3172 = [
    ("SRC", "National texts, global precedents, ITU texts, scenario injects, fictional HydroSense model card", "data/docs, data/scenarios"),
    ("C", "Manifest-driven collection; event dispatcher on a simulated clock", "knowledge/fetch.py, ingest.py, sim/engine.py"),
    ("PP", "Article-level chunking, metadata and evidence tags, optional multilingual embeddings", "knowledge/parse.py, chunk.py, embed.py"),
    ("M", "Six agents through one AI door; HydroSense scripted under test", "sim/brain.py, sim/llm_client.py, sim/adviser.py"),
    ("P", "Mandate map, citation check, gap rules, precedents, readiness scorecard", "knowledge/mandates.py, sim/citations.py, analysis/"),
    ("D", "Coordination board and private inboxes", "sim/engine.py"),
    ("SINK", "Streamlit interface, reports, ChromaDB export, SFT data, Slack", "ui/, analysis/report.py, knowledge/chroma_export.py"),
    ("MLFO", "Drill engine: rounds, model gateway with fallback, ledger", "sim/engine.py"),
    ("Sandbox", "The whole simulator; hash-chained ledger; replay without AI", "sim/ledger.py, analysis/replay.py"),
]


def page() -> None:
    st.title("🏛️ " + L("Architecture and hackathon mapping", "Architecture et correspondance avec le hackathon"))
    st.caption(f"ALERTE {__version__} · ITU AI for Good Lab Hackathon, UAE 2026")
    components.html(architecture_svg(), height=1080, scrolling=True)
    st.download_button("⬇ architecture.svg", architecture_svg(), file_name="alerte-architecture.svg", mime="image/svg+xml")
    st.markdown("#### " + L("ITU-T Y.3172 mapping", "Correspondance UIT-T Y.3172"))
    st.dataframe([{"Node": n, L("In ALERTE", "Dans ALERTE"): d, L("Code", "Code"): f} for n, d, f in Y3172], hide_index=True, use_container_width=True)
    st.markdown("#### " + L("Runtime", "Exécution"))
    s = config.settings
    st.json({"brain": s.brain, "model": s.llm_model if s.brain == "llm" else None, "embeddings": s.embed_provider,
             "ITU reference repo": str(s.itu_root) if s.itu_root else "not found", "runs folder": str(s.runs_dir)})
