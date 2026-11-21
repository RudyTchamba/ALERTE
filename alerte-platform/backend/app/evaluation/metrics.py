"""Métriques T1–T6, benchmark et contrôle négatif : fonctions PURES (sans base ni modèle), testables sur données
fabriquées. Règle d'or (I6) : une valeur non calculable renvoie `status="not_computed"` + `reason`, `value=None` — jamais 0."""
from __future__ import annotations

import datetime as dt
import math
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from typing import Any

THRESHOLDS: dict[str, dict[str, Any]] = {
    "T1": {"op": ">=", "value": 0.80, "label": "≥ 80 % (bon document et bon article dans le top 5)", "min_questions": 40},
    "T2": {"op": ">=", "value": 0.95, "label": "≥ 95 % de citations vérifiées"},
    "T3": {"op": ">=", "value": 0.80, "label": "≥ 80 % des lacunes prévues retrouvées"},
    "T4": {"op": ">=", "value": 0.85, "label": "≥ 85 % de lacunes réelles ou partiellement réelles"},
    "T5": {"op": ">=", "value": 0.80, "label": "≥ 80 % des empreintes retrouvées dans ≥ 2/3 des exercices"},
    "T6": {"max_seconds": 20 * 60, "max_llm_calls": 199, "label": "< 20 min et < 200 appels LLM"},
}
POSITIVE = {"real", "partially_real"}


def not_computed(metric: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"metric": metric, "status": "not_computed", "value": None, "passed": None, "reason": reason,
            "threshold": THRESHOLDS.get(metric), **extra}


def computed(metric: str, value: float | None, passed: bool | None, **extra: Any) -> dict[str, Any]:
    return {"metric": metric, "status": "computed", "value": value, "passed": passed, "reason": None,
            "threshold": THRESHOLDS.get(metric), **extra}


def _meets(metric: str, value: float) -> bool:
    return value >= THRESHOLDS[metric]["value"]


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


# --------------------------------------------------------------------------- T2
def t2_citations(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    total = ok = decisions = 0
    failures: list[dict[str, Any]] = []
    for e in events:
        if e["type"] != "CITATION_CHECK":
            continue
        decisions += 1
        for c in (e.get("payload") or {}).get("citations") or []:
            total += 1
            if c.get("pass") is True:
                ok += 1
            else:
                failures.append({"seq": e.get("seq"), "chunk_id": c.get("chunk_id"), "reason": c.get("reason")})
    if total == 0:
        return not_computed("T2", "aucune citation vérifiée (CITATION_CHECK absent ou sans citation)", checks=decisions)
    v = ok / total
    return computed("T2", v, _meets("T2", v), numerator=ok, denominator=total, checks=decisions, failures=failures[:50])


# --------------------------------------------------------------------------- T6
def _dt(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def t6_time_calls(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    injects = [e for e in events if e["type"] == "INJECT"]
    if not injects or not events:
        return not_computed("T6", "aucun INJECT dans le ledger : durée non mesurable")
    first = min(_dt(e["real_time"]) for e in injects)
    last = max(_dt(e["real_time"]) for e in events)
    seconds = max(0.0, (last - first).total_seconds())
    calls = sum(1 for e in events if e["type"] == "LLM_CALL")
    th = THRESHOLDS["T6"]
    ok = seconds < th["max_seconds"] and calls <= th["max_llm_calls"]
    snap = next((e for e in events if e["type"] == "SNAPSHOT"), None)
    mode = ((snap or {}).get("payload") or {}).get("ai_mode")
    note = ("mode sans IA : 0 appel LLM, durée non représentative d'un exercice avec modèle"
            if mode == "scripted" else None)
    return computed("T6", seconds, ok, wall_seconds=seconds, llm_calls=calls, ai_mode=mode, note=note,
                    time_ok=seconds < th["max_seconds"], calls_ok=calls <= th["max_llm_calls"])


# --------------------------------------------------------------------------- T1
def _norm(s: str | None) -> str:
    return "".join((s or "").lower().split())


def hit_matches(hit: dict[str, Any], doc_code: str, article: str | None) -> bool:
    if _norm(hit.get("doc_code")) != _norm(doc_code):
        return False
    return article is None or _norm(hit.get("article")) == _norm(article)


def t1_retrieval(questions: Sequence[dict[str, Any]], search: Callable[[dict[str, Any]], list[dict[str, Any]]]) -> dict[str, Any]:
    """`questions` : {id, question, expected_doc_code, expected_article?, category?}. `search(q)` -> hits classés
    (≥ 10 utiles) `{doc_code, article, ...}`. Pertinence binaire ; nDCG@10 avec UNE réponse attendue (idéal = rang 1)."""
    th = THRESHOLDS["T1"]
    if not questions:
        return not_computed("T1", "aucun jeu de questions pour cette base de connaissances")
    rr: list[float] = []
    r5 = r10 = 0
    ndcg: list[float] = []
    per_cat: dict[str, list[int]] = {}
    misses: list[dict[str, Any]] = []
    for q in questions:
        hits = search(q)[:10]
        rank = next((i for i, h in enumerate(hits, 1) if hit_matches(h, q["expected_doc_code"], q.get("expected_article"))), None)
        rr.append(1 / rank if rank else 0.0)
        ndcg.append(1 / math.log2(rank + 1) if rank else 0.0)
        r5 += 1 if rank and rank <= 5 else 0
        r10 += 1 if rank else 0
        cat = per_cat.setdefault(q.get("category") or "unspecified", [0, 0])
        cat[1] += 1
        cat[0] += 1 if rank and rank <= 5 else 0
        if not rank or rank > 5:
            misses.append({"question_id": q.get("id"), "question": q["question"], "rank": rank})
    n = len(questions)
    v = r5 / n
    enough = n >= th["min_questions"]
    return computed("T1", v, (_meets("T1", v) if enough else None), n_questions=n, recall_at_5=v, recall_at_10=r10 / n,
                    mrr=sum(rr) / n, ndcg_at_10=sum(ndcg) / n, hits_at_5=r5,
                    confidence_interval=wilson_interval(r5, n),
                    insufficient_sample=not enough,
                    note=None if enough else f"échantillon insuffisant ({n} < {th['min_questions']} questions) : seuil non évalué",
                    by_category={k: {"hits_at_5": a, "n": b} for k, (a, b) in per_cat.items()}, misses=misses[:50])


# --------------------------------------------------------------------------- T3
def t3_expected_gaps(fixtures: Sequence[dict[str, Any]], detected: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """`fixtures` : {expected_gap_key, label} (SCELLÉES, validées en amont) ; `detected` : lacunes {id, fingerprint, title, origin}."""
    if not fixtures:
        return not_computed("T3", "aucune fixture scellée pour ce scénario")
    fps = {g.get("fingerprint") for g in detected if g.get("fingerprint")}
    keys = {f["expected_gap_key"] for f in fixtures}
    found = [f for f in fixtures if f["expected_gap_key"] in fps]
    missed = [f for f in fixtures if f["expected_gap_key"] not in fps]
    new = [g for g in detected if g.get("fingerprint") not in keys]
    v = len(found) / len(fixtures)
    return computed("T3", v, _meets("T3", v), numerator=len(found), denominator=len(fixtures),
                    missed_fixtures=[{"expected_gap_key": f["expected_gap_key"], "label": f.get("label")} for f in missed],
                    new_gaps=[{"gap_id": g.get("id"), "fingerprint": g.get("fingerprint"), "title": g.get("title"),
                               "origin": g.get("origin"), "validation_status": g.get("validation_status")} for g in new])


# --------------------------------------------------------------------------- T4
def cohen_kappa(pairs: Sequence[tuple[str, str]]) -> float | None:
    n = len(pairs)
    if n == 0:
        return None
    po = sum(1 for a, b in pairs if a == b) / n
    ca, cb = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def t4_not_invented(gaps: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Précision à partir des `reality_label` des revues. Par lacune : dernier label de chaque relecteur ; avec ≥ 2
    relecteurs la lacune est « réelle » seulement si TOUS la jugent réelle/partiellement réelle (règle conservatrice)."""
    labelled: list[dict[str, Any]] = []
    reviewer_labels: dict[str, dict[str, str]] = {}
    for g in gaps:
        latest: dict[str, str] = {}
        for r in g.get("reviews") or []:
            if r.get("reality_label") in {"real", "partially_real", "not_real"}:
                latest[r.get("reviewer") or "?"] = r["reality_label"]
        if latest:
            labelled.append({"id": g.get("id"), "labels": latest})
            for who, lab in latest.items():
                reviewer_labels.setdefault(who, {})[g.get("id")] = lab
    if not labelled:
        return not_computed("T4", "aucune revue humaine avec reality_label", gaps_total=len(gaps))
    pos = sum(1 for x in labelled if all(lab in POSITIVE for lab in x["labels"].values()))
    n = len(labelled)
    v = pos / n
    kappa = None
    kappa_note = "κ non calculé : moins de 2 relecteurs"
    reviewers = sorted(reviewer_labels, key=lambda w: (-len(reviewer_labels[w]), w))
    if len(reviewers) >= 2:
        a, b = reviewers[0], reviewers[1]
        common = [(reviewer_labels[a][i], reviewer_labels[b][i]) for i in reviewer_labels[a] if i in reviewer_labels[b]]
        kappa = cohen_kappa(common)
        kappa_note = (f"κ de Cohen entre {a} et {b} sur {len(common)} lacunes communes (3 classes)"
                      if kappa is not None else "κ indéfini (accord attendu = 1 ou aucune lacune commune)")
    return computed("T4", v, _meets("T4", v), numerator=pos, denominator=n, gaps_total=len(gaps),
                    unreviewed=len(gaps) - n, reviewers=reviewers, confidence_interval=wilson_interval(pos, n),
                    kappa=kappa, kappa_note=kappa_note)


# --------------------------------------------------------------------------- T5
def t5_stability(per_exercise: dict[str, Sequence[dict[str, Any]]]) -> dict[str, Any]:
    n = len(per_exercise)
    if n < 3:
        return not_computed("T5", f"au moins 3 exercices clonés requis ({n} fourni(s))", exercises=sorted(per_exercise))
    counts: Counter[str] = Counter()
    for gaps in per_exercise.values():
        counts.update({g["fingerprint"] for g in gaps if g.get("fingerprint")})
    if not counts:
        return not_computed("T5", "aucune lacune détectée dans les exercices : stabilité non définie", exercises=sorted(per_exercise))
    need = math.ceil(2 * n / 3)
    stable = [k for k, c in counts.items() if c >= need]
    v = len(stable) / len(counts)
    return computed("T5", v, _meets("T5", v), numerator=len(stable), denominator=len(counts), exercises=sorted(per_exercise),
                    min_occurrences=need, found_in_all=sum(1 for c in counts.values() if c == n),
                    unstable=sorted(k for k, c in counts.items() if c < need))


# --------------------------------------------------------------------------- benchmark externe / contrôle négatif
def benchmark_match(items: Sequence[dict[str, Any]], detected: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return not_computed("benchmark", "ensemble de référence vide")
    mappable = [i for i in items if i.get("fingerprint")]
    if not mappable:
        return not_computed("benchmark", "aucun élément de l'ensemble n'est apparié à une empreinte", items=len(items))
    fps = {g.get("fingerprint") for g in detected}
    found = [i for i in mappable if i["fingerprint"] in fps]
    return computed("benchmark", len(found) / len(mappable), None, numerator=len(found), denominator=len(mappable),
                    not_mappable=len(items) - len(mappable),
                    missed=[i["label"] for i in mappable if i["fingerprint"] not in fps])


def negative_control(detected: Sequence[dict[str, Any]], demands: int | None, max_gaps: int = 0) -> dict[str, Any]:
    """Exercice à mandats COMPLETS : on attend ≈ 0 lacune issue des règles. Hypothèses d'agents et rejetées exclues."""
    rule = [g for g in detected if g.get("origin") != "agent_hypothesis" and g.get("validation_status") != "rejected"
            and g.get("evidence_basis") != "hypothesis"]
    rate = (len(rule) / demands) if demands else None
    return computed("negative_control", float(len(rule)), len(rule) <= max_gaps, false_positives=len(rule), demands=demands,
                    false_positive_rate=rate, max_gaps=max_gaps,
                    rate_note=None if demands else "taux non calculé : nombre de demandes inconnu",
                    gaps=[{"gap_id": g.get("id"), "title": g.get("title"), "fingerprint": g.get("fingerprint")} for g in rule])
