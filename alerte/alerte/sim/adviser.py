"""The policy and legal adviser: answers any question in four parts, with sources.

1. What the national texts say (with articles)   2. What is unclear or missing
3. How other jurisdictions handle it               4. A recommendation, clearly labelled
"""

from __future__ import annotations

from alerte import config
from alerte.analysis.gaps import CATEGORY_GAP, action_gap_type
from alerte.analysis.precedents import find_precedents
from alerte.i18n import t
from alerte.knowledge.ingest import ensure_index
from alerte.knowledge.mandates import MandateMap, load_mandates
from alerte.knowledge.store import KnowledgeStore, get_store
from alerte.models import ActionDef, LegalAnswer
from alerte.sim.brain import OfflineBrain, action_label, make_brain, mid
from alerte.sim.citations import check_all
from alerte.textutil import bridge_query, tokenize


def guess_action(question: str, mm: MandateMap) -> ActionDef | None:
    q = set(tokenize(bridge_query(question)))
    best, best_score = None, 0.0
    for a in mm.actions.values():
        words = set(tokenize(a.label + " " + " ".join(a.keywords)))
        score = len(q & words) / (len(words) ** 0.5 or 1)
        if score > best_score:
            best, best_score = a, score
    return best if best_score >= 0.5 else None


def ask(question: str, country: str = "CM", lang: str | None = None, brain: OfflineBrain | None = None,
        store: KnowledgeStore | None = None, mm: MandateMap | None = None, drill_gaps: list | None = None,
        action_code: str | None = None) -> LegalAnswer:
    ensure_index()
    lang = (lang or config.settings.language).lower()
    store = store or get_store()
    mm = mm or load_mandates()
    brain = brain or make_brain(None, store, mm)
    action = mm.actions.get(action_code) if action_code else guess_action(question, mm)
    query = question + ((" " + action.label + " " + " ".join(action.keywords)) if action else "")
    legal_types = ["law", "decree", "plan", "strategy", "guidance", "standard"]
    national = [h.chunk for h in store.search(query, config.settings.top_k, countries=[country], doc_types=legal_types)]
    if len(national) < 2:  # fall back to facts and reports
        seen = {c.chunk_id for c in national}
        national += [h.chunk for h in store.search(query, config.settings.top_k, countries=[country])
                     if h.chunk.chunk_id not in seen][: config.settings.top_k - len(national)]
    related: list[str] = []
    gtype = "G1"
    if action is not None:
        holders = mm.holders(action.code, country)
        label = mid(action_label(action, lang))
        if not holders:
            gtype = action_gap_type(action, "G1")
            related.append(t("gap_no_holder", lang, label=label))
        elif not any(ln.procedure for ln in holders):
            gtype = action_gap_type(action, "G3")
            related.append(t("gap_no_proc", lang, label=label))
        for ln in holders:
            if ln.dependency_ready in ("no", "unknown") and ln.depends_on:
                related.append(t("gap_dependency", lang, label=label, dep=ln.depends_on))
    if drill_gaps:
        related += [g.title for g in drill_gaps if action is not None and g.action == action.code and g.title not in related]
    precedents = find_precedents(action, gtype, store, exclude_country=country)
    answer = brain.legal_answer(question, national, precedents, related, lang)
    answer.citations = check_all(answer.citations, store)
    return answer


def format_answer(a: LegalAnswer, lang: str = "en") -> str:
    lines = [f"QUESTION: {a.question}", "", t("h_national", lang), a.national, "",
             t("h_missing", lang), a.missing, "", t("h_elsewhere", lang)]
    for p in a.elsewhere:
        lines.append(f"   - {p.jurisdiction}: {p.instrument}{(', ' + p.article) if p.article else ''}. {p.what_it_does}")
    if not a.elsewhere:
        lines.append("   (no example found in the library)")
    lines += ["", t("h_rec", lang), a.recommendation, "", t("h_sources", lang)]
    for c in a.citations:
        lines.append(f"   - {c.doc_id} {c.article} [{'verified' if c.verified else 'NOT VERIFIED'}]")
    lines += ["", a.disclaimer]
    return "\n".join(lines)
