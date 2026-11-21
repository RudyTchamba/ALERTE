"""Vocabulaires du module gaps (aucun nom de pays ni d'institution : généricité, doc 09 §9.3)."""
from __future__ import annotations

ENGINE_VERSION = "gaps-1.0"

# 17 catégories du brief (doc 09 §9.2)
CATEGORIES = (
    "mandate_absent_or_incomplete", "ambiguous_responsibility", "overlapping_responsibilities", "conflicting_mandates",
    "missing_coordination_mechanism", "information_sharing_deficit", "regulatory_gap", "legislative_gap",
    "public_policy_gap", "standardization_gap", "technical_gap", "operational_gap", "governance_gap",
    "institutional_capacity_gap", "interoperability_gap", "oversight_mechanism_gap", "crisis_preparedness_response_gap",
)
BASES = ("documented", "observed", "inferred", "hypothesis")
BASIS_RANK = {b: i for i, b in enumerate(BASES)}  # plus petit = plus fort
CONFIDENCES = ("high", "medium", "low")
STATUSES = ("proposed", "confirmed", "disputed", "rejected")
ORIGINS = ("rule", "coordinator_signal", "agent_hypothesis", "imported")
CAUSES = ("institutional", "documentary", "artifact", "undetermined")
EVIDENCE_KINDS = ("mandate", "chunk", "event", "message", "decision", "negative_search", "coordinator_signal")
EVIDENCE_ROLES = ("supports", "counter", "context")
REALITY_LABELS = ("real", "partially_real", "not_real")
REGISTRY_RANK = {"unreviewed": 0, "partial": 1, "reviewed_complete": 2}

# signaux COORD (doc 08 §8.11) -> candidat ; `code` None = déterminé d'après le registre
SIGNALS = {
    "ORPHAN_REQUEST": {"code": "G1", "category": "missing_coordination_mechanism", "observed": False, "absence": True},
    "NO_OWNER": {"code": "G1", "category": "mandate_absent_or_incomplete", "observed": False, "absence": True},
    "CLAIM_OVERLAP": {"code": "G2", "category": "ambiguous_responsibility", "observed": True, "absence": False},
    "CONFLICTING_DECISIONS": {"code": "G5", "category": "conflicting_mandates", "observed": True, "absence": False},
    "MISSING_BASIS": {"code": None, "category": None, "observed": True, "absence": True},
    "NO_RESPONSE": {"code": "X4", "category": "operational_gap", "observed": True, "absence": False},
}
IGNORED_SIGNALS = ("UNSUPPORTED_DECISION",)  # qualité (T2), jamais une lacune

# indices (`gap_flags.hint`) -> (code, catégorie). Un code G rattache l'hypothèse au candidat de règle correspondant.
HINTS = {
    "no_owner": ("G1", "mandate_absent_or_incomplete"), "orphan": ("G1", "missing_coordination_mechanism"),
    "overlap": ("G2", "overlapping_responsibilities"), "no_procedure": ("G3", "regulatory_gap"),
    "dependency": ("G4", "regulatory_gap"), "conflict": ("G5", "conflicting_mandates"),
    "liability": ("G6", "governance_gap"), "inclusion": ("G7", "governance_gap"),
    "oversight": ("G8", "oversight_mechanism_gap"), "security": ("G9", "crisis_preparedness_response_gap"),
    "cross_border": ("G10", "interoperability_gap"),
    "technical": ("X2", "technical_gap"), "capacity": ("X2", "institutional_capacity_gap"),
    "standard": ("X2", "standardization_gap"), "policy": ("X2", "public_policy_gap"),
    "legislative": ("X2", "legislative_gap"), "information_sharing": ("X2", "information_sharing_deficit"),
}
DEFAULT_HYPOTHESIS = ("X0", "operational_gap")

NEG_QUERY_TEMPLATES = {
    "fr": ["{label}", "autorité compétente pour {label}", "compétence et responsabilité : {label}"],
    "en": ["{label}", "authority responsible for {label}", "power and duty to {label}"],
    "es": ["{label}", "autoridad competente para {label}"],
    "ar": ["{label}"],
}
DEFAULT_NEG_CONFIG = {"strong_score": 0.65, "weak_score": 0.35, "k": 5}
