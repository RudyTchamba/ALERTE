"""Thésaurus de crise (expansion de requête) et priorité à l'autorité de la source."""
from __future__ import annotations

from app.knowledge.indexes import Fts5Index
from app.knowledge.search import _AUTHORITY_BASE, AUTHORITY, AUTHORITY_SPREAD
from app.knowledge.textproc import analyze, expand_query


def test_crisis_thesaurus_links_agent_words_to_legal_vocabulary():
    q = expand_query("plan ORSEC et alerte des populations après la crue")
    for w in ("urgence", "catastrophe", "majeur", "diffusion"):
        assert w in q
    expr = Fts5Index.match_expr(expand_query("crue ORSEC"))
    assert analyze("urgence", for_query=True) in expr and analyze("catastrophe", for_query=True) in expr
    assert expand_query("choléra") == "choléra"  # aucun ajout hors du vocabulaire de crise


def test_official_sources_outrank_secondary_ones():
    """Le barème d'autorité reste ordonné ; son AMPLITUDE est réglable (ALERTE_AUTHORITY_SPREAD)."""
    assert _AUTHORITY_BASE["official"] > _AUTHORITY_BASE["summary"] > _AUTHORITY_BASE["unofficial"]


def test_authority_weighting_is_neutral_by_default_because_rrf_scores_are_tightly_spaced():
    """Mesuré (docs/knowledge-base/retrieval-evaluation.md) : même un facteur de 0,96 enterrait un texte « unofficial » (loi 86/016, art. 3)
    dont le passage était le meilleur résultat lexical. Défaut neutre ; l'amplitude est un réglage explicite."""
    assert AUTHORITY_SPREAD == 0.0
    assert len(set(AUTHORITY.values())) == 1
