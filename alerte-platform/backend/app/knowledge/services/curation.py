"""Application d'un registre de curation (métadonnées validées par des humains) aux documents déjà enregistrés d'UNE base.

Le lien entre une ligne du registre et un PDF est EXPLICITE : le registre cite le fichier d'origine (`original_path`) et le manifeste
de migration associe ce fichier à son SHA-256 ; c'est le SHA-256 qui désigne le document. Aucune métadonnée n'est déduite du nom
du fichier : seules celles écrites dans le registre sont appliquées, le reste reste « inconnu »."""
from __future__ import annotations

import datetime as dt
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Document, DocumentVersion, KnowledgeBase
from . import pipeline as PL

FIELDS = ("title", "doc_type", "doc_number", "language", "reliability", "validity", "redistribution", "license_spdx", "source_url")


def apply_curation(session: Session, kb: KnowledgeBase, rows: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> list[dict]:
    scope = PL.kb_scope(kb)
    sha_by_name = {m["migration_filename"]: m["sha256"] for m in manifest
                   if m.get("scope") == scope and m.get("sha256") and m.get("decision") in ("copied", "renamed_collision", "duplicate_skipped")}
    out: list[dict] = []
    for r in rows:
        if r.get("collection") != kb.code:
            continue
        name = PurePosixPath(str(r.get("original_path", ""))).name
        sha = sha_by_name.get(name)
        item = {"code": r["code"], "sha256": sha, "result": "applied"}
        if not sha:
            out.append(item | {"result": "not_in_manifest"})
            continue
        ver = session.scalar(select(DocumentVersion).where(DocumentVersion.kb_id == kb.id, DocumentVersion.blob_sha256 == sha)
                             .order_by(DocumentVersion.version_no.desc()).limit(1))
        if ver is None:
            out.append(item | {"result": "not_registered"})
            continue
        doc = session.get(Document, ver.document_id)
        other = session.scalar(select(Document.id).where(Document.kb_id == kb.id, Document.code == r["code"], Document.id != doc.id))
        if other:
            out.append(item | {"result": "code_taken"})
            continue
        doc.code = r["code"]
        for f in FIELDS:
            if r.get(f):
                setattr(doc, f, r[f])
        d = r.get("doc_date")
        if d and len(d) == 10:
            doc.doc_date = dt.date.fromisoformat(d)
        if kb.scope_kind == "country" and not doc.jurisdiction:
            doc.jurisdiction = kb.code  # le périmètre choisi par l'opérateur, jamais le nom du fichier
        out.append(item)
    return out
