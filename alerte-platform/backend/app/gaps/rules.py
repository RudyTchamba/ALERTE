"""Table des règles G1-G10 (doc 09 §9.3). Chaque règle est une ENTRÉE DE TABLE : prédicat sur le registre actif + demandes
+ étiquettes d'inject. Aucun nom de pays/institution : seuls des `kind`, des actions et des étiquettes sont lus."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Bump:
    """Relève la gravité à `severity` si (au moins une étiquette de any_of) ET (toutes celles de all_of)."""

    severity: int
    any_of: frozenset[str] = frozenset()
    all_of: frozenset[str] = frozenset()

    def applies(self, tags: frozenset[str]) -> bool:
        return (not self.any_of or bool(self.any_of & tags)) and self.all_of <= tags


@dataclass(frozen=True)
class GapRule:
    code: str
    evaluator: str                       # absence | overlap | procedure | dependency | conflict
    names: dict[str, str]
    category: str
    kinds: tuple[str, ...] = ()          # `kind` de mandat testés (holders)
    required_tags: frozenset[str] = frozenset()
    match: str = "action"                # action | action_or_domain
    base_severity: int = 2
    bumps: tuple[Bump, ...] = ()
    crisis_category_tag: str | None = None   # étiquette faisant basculer la catégorie en « crise » (G1/G3 time_critical)
    negative_search: bool = False        # absence testée par recherche négative (§9.5)
    absence_claim: bool = True           # la règle affirme une ABSENCE => condition d'intégrité du registre
    priority: str = "P0"
    texts: dict[str, str] = field(default_factory=dict)

    def severity(self, tags: frozenset[str]) -> int:
        return max([self.base_severity] + [b.severity for b in self.bumps if b.applies(tags)])


_LIFE = frozenset({"life_risk"})
_LIFE_RIGHTS = frozenset({"life_risk", "rights_risk"})

RULES: tuple[GapRule, ...] = (
    GapRule("G1", "absence", {"fr": "Responsabilité orpheline", "en": "Orphan responsibility"},
            "mandate_absent_or_incomplete", kinds=("power", "duty"), bumps=(Bump(3, any_of=_LIFE_RIGHTS),),
            crisis_category_tag="time_critical", negative_search=True, priority="P0",
            texts={"fr": "Aucun mandat validé ({kinds}) pour l'action « {label} » dans le registre actif.",
                   "en": "No validated mandate ({kinds}) for action \"{label}\" in the active registry."}),
    GapRule("G2", "overlap", {"fr": "Mandats qui se chevauchent", "en": "Overlapping mandate"},
            "overlapping_responsibilities", kinds=("power",), bumps=(Bump(3, all_of=frozenset({"time_critical", "life_risk"})),),
            priority="P0",
            texts={"fr": "Au moins deux institutions ont le pouvoir d'agir sur « {label} » sans mandat de chef de file.",
                   "en": "At least two institutions hold the power to act on \"{label}\" and none is designated lead."}),
    GapRule("G3", "procedure", {"fr": "Procédure manquante", "en": "Missing procedure"}, "regulatory_gap",
            kinds=("power", "duty", "lead"), bumps=(Bump(3, any_of=_LIFE),), crisis_category_tag="time_critical",
            negative_search=True, priority="P0",
            texts={"fr": "L'action « {label} » a des détenteurs mais aucune procédure spécifique{deadline}.",
                   "en": "Action \"{label}\" has holders but no specific procedure{deadline}."}),
    GapRule("G4", "dependency", {"fr": "Dépendance vers une pièce manquante", "en": "Dependency on a missing piece"},
            "regulatory_gap", kinds=("power", "duty", "lead"), priority="P1",
            texts={"fr": "Le mandat sur « {label} » dépend d'une pièce non résolue : {dep}.",
                   "en": "The mandate on \"{label}\" depends on an unresolved piece: {dep}."}),
    GapRule("G5", "conflict", {"fr": "Objectifs contradictoires", "en": "Conflict of objectives"}, "conflicting_mandates",
            kinds=("duty",), absence_claim=False, priority="P1",
            texts={"fr": "Deux devoirs liés par un conflit sont déclenchés ensemble : « {label} ».",
                   "en": "Two conflicting duties are triggered together: \"{label}\"."}),
    GapRule("G6", "absence", {"fr": "Responsabilité des dommages", "en": "Liability gap"}, "governance_gap",
            kinds=("liability",), required_tags=frozenset({"harm_possible"}), match="action_or_domain",
            bumps=(Bump(3, any_of=_LIFE_RIGHTS),), negative_search=True, priority="P1",
            texts={"fr": "Aucun mandat de responsabilité (`liability`) pour « {label} » alors qu'un dommage est possible.",
                   "en": "No liability mandate for \"{label}\" although harm is possible."}),
    GapRule("G7", "absence", {"fr": "Inclusion", "en": "Inclusion gap"}, "governance_gap", kinds=("inclusion",),
            required_tags=frozenset({"public_communication"}), match="action_or_domain", base_severity=1,
            bumps=(Bump(2, any_of=_LIFE),), negative_search=True, priority="P1",
            texts={"fr": "Aucun mandat d'inclusion (langues, accessibilité, canaux) pour « {label} ».",
                   "en": "No inclusion mandate (languages, accessibility, channels) for \"{label}\"."}),
    GapRule("G8", "absence", {"fr": "Supervision humaine de l'IA", "en": "AI oversight gap"}, "oversight_mechanism_gap",
            kinds=("human_oversight",), required_tags=frozenset({"ai_output_used_in_decision"}), match="action_or_domain",
            bumps=(Bump(3, any_of=_LIFE),), negative_search=True, priority="P0",
            texts={"fr": "Aucun mandat de supervision humaine pour « {label} » alors qu'une sortie d'IA est utilisée.",
                   "en": "No human-oversight mandate for \"{label}\" although an AI output is used."}),
    GapRule("G9", "absence", {"fr": "Protection du canal", "en": "Security gap"}, "crisis_preparedness_response_gap",
            kinds=("channel_protection",), required_tags=frozenset({"channel_abuse"}), match="action_or_domain",
            bumps=(Bump(3, any_of=_LIFE),), negative_search=True, priority="P1",
            texts={"fr": "Aucun mandat de protection du canal pour « {label} » alors qu'un abus du canal est possible.",
                   "en": "No channel-protection mandate for \"{label}\" although channel abuse is possible."}),
    GapRule("G10", "absence", {"fr": "Transfrontalier", "en": "Cross-border gap"}, "interoperability_gap",
            kinds=("international_agreement",), required_tags=frozenset({"foreign_actor"}), match="action_or_domain",
            negative_search=True, priority="P1",
            texts={"fr": "Aucun mandat d'accord international pour « {label} » alors qu'un acteur étranger intervient.",
                   "en": "No international-agreement mandate for \"{label}\" although a foreign actor is involved."}),
)
RULES_BY_CODE = {r.code: r for r in RULES}

# codes d'extension (hors G1-G10) : sévérité de base et catégorie par défaut
EXTENSIONS = {
    "X0": {"names": {"fr": "Hypothèse d'agent", "en": "Agent hypothesis"}, "severity": 1, "category": "operational_gap",
           "life_bump": 2},
    "X2": {"names": {"fr": "Lacune signalée par un agent", "en": "Agent-reported gap"}, "severity": 1,
           "category": "technical_gap", "life_bump": 2},
    "X4": {"names": {"fr": "Observation opérationnelle", "en": "Operational observation"}, "severity": 2,
           "category": "operational_gap", "life_bump": 3},
}


def rules_digest() -> list[dict]:
    """Représentation canonique de la table (entrée du pré-engagement)."""
    return [{"code": r.code, "evaluator": r.evaluator, "kinds": list(r.kinds), "tags": sorted(r.required_tags),
             "match": r.match, "base": r.base_severity, "category": r.category,
             "bumps": [[b.severity, sorted(b.any_of), sorted(b.all_of)] for b in r.bumps]} for r in RULES]
