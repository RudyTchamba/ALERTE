"""The policy and legal adviser agent, usable on its own."""

from __future__ import annotations

import streamlit as st

from alerte import config
from alerte.sim.adviser import ask
from alerte.ui.theme import L, lang


def page() -> None:
    st.title("📚 " + L("Policy and legal adviser", "Conseiller politique et juridique"))
    st.caption(L("Answers in four parts, with sources: what the national texts say, what is unclear or missing, how others handle it, "
                 "and a clearly labelled suggestion. It never gives a final opinion; confirm with a qualified lawyer.",
                 "Réponse en quatre parties, avec sources. Il ne donne jamais d'avis définitif : consultez un juriste qualifié."))
    country = st.radio(L("Country", "Pays"), ["AE", "CM"], horizontal=True, format_func=lambda c: {"CM": "Cameroon", "AE": "United Arab Emirates"}[c])
    q = st.text_input(L("Your question", "Votre question"),
                      "Who may order mobile operators to send a public alert?" if lang() == "en"
                      else "Qui peut ordonner aux opérateurs mobiles d'envoyer une alerte publique ?")
    if st.button(L("Ask", "Demander"), type="primary") and q.strip():
        with st.spinner(L("Searching the texts…", "Recherche dans les textes…")):
            a = ask(q, country=country, lang=lang())
        st.markdown("##### 1. " + L("What the national texts say", "Ce que disent les textes nationaux"))
        st.write(a.national)
        st.markdown("##### 2. " + L("What is unclear or missing", "Ce qui est flou ou manquant"))
        st.write(a.missing)
        st.markdown("##### 3. " + L("How others handle it", "Comment font les autres"))
        for p in a.elsewhere:
            link = f"[{p.instrument}{(', ' + p.article) if p.article else ''}]({p.url})" if p.url else p.instrument
            st.markdown(f"- **{p.jurisdiction}**: {link}. {p.what_it_does}  \n  *{L('Note (some written for Cameroon)', 'Note (certaines rédigées pour le Cameroun)')}:* {p.fit_note}")
        st.markdown("##### 4. " + L("Suggestion (for expert review)", "Suggestion (à valider par un expert)"))
        st.write(a.recommendation)
        with st.expander(L("Sources and quote checks", "Sources et vérification des citations")):
            for c in a.citations:
                st.markdown(f"- {'✅' if c.verified else '❌'} **{c.doc_id} {c.article}**: “{c.quote}”")
        st.caption(a.disclaimer)
