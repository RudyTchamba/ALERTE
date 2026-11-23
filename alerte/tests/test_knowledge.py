from alerte.knowledge.chunk import article_ref, chunk_document
from alerte.knowledge.mandates import load_mandates
from alerte.knowledge.store import get_store
from alerte.textutil import bridge_query, fold, tokenize


def test_article_chunking_french_and_english():
    text = ("TITRE I\nArticle premier.- La présente loi régit la protection civile.\n"
            "Article 2.- Le ministre chargé de l'administration territoriale coordonne les secours.\n"
            "Article 3 bis : Les opérateurs relaient les alertes.\nSection 4 Mandatory alerts. Operators must send alerts.")
    chunks = chunk_document(text)
    labels = [article_ref(lbl) for lbl, _ in chunks]
    assert "Article premier" in labels
    assert "Article 2" in labels
    assert any(lbl.startswith("Article 3") for lbl in labels)
    assert "Section 4" in labels


def test_long_text_without_articles_uses_windows():
    text = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_document(text)
    assert len(chunks) >= 4
    assert all(len(c.split()) <= 256 for _, c in chunks)


def test_fold_and_bridge():
    assert fold("Données à l'étranger") == "donnees a l'etranger"
    assert "transfer" in bridge_query("transfert de données à l'étranger")
    assert "flood" in tokenize("Floods") or "flood" in [t.rstrip("s") for t in tokenize("Floods")]


def test_index_built_and_manifest_coverage():
    s = get_store()
    st = s.stats()
    assert st["chunks"] > 80
    assert {"CM", "AE", "GL"} <= set(st["by_collection"])
    assert "CM-S01" in s.documents and "CM-02" in s.documents       # official text listed even if not downloaded


def test_search_country_filter_and_fictional_excluded():
    s = get_store()
    hits = s.search("HydroSense validity sensors", 5)
    assert all(h.chunk.reliability != "fictional" for h in hits)
    hits = s.search("HydroSense validity sensors", 5, include_fictional=True)
    assert any(h.chunk.doc_id == "SCN-01" for h in hits)
    hits = s.search("personal data transfer abroad", 5, countries=["AE"])
    assert hits and all(h.chunk.country == "AE" for h in hits)


def test_institution_wall():
    s = get_store()
    # the data-protection summary is tagged for DPA/MINSANTE/OPS/HYDRO: civil protection cannot see it
    hits = s.search("prior authorisation transfer personal data abroad", 10, countries=["CM"], institutions=["DPC"])
    assert all(h.chunk.doc_id != "CM-S02" for h in hits)
    hits = s.search("prior authorisation transfer personal data abroad", 10, countries=["CM"], institutions=["DPA"])
    assert hits[0].chunk.doc_id == "CM-S02"


def test_french_question_finds_english_text():
    s = get_store()
    hits = s.search("Quelle autorisation faut-il pour transférer des données personnelles à l'étranger ?", 5, countries=["CM"])
    assert any(h.chunk.doc_id == "CM-S02" for h in hits)


def test_mandate_map_consistency():
    mm = load_mandates(refresh=True)
    assert mm.holders("compel_operator_alert", "CM") == []           # the gap the story is built around
    assert mm.holders("compel_operator_alert", "AE") == []           # report v2: no text found in the UAE either
    assert [ln.institution for ln in mm.holders("set_alert_standard", "AE")] == ["ART"]   # TDRA sets standards, it cannot compel
    assert mm.lead_of("coordinate_response", "CM") == "DPC"
    s = get_store()
    for ln in mm.lines:
        assert ln.evidence in {"documented", "inferred", "assumed"}
        if ln.source_doc:
            assert ln.source_doc in s.documents, f"{ln.line_id} cites unknown {ln.source_doc}"
        if ln.evidence == "assumed":
            assert ln.assumed_by, f"{ln.line_id}: assumptions must say who made them"


def test_retrieval_target_t1():
    from alerte.evaluation import eval_retrieval
    r = eval_retrieval()
    assert r["score"] >= 0.8, [row for row in r["rows"] if not row["found"]]
