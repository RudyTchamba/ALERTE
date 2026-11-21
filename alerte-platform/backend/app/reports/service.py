"""Cas d'usage du module reports : génération (assemblage depuis les services), versions immuables, rendus, rapports
importés, comparaisons. Toute requête filtre par `workspace_id` (autre espace -> 404)."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.canonical_json import canonical_sha256
from ..core.db import utcnow
from ..core.errors import Conflict, NotFound, Unprocessable
from ..evaluation import gaps_port
from ..evaluation.service import read_events
from . import assemble as asm
from .compare import compare_contents, compare_gap_lists
from .models import GapPriorLink, ImportedFinding, Report, ReportArtifact, ReportVersion
from .render import markdown as md
from .render import pdf as pdfr
from .render import tabular

FORMATS = {"md": ("text/markdown; charset=utf-8", "md"), "json": ("application/json", "json"),
           "csv": ("text/csv; charset=utf-8", "csv"),
           "pdf": ("application/pdf", "pdf"),
           "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx")}
RELATIONS = ("previously_identified", "newly_emerged", "contradicts")
UPLOAD_TYPES = {".pdf": "application/pdf", ".md": "text/markdown",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ORIGIN_PRIOR = "analyse antérieure"


# --------------------------------------------------------------------------- accès
def get_report(session: Session, workspace_id: str, report_id: str) -> Report:
    r = session.scalar(select(Report).where(Report.id == report_id, Report.workspace_id == workspace_id))
    if r is None:
        raise NotFound("rapport introuvable")
    return r


def get_version(session: Session, workspace_id: str, version_id: str) -> ReportVersion:
    v = session.scalar(select(ReportVersion).where(ReportVersion.id == version_id, ReportVersion.workspace_id == workspace_id))
    if v is None:
        raise NotFound("version de rapport introuvable")
    return v


def list_versions(session: Session, report_id: str) -> list[ReportVersion]:
    return list(session.scalars(select(ReportVersion).where(ReportVersion.report_id == report_id).order_by(ReportVersion.version_no)))


def create_report(session: Session, workspace_id: str, kind: str, title: str, exercise_id: str | None, confidentiality: str,
                  by: str | None) -> Report:
    if kind not in ("generated", "imported"):
        raise Unprocessable("kind doit valoir generated ou imported")
    r = Report(workspace_id=workspace_id, kind=kind, title=title, exercise_id=exercise_id, confidentiality=confidentiality,
               created_by=by)
    session.add(r)
    session.flush()
    return r


# --------------------------------------------------------------------------- génération
def _kb_block(ctx: Any, session: Session, workspace_id: str, snap: dict[str, Any]) -> dict[str, Any]:
    kn = ctx.services.get("knowledge")
    kbs = snap.get("kb", [])
    if kn is None or not kbs:
        return {"inventory": [{"code": k.get("code"), "name": k.get("name"), "documents": []} for k in kbs], "coverage": {}}
    inventory = []
    for k in kbs:
        docs = []
        for dv in (k.get("document_version_ids") or [])[:300]:
            meta = kn.document_meta(session, dv) or {}
            docs.append({"code": meta.get("code"), "title": meta.get("title"), "jurisdiction": meta.get("jurisdiction"),
                         "license": meta.get("license"), "redistribution": meta.get("redistribution")})
        inventory.append({"code": k.get("code"), "name": k.get("name"), "documents": docs})
    try:
        cov = kn.coverage(session, workspace_id, [k["kb_id"] for k in kbs])
    except Exception:  # noqa: BLE001 - couverture inconnue : jamais inventée
        cov = {}
    return {"inventory": inventory, "coverage": cov}


def prior_links_for(session: Session, workspace_id: str, exercise_id: str) -> list[dict[str, Any]]:
    rows = session.execute(select(GapPriorLink, ImportedFinding, Report).join(
        ImportedFinding, ImportedFinding.id == GapPriorLink.imported_finding_id).join(
        Report, Report.id == ImportedFinding.report_id).where(
        GapPriorLink.workspace_id == workspace_id, GapPriorLink.exercise_id == exercise_id).order_by(GapPriorLink.id)).all()
    return [{"origin": ORIGIN_PRIOR, "relation": link.relation, "gap_id": link.gap_id, "finding_id": f.id,
             "finding_title": f.title, "source_page": f.source_page, "report_id": rep.id, "report_title": rep.title,
             "note": link.note} for link, f, rep in rows]


def collect_inputs(ctx: Any, session: Session, workspace_id: str, exercise_id: str, rp: dict[str, Any]) -> dict[str, Any]:
    ledger = ctx.services.get("ledger")
    if ledger is None:
        from ..audit.ledger import Ledger

        ledger = Ledger()
    verify = ledger.verify(session, exercise_id)
    events = read_events(session, exercise_id, ledger)
    snap = gaps_port.read_snapshot(ctx, session, exercise_id)
    snap_ev = next((e["payload"] for e in events if e["type"] == "SNAPSHOT"), {})
    ex = dict((snap or {}).get("exercise") or {})
    ex.setdefault("id", exercise_id)
    ex["ai_mode"] = snap_ev.get("ai_mode") or ex.get("ai_mode")
    ex["snapshot_sha256"] = snap_ev.get("snapshot_sha256")
    ex["commitment_sha256"] = snap_ev.get("commitment_sha256")
    gaps = gaps_port.read_gaps(ctx, session, workspace_id, exercise_id) if gaps_port.gaps_available(ctx) else None
    evaluation = ctx.services.get("evaluation")
    return {"report": rp, "exercise": ex, "snapshot": snap,
            "ledger": {"head_seq": verify.get("head_seq"), "head_hash": verify.get("head_hash"), "verify": verify,
                       "events": verify.get("checked")},
            "events": events, "gaps": gaps, "kb": _kb_block(ctx, session, workspace_id, snap or {}),
            "scorecard": evaluation.scorecard(session, workspace_id, exercise_id) if evaluation else None,
            "metrics": evaluation.metrics(session, workspace_id, exercise_id) if evaluation else None,
            "prior_links": prior_links_for(session, workspace_id, exercise_id)}


def generate_version(ctx: Any, session: Session, workspace_id: str, exercise_id: str, *, title: str | None = None,
                     report_id: str | None = None, confidentiality: str = "internal", by: str | None = None) -> ReportVersion:
    """Crée une NOUVELLE version brouillon (jamais de modification d'une version existante), liée à la précédente."""
    if report_id:
        report = get_report(session, workspace_id, report_id)
        if report.kind != "generated" or report.exercise_id not in (None, exercise_id):
            raise Conflict("ce rapport n'est pas un rapport généré pour cet exercice")
        report.exercise_id = exercise_id
    else:
        report = create_report(session, workspace_id, "generated", title or f"Rapport de lacunes — exercice {exercise_id}",
                               exercise_id, confidentiality, by)
    last = session.scalar(select(ReportVersion).where(ReportVersion.report_id == report.id).order_by(ReportVersion.version_no.desc()).limit(1))
    version_no = (last.version_no if last else 0) + 1
    now = utcnow().isoformat(timespec="seconds").replace("+00:00", "Z")
    rp = {"id": report.id, "title": report.title, "version_no": version_no, "generated_at": now,
          "confidentiality": report.confidentiality, "parent_version_no": last.version_no if last else None}
    content = asm.assemble(collect_inputs(ctx, session, workspace_id, exercise_id, rp))
    led = content["cover"]["ledger"]
    v = ReportVersion(workspace_id=workspace_id, report_id=report.id, version_no=version_no, status="draft", content=content,
                      content_sha256=canonical_sha256(content), ledger_head_seq=led.get("head_seq"),
                      ledger_head_hash=led.get("head_hash"), generator_version=asm.GENERATOR_VERSION,
                      parent_version_id=last.id if last else None, created_by=by)
    session.add(v)
    session.flush()
    return v


def update_draft(session: Session, workspace_id: str, version_id: str, content: dict[str, Any]) -> ReportVersion:
    v = get_version(session, workspace_id, version_id)
    if v.status == "published":
        raise Conflict("version publiée : immuable ; générez une nouvelle version", code="report.immutable")
    if content.get("schema") != asm.SCHEMA or not isinstance(content.get("cover"), dict):
        raise Unprocessable("contenu invalide (schéma alerte.report/1 requis)")
    v.content, v.content_sha256 = asm.jsonable(content), canonical_sha256(asm.jsonable(content))
    session.flush()
    return v


def publish(session: Session, workspace_id: str, version_id: str) -> ReportVersion:
    v = get_version(session, workspace_id, version_id)
    if v.status == "published":
        raise Conflict("version déjà publiée", code="report.immutable")
    v.status, v.published_at = "published", utcnow()
    session.flush()
    return v


# --------------------------------------------------------------------------- rendus
def _render(fmt: str, content: dict[str, Any], content_sha: str) -> tuple[bytes, str | None]:
    if fmt == "md":
        return md.render_markdown(content).encode("utf-8"), None
    if fmt == "json":
        return tabular.render_json(content), None
    if fmt == "csv":
        return tabular.render_csv(content), None
    if fmt == "xlsx":
        return tabular.render_xlsx(content), "openpyxl"
    r = pdfr.get_pdf_renderer()
    return pdfr.render_pdf(content, r, identifier=bytes.fromhex(content_sha[:32])), r.name


def render_artifact(ctx: Any, session: Session, v: ReportVersion, fmt: str) -> tuple[bytes, str, str, ReportArtifact]:
    """Rendu dérivé du JSON ; mis en cache par (version, format, hash du contenu). SHA-256 et taille enregistrés."""
    if fmt not in FORMATS:
        raise NotFound(f"format inconnu : {fmt}")
    media, ext = FORMATS[fmt]
    art = session.scalar(select(ReportArtifact).where(ReportArtifact.report_version_id == v.id, ReportArtifact.format == fmt))
    if art is not None and art.content_sha256 == v.content_sha256 and ctx.blobs.exists(art.blob_sha256):
        return ctx.blobs.read_bytes(art.blob_sha256), media, f"report-v{v.version_no}.{ext}", art
    data, renderer = _render(fmt, v.content, v.content_sha256)
    sha = ctx.blobs.put_bytes(data)
    if art is None:
        art = ReportArtifact(workspace_id=v.workspace_id, report_version_id=v.id, format=fmt, content_sha256=v.content_sha256,
                             blob_sha256=sha, bytes=len(data), renderer=renderer)
        session.add(art)
    else:  # brouillon dont le contenu a changé : artefact recalculé
        art.content_sha256, art.blob_sha256, art.bytes, art.renderer, art.created_at = v.content_sha256, sha, len(data), renderer, utcnow()
    session.flush()
    return data, media, f"report-v{v.version_no}.{ext}", art


def list_artifacts(session: Session, version_id: str) -> list[ReportArtifact]:
    return list(session.scalars(select(ReportArtifact).where(ReportArtifact.report_version_id == version_id).order_by(ReportArtifact.format)))


# --------------------------------------------------------------------------- comparaison
def resolve_version(session: Session, workspace_id: str, report_id: str, ref: str) -> ReportVersion:
    q = select(ReportVersion).where(ReportVersion.workspace_id == workspace_id, ReportVersion.report_id == report_id)
    v = session.scalar(q.where(ReportVersion.version_no == int(ref))) if ref.isdigit() and len(ref) < 6 else \
        session.scalar(q.where(ReportVersion.id == ref))
    if v is None:
        raise NotFound("version introuvable pour ce rapport")
    return v


def compare_versions(session: Session, workspace_id: str, report_id: str, a: str, b: str) -> dict[str, Any]:
    get_report(session, workspace_id, report_id)
    va, vb = resolve_version(session, workspace_id, report_id, a), resolve_version(session, workspace_id, report_id, b)
    return {"report_id": report_id, "a": {"id": va.id, "version_no": va.version_no, "content_sha256": va.content_sha256},
            "b": {"id": vb.id, "version_no": vb.version_no, "content_sha256": vb.content_sha256},
            "diff": compare_contents(va.content, vb.content)}


def compare_exercises(ctx: Any, session: Session, workspace_id: str, ex_a: str, ex_b: str) -> dict[str, Any]:
    if not gaps_port.gaps_available(ctx):
        raise Conflict("service des lacunes indisponible", code="gaps.unavailable")
    ga, gb = (gaps_port.read_gaps(ctx, session, workspace_id, e) for e in (ex_a, ex_b))
    return {"a": ex_a, "b": ex_b, "basis": "fingerprint", **compare_gap_lists(ga, gb)}


# --------------------------------------------------------------------------- rapports importés
def import_report(ctx: Any, session: Session, workspace_id: str, *, title: str, filename: str, data: bytes,
                  exercise_id: str | None, confidentiality: str, original_date: str | None, source_note: str | None,
                  by: str | None) -> Report:
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in UPLOAD_TYPES:
        raise Unprocessable("format non pris en charge (PDF, MD ou DOCX)", details={"allowed": sorted(UPLOAD_TYPES)})
    if not data:
        raise Unprocessable("fichier vide")
    if (ext == ".pdf" and not data.startswith(b"%PDF")) or (ext == ".docx" and not data.startswith(b"PK")):
        raise Unprocessable("le contenu du fichier ne correspond pas à son extension")
    if ext == ".md":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Unprocessable("le fichier Markdown doit être en UTF-8") from exc
    sha = ctx.blobs.put_bytes(data)
    safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1][:300]
    r = Report(workspace_id=workspace_id, kind="imported", title=title, exercise_id=exercise_id, confidentiality=confidentiality,
               document_sha256=sha, document_filename=safe_name, document_media_type=UPLOAD_TYPES[ext],
               document_bytes=len(data), created_by=by,
               provenance={"origin": ORIGIN_PRIOR, "sha256": sha, "uploaded_by": by,
                           "uploaded_at": utcnow().isoformat(), "original_date": original_date, "source_note": source_note})
    session.add(r)
    session.flush()
    return r


def add_findings(session: Session, workspace_id: str, report_id: str, rows: list[dict[str, Any]]) -> list[ImportedFinding]:
    r = get_report(session, workspace_id, report_id)
    if r.kind != "imported":
        raise Conflict("les constats saisis ne s'ajoutent qu'à un rapport importé")
    out = [ImportedFinding(workspace_id=workspace_id, report_id=r.id, title=x["title"], body=x.get("body") or "",
                           code_hint=x.get("code_hint"), severity_hint=x.get("severity_hint"), source_page=x.get("source_page"),
                           status=x.get("status") or "extracted") for x in rows]
    session.add_all(out)
    session.flush()
    return out


def list_findings(session: Session, workspace_id: str, report_id: str) -> list[ImportedFinding]:
    get_report(session, workspace_id, report_id)
    return list(session.scalars(select(ImportedFinding).where(ImportedFinding.report_id == report_id).order_by(ImportedFinding.id)))


def get_finding(session: Session, workspace_id: str, finding_id: str) -> ImportedFinding:
    f = session.scalar(select(ImportedFinding).where(ImportedFinding.id == finding_id, ImportedFinding.workspace_id == workspace_id))
    if f is None:
        raise NotFound("constat importé introuvable")
    return f


def link_prior(ctx: Any, session: Session, workspace_id: str, finding_id: str, gap_id: str, exercise_id: str, relation: str,
               note: str | None) -> GapPriorLink:
    if relation not in RELATIONS:
        raise Unprocessable("relation invalide", details={"allowed": list(RELATIONS)})
    f = get_finding(session, workspace_id, finding_id)
    gap = next((g for g in gaps_port.read_gaps(ctx, session, workspace_id, exercise_id) if g.get("id") == gap_id), None) \
        if gaps_port.gaps_available(ctx) else None
    if gap is None:
        raise NotFound("lacune introuvable dans cet exercice")
    if session.scalar(select(GapPriorLink.id).where(GapPriorLink.gap_id == gap_id, GapPriorLink.imported_finding_id == f.id)):
        raise Conflict("lien déjà enregistré")
    link = GapPriorLink(workspace_id=workspace_id, gap_id=gap_id, gap_fingerprint=gap.get("fingerprint"), exercise_id=exercise_id,
                        imported_finding_id=f.id, relation=relation, note=note)
    session.add(link)
    session.flush()
    return link


def list_links(session: Session, workspace_id: str, report_id: str) -> list[GapPriorLink]:
    get_report(session, workspace_id, report_id)
    return list(session.scalars(select(GapPriorLink).join(ImportedFinding, ImportedFinding.id == GapPriorLink.imported_finding_id)
                                .where(ImportedFinding.report_id == report_id).order_by(GapPriorLink.id)))


def report_summary(session: Session, r: Report) -> dict[str, Any]:
    n = session.scalar(select(func.count()).select_from(ReportVersion).where(ReportVersion.report_id == r.id)) or 0
    return {"id": r.id, "kind": r.kind, "title": r.title, "exercise_id": r.exercise_id, "confidentiality": r.confidentiality,
            "origin": ORIGIN_PRIOR if r.kind == "imported" else "généré par l'exercice", "versions": n,
            "document": ({"sha256": r.document_sha256, "filename": r.document_filename, "media_type": r.document_media_type,
                          "bytes": r.document_bytes, "provenance": r.provenance} if r.kind == "imported" else None),
            "created_at": r.created_at.isoformat() if r.created_at else None}
