"""Build the knowledge index from EVERY document found, not only the listed ones.

Sources, in order: the rows of data/manifest.csv; then every other file under data/docs/ (any subfolder, any supported format)
and under the folders in ALERTE_EXTRA_DOC_DIRS, which are registered automatically (AUTO-...); then the ITU reference corpus.
Each file is read by alerte.knowledge.extract (text layer, OCR for scans, tables, pictures with text). A file is either indexed or
reported with the reason it could not be: nothing is skipped silently. Identical files are indexed once.
"""

from __future__ import annotations

import csv
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from alerte import config
from alerte.knowledge.chunk import article_ref, chunk_document
from alerte.knowledge.embed import get_embedder
from alerte.knowledge.extract import SUPPORTED, discover_files, extract_file
from alerte.knowledge.extract.result import ExtractionResult
from alerte.textutil import normalize_ws
from alerte.knowledge.store import KnowledgeStore
from alerte.models import Chunk, DocumentMeta, Reliability
from alerte.textutil import slug

log = logging.getLogger(__name__)

# Filename -> ISO country, for the ITU reference corpus (same idea as the reference ingest.py)
_ITU_COUNTRY = [
    (r"ethiopia", "ET"), (r"saudi|sdaia|nsdai", "SA"), (r"egypt", "EG"), (r"kenya", "KE"), (r"zambia", "ZM"),
    (r"brazil|pbia|cgee", "BR"), (r"india|niti", "IN"), (r"singapore|nais", "SG"), (r"japan", "JP"),
    (r"china", "CN"), (r"\bus_|usa|united.states", "US"), (r"\buk_|united.kingdom", "GB"), (r"\beu_", "EU"),
    (r"african.union|africa_declaration|smart_africa|windhoek", "AU"), (r"rwanda", "RW"), (r"nigeria", "NG"),
    (r"korea", "KR"), (r"peru", "PE"), (r"estonia", "EE"), (r"spain", "ES"), (r"turkiye", "TR"),
    (r"france", "FR"), (r"asean", "ASEAN"), (r"g7|g20|gpai|governing ai|un_|unctad|wto|who|itu|y\.3172|ai_ready", "INT"),
]


def _itu_country(name: str) -> str:
    low = name.lower()
    for pat, code in _ITU_COUNTRY:
        if re.search(pat, low):
            return code
    return "INT"


@dataclass
class IngestReport:
    indexed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)      # listed in the manifest, no file obtained yet
    empty: list[str] = field(default_factory=list)        # file present but no text could be extracted
    failed: dict[str, str] = field(default_factory=dict)  # doc_id -> reason
    auto: list[str] = field(default_factory=list)         # files found in the folders but not in the manifest
    duplicates: dict[str, str] = field(default_factory=dict)
    review: dict[str, list[int]] = field(default_factory=dict)   # doc_id -> pages a human should proofread
    files_found: int = 0
    ocr_pages: int = 0
    tables: int = 0
    chunks: int = 0
    seconds: float = 0.0
    vectors: str = "none"
    extraction: list[dict] = field(default_factory=list)

    def summary(self) -> str:
        return (f"{len(self.indexed)} documents indexed ({len(self.auto)} found automatically), {self.chunks} passages, vectors: {self.vectors}, "
                f"{self.ocr_pages} pages read by OCR, {self.tables} tables, {len(self.missing)} listed but not obtained, "
                f"{len(self.empty)} unreadable, {len(self.review)} to proofread, {self.seconds:.1f}s")


def _split(v: str) -> list[str]:
    return [x.strip() for x in re.split(r"[;|]", v or "") if x.strip()]


def read_manifest(path: Path | None = None) -> list[DocumentMeta]:
    path = Path(path or config.settings.manifest_path)
    docs = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("doc_id") or "").strip() or row["doc_id"].startswith("#"):
                continue
            docs.append(DocumentMeta(
                doc_id=row["doc_id"].strip(), title=row["title"].strip(),
                country=(row.get("country") or "INT").strip(), doc_type=(row.get("doc_type") or "report").strip(),
                language=(row.get("language") or "en").strip(),
                reliability=Reliability((row.get("reliability") or "summary").strip()),
                url=(row.get("url") or "").strip(), file=(row.get("file") or "").strip(),
                collection=(row.get("collection") or "GL").strip(),
                institutions=_split(row.get("institutions", "")), topics=_split(row.get("topics", "")),
                status=(row.get("status") or "current").strip(), replaced_by=(row.get("replaced_by") or "").strip(),
                accessed=(row.get("accessed") or "").strip(), notes=(row.get("notes") or "").strip(),
            ))
    return docs


def _chunks_for(doc: DocumentMeta, text: str, ext: ExtractionResult | None = None) -> list[Chunk]:
    out = []
    label = ext.label() if ext is not None else ""
    review = bool(ext is not None and ext.needs_review)
    for n, (art, body) in enumerate(chunk_document(text)):
        out.append(Chunk(
            chunk_id=f"{slug(doc.doc_id, 30)}-{n:04d}", doc_id=doc.doc_id, title=doc.title, text=body,
            article=article_ref(art), country=doc.country, doc_type=doc.doc_type, language=doc.language,
            reliability=doc.reliability.value, collection=doc.collection, institutions=doc.institutions,
            topics=doc.topics, url=doc.url, status=doc.status, extraction=label, needs_review=review))
    return out


def detect_language(text: str, fallback: str = "en") -> str:
    from alerte.knowledge.extract.quality import arabic_ratio
    if arabic_ratio(text) > 0.3:
        return "ar"
    words = re.findall(r"[a-zà-ÿ]+", text.lower()[:20000])
    if not words:
        return fallback
    fr = sum(w in {"le", "la", "les", "des", "du", "de", "et", "est", "une", "dans", "pour", "par", "sur", "que", "qui", "aux", "au"} for w in words)
    en = sum(w in {"the", "of", "and", "to", "in", "is", "for", "that", "with", "shall", "by", "on", "as", "are", "or"} for w in words)
    return "fr" if fr > en * 1.2 else ("en" if en else fallback)


_FOLDER_COUNTRY = {"CM": "CM", "AE": "AE"}
_LANG_HINT = [(r"(^|[_\-. ])(fr|fra|french|francais|français)([_\-. ]|$)", "fr"), (r"(^|[_\-. ])(ar|ara|arabic|arabe)([_\-. ]|$)", "ar"),
              (r"(^|[_\-. ])(en|eng|english|anglais)([_\-. ]|$)", "en")]


def auto_meta(path: Path, root: Path | None, taken: set[str]) -> DocumentMeta:
    """Metadata for a file found in a folder but not listed in the manifest."""
    try:
        rel = path.resolve().relative_to(root.resolve()) if root else Path(path.name)
        parts = list(rel.parts)
    except ValueError:
        parts = [path.parent.name, path.name]
    top = parts[0].upper() if len(parts) > 1 else "EXTRA"
    low_parts = [p.lower() for p in parts[:-1]]
    country = _FOLDER_COUNTRY.get(top, "INT")
    base = "AUTO-" + slug(path.stem, 48)
    doc_id, n = base, 2
    while doc_id in taken:
        doc_id, n = f"{base}-{n}", n + 1
    taken.add(doc_id)
    official = "official" in low_parts
    return DocumentMeta(
        doc_id=doc_id, title=path.stem.replace("_", " ").strip(), country=country, doc_type="report", language="",
        reliability=Reliability.official if official else Reliability.summary, collection=top if top in ("CM", "AE", "GL", "ITU", "SCN") else "EXTRA",
        file=str(path), accessed=date.today().isoformat(),
        notes="Found automatically in the folders; add it to data/manifest.csv to set title, institutions and topics")


def itu_reference_documents(itu_docs: Path) -> list[tuple[DocumentMeta, Path]]:
    items = []
    for p in discover_files(itu_docs):
        if p.name.lower() == "inputs.md":
            continue
        doc_id = "ITUREF-" + slug(p.stem, 48)
        items.append((DocumentMeta(
            doc_id=doc_id, title=p.stem.replace("_", " "), country=_itu_country(p.name),
            doc_type="strategy" if p.parent.name == "AI_Strategies" else "standard",
            language="en",
            reliability=Reliability.summary if p.suffix.lower() in (".txt", ".md") else Reliability.official,
            collection="ITUREF",
            url="https://github.com/CrashingGuru/ITUAIReadiness", file=str(p),
            topics=[p.parent.name.lower()], accessed=date.today().isoformat(),
            notes="From the ITU reference repository seed corpus"), p))
    return items


def build_index(include_itu: bool | None = None, embed_provider: str | None = None,
                index_dir: Path | None = None, manifest: Path | None = None,
                max_itu_docs: int | None = None, progress=None) -> IngestReport:
    s = config.settings
    t0 = time.time()
    rep = IngestReport()
    docs_dir = s.docs_dir
    out_dir = Path(index_dir or s.index_dir)
    say = progress or (lambda msg: log.info(msg))
    from alerte.knowledge.extract import pdf as _pdf
    _pdf.PROGRESS = say
    all_docs: list[DocumentMeta] = []
    chunks: list[Chunk] = []
    seen_files: set[str] = set()        # resolved paths already handled
    seen_hash: dict[str, str] = {}      # sha256 -> doc_id

    def handle(doc: DocumentMeta, path: Path, language: str | None) -> None:
        rep.files_found += 1
        seen_files.add(str(path.resolve()))
        say(f"[{len(rep.indexed) + len(rep.empty) + 1}] reading {path.name} ...")
        ext = extract_file(path, language)
        row = ext.report_row()
        row["doc_id"] = doc.doc_id
        rep.extraction.append(row)
        if ext.failed or not ext.text.strip():
            reason = ext.failed or "no text found"
            rep.empty.append(doc.doc_id)
            rep.failed[doc.doc_id] = reason
            all_docs.append(doc)
            say(f"    FAILED: {reason}")
            return
        if ext.sha256 in seen_hash and not ext.corrected:
            rep.duplicates[doc.doc_id] = seen_hash[ext.sha256]
            all_docs.append(doc)
            say(f"    identical to {seen_hash[ext.sha256]}: indexed once")
            return
        seen_hash[ext.sha256] = doc.doc_id
        text = normalize_ws(ext.text)
        if not doc.language:
            doc = doc.model_copy(update={"language": detect_language(text, "en")})
        all_docs.append(doc)
        new = _chunks_for(doc, text, ext)
        chunks.extend(new)
        rep.indexed.append(doc.doc_id)
        rep.ocr_pages += ext.ocr_pages
        rep.tables += ext.tables
        if ext.review_pages:
            rep.review[doc.doc_id] = ext.review_pages
        say(f"    {len(new)} passages via {ext.label()}" + (f", proofread pages {ext.review_pages}" if ext.review_pages else "")
            + (" (cached)" if ext.cached else ""))

    # 1. documents listed in the manifest
    for doc in read_manifest(manifest):
        if not doc.file:
            all_docs.append(doc)
            rep.missing.append(doc.doc_id)
            continue
        path = docs_dir / doc.file
        if not path.exists():
            all_docs.append(doc)
            rep.missing.append(doc.doc_id)
            continue
        handle(doc, path, doc.language or None)

    # 2. every other file in the document folders, whatever its format or subfolder
    taken = {d.doc_id for d in all_docs}
    extra_roots = [(docs_dir, docs_dir)] + [(p, p) for p in s.extra_doc_dirs]
    for root, base in extra_roots:
        for path in discover_files(root):
            if str(path.resolve()) in seen_files or (itu_dir := s.itu_docs_dir) is not None and itu_dir in path.resolve().parents:
                continue
            doc = auto_meta(path, base, taken)
            rep.auto.append(doc.doc_id)
            handle(doc, path, None)

    # 3. the ITU reference corpus
    if include_itu is None:
        include_itu = s.itu_docs_dir is not None
    if include_itu and s.itu_docs_dir is not None:
        items = itu_reference_documents(s.itu_docs_dir)
        if max_itu_docs:
            items = items[:max_itu_docs]
        for doc, path in items:
            handle(doc, path, "en")

    vectors, info = None, None
    embedder = get_embedder(embed_provider)
    if embedder is not None and chunks:
        say(f"embedding {len(chunks)} passages with {embedder.name}/{embedder.model} ...")
        vectors = embedder.embed([f"{c.title}. {c.article}. {c.text}" for c in chunks])
        info = {"provider": embedder.name, "model": embedder.model}
        rep.vectors = f"{embedder.name}/{embedder.model}"
    rep.chunks = len(chunks)
    _pdf.PROGRESS = None
    KnowledgeStore.save(out_dir, chunks, all_docs, vectors, info)
    rep.seconds = time.time() - t0
    _write_reports(out_dir, rep)
    return rep


def _write_reports(out_dir: Path, rep: IngestReport) -> None:
    """index/extraction_report.json (everything) and index/review_queue.md (what a human should check)."""
    (out_dir / "extraction_report.json").write_text(json.dumps(
        {"summary": rep.summary(), "failed": rep.failed, "duplicates": rep.duplicates, "auto_registered": rep.auto,
         "review": rep.review, "documents": rep.extraction}, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Extraction review queue", "", rep.summary(), ""]
    if rep.failed:
        lines += ["## No text could be extracted", ""] + [f"- **{k}**: {v}" for k, v in rep.failed.items()] + [""]
    if rep.review:
        lines += ["## Pages to proofread", "",
                  "OCR is never perfect. For each document below, run `python -m alerte review <doc_id>` to get the page images and a draft, "
                  "correct the draft, and save it next to the source file as `<file name>.corrected.md`. The next `ingest` uses it.", ""]
        for doc_id, pages in rep.review.items():
            row = next((r for r in rep.extraction if r["doc_id"] == doc_id), {})
            lines.append(f"- **{doc_id}** ({row.get('file', '')}): pages {pages}")
        lines.append("")
    if not rep.failed and not rep.review:
        lines.append("Nothing to review: every page was read from an exact text layer or by OCR with high confidence and agreement.")
    (out_dir / "review_queue.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_index() -> None:
    """Build the index on first use so the app works right after cloning."""
    if not (config.settings.index_dir / "chunks.jsonl").exists():
        log.info("No index yet: building it (one-time, keyword search only) ...")
        build_index(embed_provider="none")
