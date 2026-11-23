"""Thésaurus de crise (expansion de requête) et priorité à l'autorité de la source."""
from __future__ import annotations

from app.knowledge.indexes import Fts5Index
from app.knowledge.search import AUTHORITY
from app.knowledge.textproc import analyze, expand_query


def test_crisis_thesaurus_links_agent_words_to_legal_vocabulary():
    q = expand_query("plan ORSEC et alerte des populations après la crue")
    for w in ("urgence", "catastrophe", "majeur", "diffusion"):
        assert w in q
    expr = Fts5Index.match_expr(expand_query("crue ORSEC"))
    assert analyze("urgence", for_query=True) in expr and analyze("catastrophe", for_query=True) in expr
    assert expand_query("choléra") == "choléra"  # aucun ajout hors du vocabulaire de crise


def test_official_sources_outrank_secondary_ones():
    assert AUTHORITY["official"] > AUTHORITY["summary"] > AUTHORITY["unofficial"]
