"""ALERTE command line.  Run `python -m alerte --help`.

  python -m alerte doctor                  check your setup
  python -m alerte ingest                  build the knowledge index
  python -m alerte run cm01                run the Cameroon drill (offline brain)
  python -m alerte run cm01 --brain llm    run it with an AI model (Ollama, vLLM, sandbox...)
  python -m alerte ui                      open the web interface
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

from alerte import __version__, config


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _resolve_run(ref: str) -> Path:
    p = Path(ref)
    if p.is_dir():
        return p
    cand = config.settings.runs_dir / ref
    if cand.is_dir():
        return cand
    matches = sorted(config.settings.runs_dir.glob(f"{ref}*"))
    if matches:
        return matches[-1]
    sys.exit(f"Run '{ref}' not found in {config.settings.runs_dir}")


# ---------------------------------------------------------------------------- commands
def cmd_doctor(args) -> int:
    s = config.settings
    print(f"ALERTE {__version__} on {platform.system()} {platform.release()}, Python {platform.python_version()}")
    ok = sys.version_info >= (3, 10)
    print(f"[{'ok' if ok else 'FAIL'}] Python >= 3.10")
    for mod, why in (("pydantic", "core"), ("yaml", "core"), ("numpy", "core"), ("pymupdf", "PDF reading"),
                     ("streamlit", "web interface"), ("markdown", "HTML reports"), ("chromadb", "export to ITU ChromaDB (optional)"),
                     ("fastembed", "CPU embeddings (optional)"), ("docx", "Word documents"),
                     ("pptx", "PowerPoint files"), ("openpyxl", "Excel files"), ("cv2", "OCR image clean-up"),
                     ("pytesseract", "OCR (Tesseract wrapper)"), ("rapidfuzz", "OCR quality checks")):
        try:
            __import__(mod)
            print(f"[ok] {mod:10s} {why}")
        except ImportError:
            print(f"[--] {mod:10s} {why}: not installed")
    from alerte.knowledge.extract import ocr as _ocr
    st = _ocr.status()
    print(f"[{'ok' if st.tesseract else '!!'}] OCR: {st.describe()}")
    if not st.tesseract:
        from alerte.knowledge.extract.tools import install_hint
        print(f"     scanned documents need Tesseract: {install_hint()}   then: python -m alerte ocr-setup")
    elif {"fra", "eng", "ara"} - set(st.langs):
        print(f"     missing OCR languages: {', '.join(sorted({'fra', 'eng', 'ara'} - set(st.langs)))}  (run: python -m alerte ocr-setup)")
    print(f"[..] data folder:  {s.data_dir}")
    print(f"[..] index folder: {s.index_dir} ({'built' if (s.index_dir / 'chunks.jsonl').exists() else 'not built yet: run ingest'})")
    print(f"[..] ITU reference repo: {s.itu_root or 'not found (place ALERTE inside your fork of ITUAIReadiness, or set ALERTE_ITU_ROOT)'}")
    print(f"[..] brain: {s.brain}  (set ALERTE_BRAIN=llm to use an AI model)")
    if s.brain == "llm" or args.check_llm:
        from alerte.sim.llm_client import LLMClient
        good, msg = LLMClient().health()
        print(f"[{'ok' if good else 'FAIL'}] AI model at {s.llm_base_url} ({s.llm_model}): {msg}")
    print(f"[..] embeddings: {s.embed_provider}" + ("" if s.embed_provider == "none" else f" / {s.embed_model}"))
    print(f"[..] Slack notifications: {'on' if s.slack_webhook_url else 'off'}")
    return 0 if ok else 1


def cmd_ingest(args) -> int:
    from alerte.knowledge.ingest import build_index
    import os
    include_itu = None if args.itu == "auto" else args.itu == "yes"
    if args.thorough:
        os.environ["ALERTE_OCR_THOROUGH"] = "1"
    if args.no_cache:
        os.environ["ALERTE_NO_OCR_CACHE"] = "1"
    rep = build_index(include_itu=include_itu, embed_provider=args.embed, max_itu_docs=args.max_itu_docs,
                      progress=None if args.quiet else (lambda m: print(m, flush=True)))
    print()
    print(rep.summary())
    if rep.auto:
        print(f"Found in the folders but not in manifest.csv ({len(rep.auto)}), indexed anyway: " + ", ".join(rep.auto))
    if rep.missing:
        print("Listed but not obtained yet (run `python -m alerte fetch`, or add the files by hand):")
        print("  " + ", ".join(rep.missing))
    if rep.failed:
        print("NO TEXT COULD BE EXTRACTED from:")
        for k, v in rep.failed.items():
            print(f"  {k}: {v}")
    if rep.duplicates:
        print("Identical files (indexed once): " + ", ".join(f"{k} = {v}" for k, v in rep.duplicates.items()))
    if rep.review:
        print("Pages to proofread (OCR was not certain). Run `python -m alerte review <doc_id>` for each:")
        for k, v in rep.review.items():
            print(f"  {k}: pages {v}")
    print(f"Reports: {config.settings.index_dir / 'extraction_report.json'} and review_queue.md")
    return 1 if (args.strict and rep.failed) else 0


def cmd_extract(args) -> int:
    import json as _json
    from alerte.knowledge.extract import extract_file
    res = extract_file(args.file, args.lang, use_cache=False, thorough=args.thorough)
    if args.json:
        print(_json.dumps(res.report_row(), ensure_ascii=False, indent=1))
        return 1 if res.failed else 0
    print(f"{res.path}: {res.label()}" + (f"  FAILED: {res.failed}" if res.failed else ""))
    for p in res.pages:
        conf = "exact" if p.confidence is None else f"OCR {p.confidence}%"
        print(f"  page {p.page:3d}  {p.method:34s} {conf:10s} {p.chars:6d} chars  tables={p.tables}" + (f"  FLAGS: {'; '.join(p.flags)}" if p.flags else ""))
    if not args.no_text:
        print("\n" + res.text)
    return 1 if res.failed else 0


def cmd_ocr_setup(args) -> int:
    from alerte.knowledge.extract.tools import setup_ocr
    return setup_ocr(args.langs, "fast" if args.fast else "best")


def cmd_ocr_eval(args) -> int:
    from alerte.knowledge.extract.tools import run_eval
    return run_eval(args.thorough, Path(args.keep) if args.keep else None)


def cmd_review(args) -> int:
    from alerte.knowledge.extract.tools import review_pack
    return review_pack(args.target)


def cmd_fetch(args) -> int:
    from alerte.knowledge.fetch import fetch_all
    for doc_id, status in fetch_all(only=args.only, dry_run=args.dry_run):
        print(f"{doc_id:8s} {status}")
    print("Then run: python -m alerte ingest")
    return 0


def cmd_search(args) -> int:
    from alerte.knowledge.ingest import ensure_index
    from alerte.knowledge.store import get_store
    ensure_index()
    hits = get_store().search(args.query, args.k, countries=args.country or None)
    for h in hits:
        c = h.chunk
        print(f"{h.score:5.2f}  {c.doc_id} {c.article}  [{c.reliability}]  {c.title}")
        print(f"       {c.text[:220]}...")
    return 0


def cmd_scenarios(args) -> int:
    from alerte.sim.scenario import list_scenarios
    for s in list_scenarios():
        print(f"{s['id']:8s} {s['country']}  {s['events']:3d} events  {s['title']}" + (f"  (twin of {s['twin_of']})" if s["twin_of"] else ""))
    return 0


def cmd_run(args) -> int:
    from alerte.sim.engine import Drill
    drill = Drill(args.scenario, brain=args.brain, lang=args.lang)
    print(f"Run {drill.run_id}  ({drill.scenario.title}, brain: {drill.model_info})")
    print(drill.scenario.fictional_notice)
    if drill.brain_name == "offline":
        print("MODE: rule engine, no AI model. Words are assembled from the who-does-what table with fixed sentence templates; "
              "agents do not reason or discuss. Use --brain llm with a model to see agents think (docs/AGENTS.md).")

    def progress(res):
        flags = sum(1 for m in res.messages if m.type.value == "GAP_FLAG")
        print(f"  event {res.event_id:2d} {res.sim_time:10s} -> {', '.join(res.recipients):28s} "
              f"{len(res.decisions)} decisions, {flags} gap alerts ({res.seconds:.1f}s)")

    result = drill.run(progress=progress)
    s = result.summary
    print(f"\nDone in {s['seconds']} s: {s['gaps']} gaps ({s['confirmed_gaps']} confirmed by text), "
          f"planned gaps found {s['expected_gap_coverage']['found']}/{s['expected_gap_coverage']['expected']}, "
          f"quotes verified {s['citations']['verified']}/{s['citations']['citations']}")
    print("Who wrote the decisions: " + ", ".join(f"{k} {v}" for k, v in s["decisions_by_author"].items())
          + (f" · {s['ai_calls']} AI model calls, {s['discussion_messages']} discussion messages" if s["ai_calls"] else ""))
    print(f"Logbook: {s['ledger']['message']}")
    print(f"Report:  {result.run_dir / 'report.html'}")
    return 0


def cmd_verify(args) -> int:
    from alerte.sim.ledger import verify_ledger
    res = verify_ledger(_resolve_run(args.run) / "ledger.jsonl")
    print(("OK: " if res["ok"] else "BROKEN: ") + res["message"])
    return 0 if res["ok"] else 2


def cmd_ask(args) -> int:
    from alerte.sim.adviser import ask, format_answer
    lang = args.lang or config.settings.language
    print(format_answer(ask(args.question, country=args.country, lang=lang), lang))
    return 0


def cmd_compare(args) -> int:
    from alerte.analysis.compare import compare_markdown, compare_runs
    md = compare_markdown(compare_runs(_resolve_run(args.run_a), _resolve_run(args.run_b)))
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(md)
    return 0


def cmd_eval(args) -> int:
    from alerte.evaluation import eval_drills, eval_retrieval
    r = eval_retrieval()
    print(f"T1 retrieval: {r['score']:.0%} of {r['n']} questions ({'PASS' if r['passed'] else 'FAIL'}, target 80%)")
    for row in r["rows"]:
        if not row["found"]:
            print(f"   missed: {row['question']} (expected {row['expected']}, got {row['top']})")
    d = eval_drills(args.scenarios, brain=args.brain, repeats=args.repeats)
    _print(d)
    return 0


def cmd_export_chroma(args) -> int:
    from alerte.knowledge.chroma_export import export_to_chroma
    from alerte.knowledge.ingest import ensure_index
    from alerte.knowledge.store import get_store
    ensure_index()
    target = Path(args.chroma_dir) if args.chroma_dir else (
        (config.settings.itu_root / "simulation" / "data" / "chromadb") if config.settings.itu_root else Path("chromadb"))
    n = export_to_chroma(get_store(), target, args.collection, args.embed, args.embed_model, args.reset, args.include_itu)
    print(f"Exported {n} passages to {target} (collection '{args.collection}')")
    return 0


def cmd_export_sft(args) -> int:
    from alerte.sft import build_dataset
    runs = [_resolve_run(r) for r in args.runs]
    _print(build_dataset(Path(args.out), runs))
    print(f"Dataset written to {args.out}. Train on a GPU with: python sandbox/finetune_lora.py --data {args.out}")
    return 0


def cmd_ui(args) -> int:
    app = Path(__file__).resolve().parent / "ui" / "main.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(args.port),
           "--browser.gatherUsageStats", "false", "--client.toolbarMode", "minimal",
           "--theme.primaryColor", "#b3261e"]
    if args.headless:
        cmd += ["--server.headless", "true", "--server.address", args.address]
    print("Opening ALERTE at http://localhost:%d  (Ctrl+C to stop)" % args.port)
    return subprocess.call(cmd, env={**os.environ})


# ---------------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="alerte", description="ALERTE crisis drill simulator (ITU AI for Good Lab hackathon).")
    p.add_argument("--version", action="version", version=f"ALERTE {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="show detailed logs")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("doctor", help="check your setup")
    s.add_argument("--check-llm", action="store_true", help="also test the AI model connection")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("ingest", help="build the knowledge index from EVERY document in data/docs (OCR for scans)")
    s.add_argument("--itu", choices=["auto", "yes", "no"], default="auto", help="also index the ITU reference corpus")
    s.add_argument("--embed", default=None, help="embedding provider: none, ollama, openai, fastembed")
    s.add_argument("--max-itu-docs", type=int, default=None, help="limit ITU documents (quick tests)")
    s.add_argument("--strict", action="store_true", help="exit with an error if any file yielded no text")
    s.add_argument("--thorough", action="store_true", help="run every OCR pass on every page (slower, most careful)")
    s.add_argument("--no-cache", action="store_true", help="ignore cached OCR results and read everything again")
    s.add_argument("--quiet", action="store_true", help="do not print progress per file")
    s.set_defaults(func=cmd_ingest)

    s = sub.add_parser("extract", help="read one file with the full extraction pipeline and show a per-page quality report")
    s.add_argument("file")
    s.add_argument("--lang", default=None, help="document language hint: fr, en, ar")
    s.add_argument("--thorough", action="store_true")
    s.add_argument("--json", action="store_true")
    s.add_argument("--no-text", action="store_true", help="show only the per-page report")
    s.set_defaults(func=cmd_extract)

    s = sub.add_parser("ocr-setup", help="check Tesseract and download the French, English and Arabic OCR models")
    s.add_argument("--langs", nargs="*", default=["eng", "fra", "ara"])
    s.add_argument("--fast", action="store_true", help="smaller, faster, slightly less accurate models")
    s.set_defaults(func=cmd_ocr_setup)

    s = sub.add_parser("ocr-eval", help="measure extraction accuracy on generated test documents (scans, tables, mixed pages)")
    s.add_argument("--thorough", action="store_true")
    s.add_argument("--keep", default=None, help="keep the generated test documents in this folder")
    s.set_defaults(func=cmd_ocr_eval)

    s = sub.add_parser("review", help="prepare page images and an editable draft for a document whose OCR needs proofreading")
    s.add_argument("target", help="doc id (see review_queue.md) or part of the file name")
    s.set_defaults(func=cmd_review)

    s = sub.add_parser("fetch", help="download the official texts listed in the manifest")
    s.add_argument("--only", nargs="*", help="only these doc ids")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("search", help="search the library")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=5)
    s.add_argument("--country", nargs="*", help="e.g. CM AE EU")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("scenarios", help="list the crisis stories")
    s.set_defaults(func=cmd_scenarios)

    s = sub.add_parser("run", help="run a drill on autopilot")
    s.add_argument("scenario", help="scenario id, e.g. cm01 or ae01")
    s.add_argument("--brain", choices=["offline", "llm"], default=None)
    s.add_argument("--lang", choices=["en", "fr"], default=None)
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("verify", help="check that a drill logbook was not changed")
    s.add_argument("run", help="run folder or run id")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("ask", help="ask the legal adviser")
    s.add_argument("question")
    s.add_argument("--country", default="CM")
    s.add_argument("--lang", choices=["en", "fr"], default=None)
    s.set_defaults(func=cmd_ask)

    s = sub.add_parser("compare", help="compare two runs (twins, or before/after)")
    s.add_argument("run_a")
    s.add_argument("run_b")
    s.add_argument("--out", help="write Markdown to this file")
    s.set_defaults(func=cmd_compare)

    s = sub.add_parser("eval", help="measure the quality targets T1, T2, T3, T5, T6")
    s.add_argument("--scenarios", nargs="*", default=["cm01", "ae01"])
    s.add_argument("--brain", choices=["offline", "llm"], default="offline")
    s.add_argument("--repeats", type=int, default=1)
    s.set_defaults(func=cmd_eval)

    s = sub.add_parser("export-chroma", help="export the knowledge base to ChromaDB (ITU reference format)")
    s.add_argument("--chroma-dir", default=None)
    s.add_argument("--collection", default="alerte_kb")
    s.add_argument("--embed", default=None, help="compute vectors with: ollama, openai, fastembed")
    s.add_argument("--embed-model", default=None)
    s.add_argument("--reset", action="store_true")
    s.add_argument("--include-itu", action="store_true", help="also export the ITU reference documents")
    s.set_defaults(func=cmd_export_chroma)

    s = sub.add_parser("export-sft", help="build a fine-tuning dataset (JSONL)")
    s.add_argument("--out", default="sandbox/alerte_sft.jsonl")
    s.add_argument("--runs", nargs="*", default=[], help="finished runs to learn decisions from")
    s.set_defaults(func=cmd_export_sft)

    s = sub.add_parser("ui", help="open the web interface")
    s.add_argument("--port", type=int, default=8501)
    s.add_argument("--headless", action="store_true", help="do not open a browser (servers, sandbox)")
    s.add_argument("--address", default="0.0.0.0")
    s.set_defaults(func=cmd_ui)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    for stream in (sys.stdout, sys.stderr):  # Windows consoles: avoid UnicodeEncodeError on accents
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
    return int(args.func(args) or 0)
