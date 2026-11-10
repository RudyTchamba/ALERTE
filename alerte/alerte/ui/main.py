"""ALERTE web interface.  Start with:  python -m alerte ui"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # allow `streamlit run` from anywhere

from alerte import __version__, config  # noqa: E402
from alerte.knowledge.ingest import ensure_index  # noqa: E402
from alerte.ui.pages import about, adviser, decisions, gaps, knowledge, live, readiness, replay  # noqa: E402
from alerte.ui.theme import CSS, L  # noqa: E402

st.set_page_config(page_title="ALERTE", page_icon="🚨", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource(show_spinner="Building the knowledge index (first start only)…")
def _boot() -> bool:
    ensure_index()
    return True


_boot()
st.session_state.setdefault("lang", "en")
st.sidebar.markdown("### 🚨 ALERTE")
st.session_state["lang"] = st.sidebar.radio("Language / Langue", ["en", "fr"], horizontal=True,
                                            index=0 if st.session_state["lang"] == "en" else 1,
                                            format_func=lambda x: "English" if x == "en" else "Français")

pages = [
    st.Page(live.page, title=L("1 · Live exercise", "1 · Exercice en direct"), icon="🚨", url_path="live", default=True),
    st.Page(decisions.page, title=L("2 · Decisions", "2 · Décisions"), icon="⚖️", url_path="decisions"),
    st.Page(gaps.page, title=L("3 · Gap report", "3 · Rapport des lacunes"), icon="🧭", url_path="gaps"),
    st.Page(replay.page, title=L("4 · Replay and audit", "4 · Rejeu et audit"), icon="⏪", url_path="replay"),
    st.Page(adviser.page, title=L("Legal adviser", "Conseiller juridique"), icon="📚", url_path="adviser"),
    st.Page(readiness.page, title=L("Readiness and twins", "Préparation et jumeaux"), icon="📊", url_path="readiness"),
    st.Page(knowledge.page, title=L("Knowledge base", "Base de connaissances"), icon="🗂️", url_path="knowledge"),
    st.Page(about.page, title=L("Architecture", "Architecture"), icon="🏛️", url_path="architecture"),
]
nav = st.navigation(pages)
s = config.settings
st.sidebar.markdown("---")
st.sidebar.caption(f"Brain: **{s.brain}**" + (f" · {s.llm_model}" if s.brain == "llm" else "") + f" · v{__version__}")
st.sidebar.caption("ITU AI for Good Lab hackathon (UAE 2026)")
st.markdown(f"<div class='banner'>{L('Fictional exercise. Not a real alert. ALERTE never sends messages to real people.', 'Exercice fictif. Ceci n’est pas une vraie alerte. ALERTE n’envoie aucun message à de vraies personnes.')}</div>",
            unsafe_allow_html=True)
nav.run()
