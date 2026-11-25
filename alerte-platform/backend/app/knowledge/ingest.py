"""Pipeline d'ingestion : extraction → normalisation → structure → chunking → analyseur → FTS5 → rapport de qualité → embeddings."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, update

from ..core.jobs import JobContext
from .chunking import ChunkDraft, chunk_pages
from .extract import ExtractionError, OcrEngine, extract
from .indexes import chunk_fts_row, fts_insert
from .models import Chunk, ChunkEmbedding, Document, DocumentVersion, KBVersionItem, KnowledgeBase
from .runtime import KnowledgeRuntime
from .textproc import analyze, detect_language, normalize_text, scan_injection, strip_repeated_lines

log = logging.getLogger("alerte.knowledge.ingest")

MIN_USEFUL_CHARS = 500


def suggest_metadata(first_text: str) -> dict:
    """Propositions (jamais la licence) : titre, numéro et date de texte par expressions régulières."""
    lines = [ln.strip() for ln in first_text.split("\n") if ln.strip()]
    out: dict[str, Any] = {}
    if lines:
        out["title"] = lines[0][:200]
    m = re.search(r"\b(?:n°|no\.?|numéro|number)\s*([0-9]{1,4}[/\-.]?[0-9]{0,4}[A-Za-z\-/]*)", first_text[:3000], re.I)
    if m:
        out["doc_number"] = m.group(1)
    m = re.search(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b", first_text[:3000])
    if m:
        out["doc_date"] = m.group(0)
    head = first_text[:300].lower()
    best: tuple[int, str] | None = None
    for kind, words in (("law", ("loi", "law", "act", "قانون")), ("decree", ("décret", "decret", "decree", "مرسوم")),
                        ("order", ("arrêté", "arrete", "order", "قرار")), ("strategy", ("stratégie", "strategy")),
                        ("report", ("rapport", "report"))):
        for w in words:
            m = re.search(rf"(?<!\w){re.escape(w)}(?!\w)", head)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), kind)
    if best:
        out["doc_type"] = best[1]
    return out


def missing_articles(labels: list[str | None]) -> list[int]:
    """Numéros d'articles absents de la suite reconnue (ex. 52, 53 lus « §3 » par l'OCR). N'invente rien : signale seulement.
    Ne s'applique qu'aux textes à numérotation entière continue (au moins 10 articles reconnus)."""
    nums = set()
    for a in labels:
        m = re.search(r"(\d+)\s*$", (a or "").strip().rstrip(".-"))
        if m and 0 < int(m.group(1)) < 1000:
            nums.add(int(m.group(1)))
    if len(nums) < 10:
        return []
    span = max(nums) - min(nums) + 1
    gaps = [n for n in range(min(nums), max(nums) + 1) if n not in nums]
    # une suite très lacunaire n'est pas un défaut d'OCR : loi modificative (articles qui renvoient à d'autres textes), considérants numérotés…
    return gaps if len(gaps) <= 25 and len(gaps) / span <= 0.2 else []


def _page_quality(method: str, chars: int, conf: float | None) -> float:
    base = min(1.0, chars / 400)
    if method == "ocr":
        return base * ((conf or 0) / 100)
    return base if method == "text" else 0.0


def ingest_version(rt: KnowledgeRuntime, job: JobContext | None, version_id: str, *, embed: bool = True) -> dict:
    """Corps du job `kb_ingest`. Reprise : les chunks déjà présents d'une version non publiée sont recréés proprement."""
    def prog(p: float, msg: str) -> None:
        if job:
            job.update(p, msg)

    with rt.factory() as s:
        v = s.get(DocumentVersion, version_id)
        doc = s.get(Document, v.document_id)
        kb = s.get(KnowledgeBase, v.kb_id)
        meta = dict(sha=v.blob_sha256, name=v.original_name or "", kb_id=kb.id, ws=v.workspace_id, doc_id=doc.id,
                    title=doc.title, evidence=doc.evidence_default, params=kb.chunking_params, doc_lang=doc.language)

    prog(0.05, "extraction du texte")
    try:
        ocr = OcrEngine(rt.settings.ocr_langs, rt.settings.tessdata_dir) if Path(meta["name"]).suffix.lower() == ".pdf" else None
        ex = extract(rt.blobs.path_for(meta["sha"]), Path(meta["name"]).suffix, ocr)
    except Exception as exc:  # noqa: BLE001 - échec explicite, jamais silencieux
        msg = str(exc)[:400]
        with rt.factory() as s:
            s.execute(update(DocumentVersion).where(DocumentVersion.id == version_id).values(
                status="failed", quality_report={"error": msg,
                                                 "code": getattr(exc, "code", "kb.document.unreadable")}))
            s.commit()
        if isinstance(exc, ExtractionError):
            raise
        raise ExtractionError(msg) from exc

    prog(0.35, "normalisation et détection de structure")
    stats: Counter = Counter()
    texts = [normalize_text(p.text, stats) for p in ex.pages]
    if ex.paged:
        texts = strip_repeated_lines(texts, stats)
    flags: list[dict] = []
    for p, t in zip(ex.pages, texts, strict=True):
        flags.extend(scan_injection(t, p.number))
    if ex.method == "csv":
        rows = [normalize_text(r) for r in ex.rows]
        drafts, off = [], 0
        for r in rows:
            drafts.append(ChunkDraft(r, None, None, off, off + len(r)))
            off += len(r) + 1
    else:
        drafts = chunk_pages([(p.number, t) for p, t in zip(ex.pages, texts, strict=True)], meta["params"])
    full_text = "\n".join(texts)
    doc_lang = meta["doc_lang"] or detect_language(full_text)

    pages_review = [p.number for p in ex.pages if p.review_reason and p.number is not None]
    review_reasons = {str(p.number): p.review_reason for p in ex.pages if p.review_reason}
    chars_total = sum(len(t.strip()) for t in texts)
    n_pages = len(ex.pages) if ex.paged else 1
    qualities = [_page_quality(p.method, len(t.strip()), p.ocr_confidence) for p, t in zip(ex.pages, texts, strict=True)] \
        if ex.paged else [1.0 if chars_total else 0.0]
    quality = sum(qualities) / len(qualities) if qualities else 0.0
    articles = sum(1 for d in drafts if d.article)
    warnings = list(ex.warnings)
    gaps = missing_articles([d.article for d in drafts])
    covered = sum(len(d.text) for d in drafts)
    lost_text = ex.method != "csv" and chars_total >= MIN_USEFUL_CHARS and covered < 0.95 * chars_total
    if lost_text:
        warnings.append(f"texte non couvert par les chunks : {chars_total - covered} caractère(s) sur {chars_total} "
                        f"({100 * (chars_total - covered) / chars_total:.1f} %) : relire le document")
    if gaps:
        warnings.append(f"suite des articles interrompue : {len(gaps)} numéro(s) absent(s) ou non reconnu(s) "
                        f"({', '.join(map(str, gaps[:15]))}{'…' if len(gaps) > 15 else ''}) : relire les pages concernées")
    if chars_total < MIN_USEFUL_CHARS:
        warnings.append(f"moins de {MIN_USEFUL_CHARS} caractères utiles ({chars_total}) : scan vide ou mauvais fichier ?")
    if flags:
        warnings.append(f"{len(flags)} motif(s) d'instruction suspecte signalé(s) (texte non modifié)")
    pages_blob = rt.blobs.put_bytes(json.dumps(
        [{"page": p.number, "text": t, "method": p.method, "review": p.review_reason}
         for p, t in zip(ex.pages, texts, strict=True)], ensure_ascii=False).encode("utf-8"))
    report = {
        "pages": n_pages, "chars_total": chars_total, "chars_per_page": round(chars_total / max(1, n_pages), 1),
        "ocr_pages": sum(1 for p in ex.pages if p.method == "ocr"),
        "ocr_pct": round(100 * sum(1 for p in ex.pages if p.method == "ocr") / max(1, n_pages), 1),
        "articles_detected": articles, "missing_articles": gaps, "chunks": len(drafts), "language": doc_lang,
        "pages_to_review": pages_review, "review_reasons": review_reasons, "injection_flags": flags,
        "normalization": dict(stats), "warnings": warnings, "extraction_method": ex.method,
        "suggested_metadata": suggest_metadata(full_text),
        "ocr": ({"requested": ocr.requested, "available": ocr.available, "missing": ocr.missing, "error": ocr.error}
                if ocr else None),
    }

    prog(0.55, "indexation lexicale")
    with rt.factory() as s:
        in_published = s.scalar(select(KBVersionItem.document_version_id).where(
            KBVersionItem.document_version_id == version_id))
        if in_published:
            raise RuntimeError("version publiée : immuable, impossible de la ré-ingérer")
        old = s.scalars(select(Chunk.id).where(Chunk.document_version_id == version_id)).all()
        if old:  # reprise d'une ingestion interrompue : table rase (version non publiée)
            from sqlalchemy import text as sql_text
            for i in range(0, len(old), 500):
                ids = old[i:i + 500]
                s.execute(delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(ids)))
                from sqlalchemy import bindparam
                s.execute(sql_text("DELETE FROM chunk_fts WHERE chunk_id IN :ids").bindparams(
                    bindparam("ids", expanding=True)), {"ids": ids})
                s.execute(delete(Chunk).where(Chunk.id.in_(ids)))
        rows = []
        for i, d in enumerate(drafts):
            lang = detect_language(d.text) if len(d.text) > 120 else doc_lang
            lang = doc_lang if lang == "und" else lang
            c = Chunk(workspace_id=meta["ws"], kb_id=meta["kb_id"], document_version_id=version_id, ordinal=i,
                      page_start=d.page_start if ex.paged else None, page_end=d.page_end if ex.paged else None,
                      article=d.article, section=d.section, language=lang, text=d.text, search_text=analyze(d.text),
                      text_sha256=hashlib.sha256(d.text.encode("utf-8")).hexdigest(), char_start=d.char_start,
                      char_end=d.char_end, doc_title=meta["title"], evidence_tag=meta["evidence"])
            s.add(c)
            rows.append(c)
        s.flush()
        fts_insert(s, [chunk_fts_row(c) for c in rows])
        status = "needs_review" if (pages_review or gaps or lost_text or quality < 0.5 or chars_total < MIN_USEFUL_CHARS) else "ready"
        s.execute(update(DocumentVersion).where(DocumentVersion.id == version_id).values(
            status=status, extraction_method=ex.method, extraction_quality=round(quality, 3),
            pages_to_review=pages_review, quality_report=report, text_blob_sha256=pages_blob))
        d_obj = s.get(Document, meta["doc_id"])
        if not d_obj.language and doc_lang != "und":
            d_obj.language = doc_lang
        d_obj.current_version_id = version_id
        s.commit()

    result: dict[str, Any] = {"version_id": version_id, "document_id": meta["doc_id"], "status": status,
                              "chunks": len(drafts), "pages_to_review": pages_review, "warnings": warnings}
    if embed and not _embedder_unavailable(rt):
        prog(0.7, "embeddings")
        try:
            from .kbops import embed_kb
            result["embedding"] = embed_kb(rt, job, meta["kb_id"], version_ids=[version_id], _span=(0.7, 1.0))
        except Exception as exc:  # noqa: BLE001 - la version reste utilisable en lexical ; l'échec est consigné
            result["embedding_error"] = str(exc)[:300]
            with rt.factory() as s:
                rep = dict(s.get(DocumentVersion, version_id).quality_report or {})
                rep.setdefault("warnings", []).append(f"embeddings non calculés : {str(exc)[:200]}")
                s.execute(update(DocumentVersion).where(DocumentVersion.id == version_id).values(quality_report=rep))
                s.commit()
    elif embed:
        result["embedding_error"] = "serveur d'embeddings non configuré (recherche lexicale seule)"
    return result


def _embedder_unavailable(rt: KnowledgeRuntime) -> bool:
    from .embedders import UnavailableEmbedder
    return rt.embedder is None or isinstance(rt.embedder, UnavailableEmbedder)
