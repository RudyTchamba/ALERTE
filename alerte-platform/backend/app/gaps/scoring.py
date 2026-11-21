"""Base de preuve, confiance, cause (doc 09 §9.4, §9.9 #11) : règles ÉCRITES, pures, testées. Ré-appliquées après la recherche négative."""
from __future__ import annotations

from typing import TYPE_CHECKING

from . import constants as C

if TYPE_CHECKING:
    from .detection import GapCandidate


def _weaker(a: str, b: str) -> str:
    return a if C.BASIS_RANK[a] >= C.BASIS_RANK[b] else b


def has_non_agent_support(c: GapCandidate) -> bool:
    return any(e.role == "supports" and not e.is_agent for e in c.evidence)


def finalize(c: GapCandidate) -> None:
    """Calcule `evidence_basis`, `confidence`, `cause` à partir de la base provisoire et des drapeaux de la recherche négative."""
    basis = c.basis
    if c.needs_negative_search or c.absence:
        if c.strong_hit:                                            # contre-preuve : rétrogradation, jamais suppression
            basis = _weaker(basis, "inferred")
            c.note("contre-preuve trouvée dans le corpus : rétrogradé en « inferred »")
        if c.needs_negative_search and c.neg_status == "unavailable":
            basis = _weaker(basis, "inferred")
            c.note("recherche négative non exécutée : absence non documentée")
        if c.corpus_documents == 0 or (c.coverage is not None and c.coverage < 1.0):
            basis = _weaker(basis, "inferred")                       # absence dans un corpus incomplet ≠ preuve
            c.note("couverture documentaire incomplète : l'absence n'est pas une preuve d'inexistence")
    if not has_non_agent_support(c):                                # règle de promotion
        basis = "hypothesis"
    if basis == "observed" and c.scripted and not c.observed_signals:
        basis = "inferred"                                          # jamais observed en mode scripted
    c.evidence_basis = basis
    # confiance
    if c.proposed_mandate:
        c.confidence = "low"
    elif basis == "documented" and c.observed_signals >= 1:
        c.confidence = "high"
    elif basis == "documented":
        c.confidence = "medium"
    elif basis == "observed" and c.registry_state in ("partial", "reviewed_complete"):
        c.confidence = "medium"
    else:
        c.confidence = "low"
    # cause
    if c.artifact:
        c.cause = "artifact"
    elif c.absence and (c.corpus_documents == 0 or (c.coverage is not None and c.coverage < 1.0)):
        c.cause = "documentary"
    elif basis == "documented" or (basis == "observed" and c.registry_state == "reviewed_complete"):
        c.cause = "institutional"
    else:
        c.cause = "undetermined"
