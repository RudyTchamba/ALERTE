"""Write the outputs of a finished drill: gap report, decision timeline, scorecard, assumptions,
and machine-readable JSON, in Markdown and standalone HTML."""

from __future__ import annotations

import html
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alerte.analysis.gaps import GAP_TYPES, GAP_TYPES_FR, expected_gap_coverage, find_gaps
from alerte.analysis.scorecard import score
from alerte.integrations.slack import notify_run
from alerte.models import as_dict
from alerte.sim.ledger import verify_ledger

if TYPE_CHECKING:  # pragma: no cover
    from alerte.sim.engine import Drill, DrillResult

SEV = {1: "1 (inconvenience)", 2: "2 (delay or extra cost)", 3: "3 (risk to life or rights)"}
SEV_FR = {1: "1 (gêne)", 2: "2 (retard ou surcoût)", 3: "3 (risque pour la vie ou les droits)"}


def citation_stats(drill: "Drill") -> dict[str, Any]:
    cites = [c for d in drill.decisions for c in d.legal_basis]
    checked = [c for c in cites if c.verified is not None]
    ok = sum(1 for c in checked if c.verified)
    return {"citations": len(cites), "verified": ok, "rate": round(ok / len(checked), 3) if checked else 1.0}


def write_outputs(drill: "Drill") -> "DrillResult":
    from alerte.sim.engine import DrillResult
    sc, lang = drill.scenario, drill.lang
    gaps = find_gaps(sc, drill.mm, drill.store, drill.decisions, drill.messages, lang)
    scores = score(sc, drill.mm, gaps)
    coverage = expected_gap_coverage(sc, gaps)
    cstats = citation_stats(drill)
    for g in gaps:
        drill.ledger.append("GAP", "ANALYSIS", g.model_dump(mode="json"))
    assumptions = [ln.model_dump() for ln in drill.mm.for_country(sc.country) if ln.evidence != "documented"]
    summary_docs = sorted({d.doc_id for d in drill.store.documents.values()
                           if d.country == sc.country and d.reliability.value == "summary"})
    llm_failures = getattr(drill.brain, "failures", 0)
    summary = {
        "scenario": sc.id, "title": sc.title, "country": sc.country, "language": lang, "brain": drill.model_info,
        "events": len(sc.events), "decisions": len(drill.decisions), "messages": len(drill.messages),
        "gaps": len(gaps), "gaps_by_type": {t: sum(1 for g in gaps if g.type == t) for t in GAP_TYPES if any(g.type == t for g in gaps)},
        "confirmed_gaps": sum(1 for g in gaps if g.status == "confirmed"),
        "expected_gap_coverage": coverage, "citations": cstats,
        "no_legal_basis_decisions": sum(1 for d in drill.decisions if d.no_legal_basis),
        "llm_failures_fallback_used": llm_failures,
        "decisions_by_author": {a: sum(1 for d in drill.decisions if d.author == a) for a in sorted({d.author for d in drill.decisions})},
        "ai_calls": getattr(drill.brain, "calls", 0),
        "discussion_messages": sum(1 for m in drill.messages if m.round == 3 and m.type.value in ("OBJECTION", "INFO")),
        "seconds": round(time.time() - drill.started, 2),
        "scorecard": {s.dimension_id: s.score for s in scores},
    }
    out = drill.run_dir
    (out / "scenario.json").write_text(sc.model_dump_json(indent=1), encoding="utf-8")
    for name, obj in (("decisions", drill.decisions), ("messages", drill.messages), ("gaps", gaps), ("scorecard", scores)):
        (out / f"{name}.json").write_text(json.dumps(as_dict(obj), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "assumptions.json").write_text(json.dumps({"mandate_lines": assumptions, "summary_documents": summary_docs},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    md = render_markdown(drill, gaps, scores, coverage, cstats, assumptions, summary_docs, summary)
    (out / "report.md").write_text(md, encoding="utf-8")
    (out / "report.html").write_text(markdown_to_html(md, f"ALERTE report: {sc.title}"), encoding="utf-8")
    drill.ledger.append("FINISH", "FACILITATOR", {k: v for k, v in summary.items() if k != "scorecard"})
    summary["ledger"] = verify_ledger(out / "ledger.jsonl")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    notify_run(summary, out)
    return DrillResult(drill.run_id, out, summary)


def _status(g) -> str:
    if g.status == "confirmed":
        return "confirmed by text"
    if g.status == "suspected":
        return "suspected (needs expert check)"
    return g.status + (f": {g.review_note}" if g.review_note else "")


def _cell(text: Any) -> str:
    return str(text).replace("|", "/").replace("\n", " ")


def render_markdown(drill, gaps, scores, coverage, cstats, assumptions, summary_docs, summary) -> str:
    sc, lang = drill.scenario, drill.lang
    fr = lang == "fr"
    names = GAP_TYPES_FR if fr else GAP_TYPES
    sev = SEV_FR if fr else SEV
    L = []
    L.append(f"# {'Rapport ALERTE' if fr else 'ALERTE report'}: {sc.title}\n")
    L.append(f"> **{sc.fictional_notice}**\n")
    brain = drill.model_info.get("model") or drill.model_info.get("brain")
    L.append(f"Run `{drill.run_id}` · country {sc.country} · brain: {brain} · {len(sc.events)} events · "
             f"{len(drill.decisions)} decisions · {len(gaps)} gaps ({summary['confirmed_gaps']} confirmed by text) · "
             f"{summary['seconds']} s\n")
    L.append("## Summary\n")
    L.append(f"- Gaps by type: " + ", ".join(f"{t} {names[t]} ({n})" for t, n in summary["gaps_by_type"].items()))
    L.append(f"- Planned gaps found (test T3): {coverage['found']} of {coverage['expected']} ({coverage['rate']:.0%})"
             + (f"; missed: {', '.join(coverage['missed'])}" if coverage["missed"] else ""))
    L.append(f"- Quotes verified (test T2): {cstats['verified']} of {cstats['citations']} ({cstats['rate']:.0%})")
    L.append(f"- Decisions with no legal basis found: {summary['no_legal_basis_decisions']}")
    by = summary["decisions_by_author"]
    L.append("- Who wrote the decisions: " + ", ".join(f"{ {'rules': 'rule engine (no AI)', 'ai': 'AI model', 'fallback': 'rule engine after an AI failure', 'scripted': 'scripted (HydroSense)', 'human': 'a human'}.get(k, k)} {v}" for k, v in by.items())
             + (f"; {summary['discussion_messages']} discussion messages between agents" if summary["discussion_messages"] else ""))
    if summary["llm_failures_fallback_used"]:
        L.append(f"- AI model calls that failed and used the offline rules instead: {summary['llm_failures_fallback_used']}")
    L.append("")
    L.append("## Gap report\n")
    for g in gaps:
        L.append(f"### {g.gap_id} · {g.title}\n")
        L.append(f"- **Type:** {g.type} {names[g.type]} · **Severity:** {sev.get(g.severity, g.severity)} · "
                 f"**Status:** {_status(g)}")
        L.append(f"- **When:** event(s) {', '.join(map(str, g.event_ids))}, first at {g.first_sim_time}")
        L.append(f"- **What is missing:** {g.description}")
        L.append(f"- **Institutions concerned:** {', '.join(g.institutions) or '-'}")
        L.append(f"- **Texts checked:** {', '.join(g.texts_checked) or 'none found in the library'}")
        L.append(f"- **Evidence:** " + "; ".join(g.evidence[:6]))
        if g.precedents:
            L.append(f"- **{'Ailleurs dans le monde' if fr else 'How others handle it'}:**")
            for p in g.precedents:
                art = f", {p.article}" if p.article else ""
                link = f"[{p.instrument}{art}]({p.url})" if p.url else f"{p.instrument}{art}"
                fit = "Fit for Cameroon" if sc.country == "CM" else "Note (written for Cameroon)"
                L.append(f"    - *{p.jurisdiction}*: {link}. {p.what_it_does} *{fit}:* {p.fit_note}")
        else:
            L.append("- **How others handle it:** fewer than two good examples found in the library.")
        L.append("")
    L.append("## Decision timeline\n")
    L.append("| Story time | Seat | Decision | Legal basis | Quote check | Confidence | By |")
    L.append("| --- | --- | --- | --- | --- | --- | --- |")
    for d in drill.decisions:
        basis = "; ".join(f"{c.doc_id} {c.article}".strip() for c in d.legal_basis) or ("NO LEGAL BASIS FOUND" if d.no_legal_basis else "-")
        check = ", ".join("ok" if c.verified else "NOT VERIFIED" for c in d.legal_basis) or "-"
        L.append(f"| {d.sim_time} | {d.seat} | {_cell(d.decision)[:160]} | {_cell(basis)} | {check} | {d.confidence} | {d.author} |")
    L.append("")
    L.append("## Readiness scorecard (ITU AI Readiness Framework, 13 dimensions)\n")
    L.append("Scores describe what this drill revealed (5 = no gap found, 0 = many serious gaps); they are not an official rating.\n")
    L.append("| # | Dimension | Score | Evidence |")
    L.append("| --- | --- | --- | --- |")
    for s in scores:
        val = "not assessed" if s.score < 0 else f"{s.score:.1f} / 5"
        L.append(f"| {s.dimension_id} | {s.name} | {val} | {_cell('; '.join(s.evidence[:3]))} |")
    L.append("")
    L.append("## Assumptions and sources to confirm\n")
    L.append("Lines of the who-does-what map that are not directly documented:\n")
    for a in assumptions:
        who = f" (assumed by {a['assumed_by']})" if a.get("assumed_by") else ""
        L.append(f"- `{a['line_id']}` {a['institution']} {a['kind']} *{a['action']}*: {a['description']} [{a['evidence']}{who}]")
    if summary_docs:
        L.append(f"\nNational documents used as summaries (official text still to obtain or confirm): {', '.join(summary_docs)}")
    L.append("\n## Logbook\n")
    L.append("Every step of this drill is in `ledger.jsonl`, chained by SHA-256 fingerprints. "
             "Check it with `python -m alerte verify " + str(drill.run_dir.name) + "`.\n")
    L.append(f"\n*{sc.fictional_notice}*\n")
    return "\n".join(L)


def markdown_to_html(md: str, title: str) -> str:
    try:
        import markdown  # optional, nicer tables
        body = markdown.markdown(md, extensions=["tables"])
    except ImportError:
        body = "<pre>" + html.escape(md) + "</pre>"
    css = ("body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;"
           "line-height:1.5;color:#1d1d1f;background:#fff}table{border-collapse:collapse;width:100%;font-size:.9rem}"
           "td,th{border:1px solid #ddd;padding:.35rem .5rem;vertical-align:top}th{background:#f3f3f3}"
           "blockquote{border-left:4px solid #c0392b;margin:0;padding:.3rem 1rem;background:#fdf2f0}"
           "h3{margin-top:2rem}code{background:#f3f3f3;padding:0 .2rem}"
           "@media (prefers-color-scheme: dark){body{background:#151515;color:#eee}th{background:#262626}"
           "td,th{border-color:#444}blockquote{background:#2a1714}code{background:#262626}a{color:#8ab4f8}}")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{css}</style></head><body>{body}</body></html>")


def load_run(run_dir: Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    data: dict[str, Any] = {"run_dir": str(run_dir)}
    for name in ("summary", "gaps", "decisions", "messages", "scorecard", "scenario", "assumptions"):
        p = run_dir / f"{name}.json"
        if p.exists():
            data[name] = json.loads(p.read_text(encoding="utf-8"))
    return data
