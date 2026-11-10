"""The knowledge base: search, document manifest (with reliability), who-does-what map."""

from __future__ import annotations

import streamlit as st

from alerte.knowledge.mandates import load_mandates
from alerte.knowledge.store import get_store
from alerte.ui.theme import L, badge


def page() -> None:
    st.title("🗂️ " + L("Knowledge base", "Base de connaissances"))
    store = get_store()
    s = store.stats()
    st.caption(f"{s['documents']} {L('documents listed', 'documents listés')} · {s['chunks']} {L('passages indexed', 'passages indexés')} · "
               f"{s['by_collection']} · {L('vectors', 'vecteurs')}: {s['vectors'] or L('keyword search only', 'recherche par mots-clés')}")
    t1, t2, t3, t4, t5 = st.tabs([L("Search", "Recherche"), L("Documents", "Documents"), L("Who does what", "Qui fait quoi"),
                                  L("Add documents", "Ajouter des documents"), L("Extraction quality", "Qualité d'extraction")])
    with t1:
        q = st.text_input(L("Search the library", "Rechercher"), "public warning operators")
        countries = st.multiselect(L("Countries", "Pays"), sorted({c.country for c in store.chunks}))
        for h in store.search(q, 8, countries=countries or None):
            c = h.chunk
            st.markdown(f"**{c.doc_id} {c.article}** · {c.title} " + badge(c.reliability, "amber" if c.reliability == "summary" else "green")
                        + (badge(c.extraction, "red" if c.needs_review else "blue") if c.extraction else ""), unsafe_allow_html=True)
            st.caption(c.text[:400] + ("…" if len(c.text) > 400 else ""))
    with t2:
        indexed = {c.doc_id for c in store.chunks}
        st.dataframe([{"ID": d.doc_id, L("Title", "Titre"): d.title, L("Country", "Pays"): d.country, "Type": d.doc_type,
                       L("Reliability", "Fiabilité"): d.reliability.value, L("Indexed", "Indexé"): d.doc_id in indexed, L("Link", "Lien"): d.url}
                      for d in store.documents.values()],
                     column_config={L("Link", "Lien"): st.column_config.LinkColumn(L("Link", "Lien"))}, hide_index=True, use_container_width=True)
    with t4:
        add_documents_tab()
    with t5:
        extraction_tab()
    with t3:
        mm = load_mandates()
        country = st.radio(L("Map", "Carte"), ["AE", "CM"], horizontal=True, key="mapc")
        st.dataframe(mm.to_rows(country), hide_index=True, use_container_width=True)


def add_documents_tab() -> None:
    """Upload files into data/docs/inbox and rebuild the knowledge base, with live progress."""
    from alerte import config
    from alerte.knowledge.ingest import build_index
    from alerte.knowledge.extract import SUPPORTED, ocr
    st.write(L("Drop any document here: scanned or digital PDF, photo of a page, Word, PowerPoint, Excel, text. "
               "Everything is read, scans by OCR, tables and pictures with text included, then added to the knowledge base.",
               "Déposez ici n'importe quel document : PDF scanné ou numérique, photo de page, Word, PowerPoint, Excel, texte. "
               "Tout est lu (OCR pour les scans, tableaux et images avec texte compris) puis ajouté à la base."))
    eng = ocr.status()
    (st.success if eng.tesseract else st.error)(L("OCR engine: ", "Moteur OCR : ") + eng.describe())
    files = st.file_uploader(L("Documents", "Documents"), accept_multiple_files=True,
                             type=sorted(e.lstrip(".") for e in SUPPORTED))
    inbox = config.settings.docs_dir / "inbox"
    if files and st.button(L("Save and read these documents", "Enregistrer et lire ces documents"), type="primary"):
        inbox.mkdir(parents=True, exist_ok=True)
        for f in files:
            (inbox / f.name).write_bytes(f.getbuffer())
        log = st.empty()
        lines: list[str] = []

        def progress(msg: str) -> None:
            lines.append(msg)
            log.code("\n".join(lines[-14:]))

        with st.spinner(L("Reading all documents (scans can take a minute per page)…", "Lecture de tous les documents…")):
            rep = build_index(embed_provider="none", progress=progress)
        from alerte.knowledge.store import get_store
        get_store(refresh=True)
        st.success(rep.summary())
        if rep.failed:
            st.error(L("No text could be extracted from: ", "Aucun texte extrait de : ") + ", ".join(f"{k} ({v})" for k, v in rep.failed.items()))
        if rep.review:
            st.warning(L("Some pages need a human proofread: see the “Extraction quality” tab.", "Des pages doivent être relues : voir l'onglet « Qualité d'extraction »."))
    st.caption(f"{L('Folder', 'Dossier')}: {inbox}  ·  " + L("You can also copy files into any subfolder of data/docs and run “python -m alerte ingest”.",
                                                           "Vous pouvez aussi copier les fichiers dans data/docs et lancer « python -m alerte ingest »."))


def extraction_tab() -> None:
    import json
    from alerte import config
    rep_path = config.settings.index_dir / "extraction_report.json"
    if not rep_path.exists():
        st.info(L("No extraction report yet. Build the index with “python -m alerte ingest”.", "Pas encore de rapport : lancez « python -m alerte ingest »."))
        return
    rep = json.loads(rep_path.read_text(encoding="utf-8"))
    st.caption(rep["summary"])
    if rep["failed"]:
        st.error(L("No text could be extracted from these files:", "Aucun texte extrait de ces fichiers :"))
        st.dataframe([{"doc": k, L("reason", "raison"): v} for k, v in rep["failed"].items()], hide_index=True, use_container_width=True)
    if rep["duplicates"]:
        st.info(L("Identical files (indexed once): ", "Fichiers identiques (indexés une fois) : ") + ", ".join(f"{k} = {v}" for k, v in rep["duplicates"].items()))
    st.markdown("##### " + L("Every file, how it was read", "Chaque fichier, comment il a été lu"))
    st.dataframe([{"doc": d["doc_id"], L("file", "fichier"): d["file"].replace("\\", "/").split("/")[-1], L("method", "méthode"): d["method"],
                   L("pages", "pages"): d["pages"], "OCR": d["ocr_pages"], L("tables", "tableaux"): d["tables"],
                   L("OCR confidence", "confiance OCR"): d["mean_ocr_confidence"], L("to proofread", "à relire"): ", ".join(map(str, d["review_pages"])),
                   L("problem", "problème"): d["failed"]} for d in rep["documents"]], hide_index=True, use_container_width=True)
    flagged = [d for d in rep["documents"] if d["review_pages"]]
    if flagged:
        st.warning(L("These pages were read with low confidence or the two readings disagreed. Check them against the original.",
                     "Ces pages ont été lues avec une faible confiance ou les deux lectures divergent. Vérifiez-les avec l'original."))
        for d in flagged:
            with st.expander(f"{d['doc_id']} · {L('pages', 'pages')} {d['review_pages']}"):
                for p in d["page_details"]:
                    if p["flags"]:
                        st.markdown(f"- {L('page', 'page')} {p['page']}: " + "; ".join(p["flags"]))
                st.code(f"python -m alerte review {d['doc_id']}")
                st.caption(L("Fix the draft, save it next to the source as <file>.corrected.md, then run ingest again.",
                             "Corrigez le brouillon, enregistrez-le à côté de la source sous <fichier>.corrected.md puis relancez l'ingestion."))
