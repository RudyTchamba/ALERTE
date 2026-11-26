"""CLI applicative d'ALERTE : `python -m app.cli ...` — appelle DIRECTEMENT les services backend (aucune requête HTTP, aucun serveur).

La CLI et l'API REST partagent les mêmes services (`app/knowledge/services/*`, `kbops`, `ingest`) et donc les mêmes règles :
isolation par périmètre, contrôles d'entrée, états de traitement, historique. Aucune logique métier n'est écrite ici.

Toute opération sur une base EXIGE un périmètre explicite (`--country CM` ou `--kb-id <ID>`) ; sans périmètre la commande refuse et
explique pourquoi : il n'existe aucune construction « globale ». Les données utilisées sont celles de `ALERTE_DATA_DIR`
(comme le serveur) : arrêtez le serveur ou utilisez un autre dossier pour une construction longue.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import select

from . import modules
from .core.blobs import BlobStore
from .core.config import Settings, get_settings
from .core.context import AppContext
from .core.db import make_engine, make_sessionmaker
from .core.errors import AppError
from .core.jobs import JobRunner
from .knowledge import kbops
from .knowledge.models import Document, DocumentVersion, KnowledgeBase
from .knowledge.services import build as BLD
from .knowledge.services import pipeline as PL
from .knowledge.services import sources as S
from .migrate import init_database

EXIT_REFUSED = 2


class ConsoleJob:
    """Remplace le `JobContext` d'un job : affiche la progression au lieu de l'écrire en base."""

    job_id = None

    def __init__(self, quiet: bool = False) -> None:
        self.quiet, self._last = quiet, None

    def update(self, progress: float | None = None, message: str | None = None) -> None:
        if self.quiet or message is None or message == self._last:
            return
        self._last = message
        pct = f"{int((progress or 0) * 100):3d}% " if progress is not None else "     "
        print(f"  … {pct}{message}", flush=True)


def make_ctx(settings: Settings | None = None) -> AppContext:
    """Même assemblage que `create_app`, sans serveur : base migrée, modules enregistrés, aucun thread de job utilisé."""
    settings = settings or get_settings()
    settings.ensure_dirs()
    engine = make_engine(settings.database_url)
    factory = make_sessionmaker(engine)
    ctx = AppContext(settings=settings, engine=engine, session_factory=factory, blobs=BlobStore(settings.blobs_dir),
                     jobs=JobRunner(factory, 1), recover_on_start=False)
    init_database(settings, engine)
    modules.run_setups(ctx)
    return ctx


@contextmanager
def session(ctx: AppContext) -> Iterator[Any]:
    s = ctx.session_factory()
    try:
        yield s
    finally:
        s.close()


def workspace_id(ctx: AppContext, wanted: str | None) -> str:
    from .workspaces.models import Workspace
    with session(ctx) as s:
        rows = list(s.scalars(select(Workspace)))
    if wanted:
        if not any(w.id == wanted for w in rows):
            raise S.SourceError(f"espace de travail introuvable : {wanted}", "cli.workspace_unknown")
        return wanted
    if len(rows) == 1:
        return rows[0].id
    if not rows:
        raise S.SourceError("aucun espace de travail : créez-en un (`workspace create --name …`)", "cli.no_workspace")
    raise S.SourceError("plusieurs espaces de travail : précisez --workspace <ID> (" + ", ".join(f"{w.id}={w.name}" for w in rows) + ")",
                        "cli.workspace_ambiguous")


def scope_args(p: argparse.ArgumentParser) -> None:
    g = p.add_argument_group("périmètre (obligatoire)")
    g.add_argument("--country", help="code du pays ou de la base (ex. CM, AE, GL, ITU) : doit désigner UNE base")
    g.add_argument("--kb-id", help="identifiant d'une base de connaissances")
    p.add_argument("--workspace", help="identifiant de l'espace de travail (si plusieurs)")


def _resolve(ctx: AppContext, a: argparse.Namespace) -> tuple[str, str]:
    ws = workspace_id(ctx, a.workspace)
    with session(ctx) as s:
        kb = BLD.resolve_scope(s, ws, country=a.country, kb_id=a.kb_id)
        return ws, kb.id


def _show(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


# --------------------------------------------------------------------------- commandes
def cmd_workspace_create(ctx: AppContext, a: argparse.Namespace) -> int:
    from .workspaces import service as ws_service
    with session(ctx) as s:
        ws, token = ws_service.create_workspace(s, a.name, None)
        s.commit()
        print(f"espace créé : {ws.id} ({ws.name})\njeton propriétaire (affiché une seule fois) : {token}")
    return 0


def cmd_kb_create(ctx: AppContext, a: argparse.Namespace) -> int:
    ws = workspace_id(ctx, a.workspace)
    rt = ctx.services["knowledge"]
    with session(ctx) as s:
        kb = kbops.create_kb(rt, s, ws, code=a.code, name=a.name, kind=a.kind, scope_kind=a.scope_kind, domain=a.domain,
                             languages=a.language or [], description=a.description)
        s.commit()
        print(f"base créée : {kb.id} code={kb.code} périmètre={kb.scope_kind} dossier=blobs/knowledge_sources/{PL.kb_scope(kb)}")
    return 0


def cmd_kb_list(ctx: AppContext, a: argparse.Namespace) -> int:
    ws = workspace_id(ctx, a.workspace)
    rt = ctx.services["knowledge"]
    with session(ctx) as s:
        for kb in s.scalars(select(KnowledgeBase).where(KnowledgeBase.workspace_id == ws).order_by(KnowledgeBase.code)):
            st = BLD.kb_status(rt, s, kb)
            print(f"{kb.code:8} {kb.id}  {st['scope_kind']:12} documents={st['documents']:3} prêts={st['documents_ready']:3} "
                  f"en attente={st['documents_waiting']:3} échecs={st['documents_failed']:2} chunks={st['chunks']:5} "
                  f"vecteurs={st['embeddings']['embedded']}/{st['chunks']}  {st['general_status']}")
    return 0


def cmd_sources_migrate(ctx: AppContext, a: argparse.Namespace) -> int:
    jobs = []
    for m in a.map:
        scope, _, folder = m.partition("=")
        if not folder:
            raise S.SourceError(f"--map attend PÉRIMÈTRE=DOSSIER (ex. CM=../alerte/data/docs/CM), reçu : {m!r}", "cli.bad_map")
        jobs.append((scope, Path(folder).expanduser(), a.source_kind, a.label or folder))
    rep = S.migrate(ctx.settings.sources_dir, jobs, dry_run=not a.apply)
    for it in rep.items:
        print(f"{it.decision:18} {it.scope:18} {it.migration_filename}  ->  {it.destination or it.duplicate_of}")
    print(f"{'SIMULATION (rien écrit) — ajoutez --apply pour copier' if rep.dry_run else 'copie effectuée'} : {rep.counts()}")
    if a.apply and a.manifest:
        S.write_manifest(Path(a.manifest), rep)
        print(f"provenance consignée dans {a.manifest}")
    return 0


def _manifest_index(path: str | None) -> dict[str, dict]:
    if not path:
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["sha256"]] = r
    return out


def cmd_sources_list(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    with session(ctx) as s:
        kb = s.get(KnowledgeBase, kb_id)
        files = kbops.list_unregistered(ctx.services["knowledge"], s, kb)
    for f in files:
        print(f"{f['path']}  ({f['bytes']} octets)")
    print(f"{len(files)} fichier(s) sans enregistrement documentaire dans le dossier de {PL.kb_scope(kb)}")
    return 0


def cmd_sources_verify(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    rt = ctx.services["knowledge"]
    with session(ctx) as s:
        rep = BLD.check_coherence(rt, s, s.get(KnowledgeBase, kb_id), verify_files=True)
    chk = next(c for c in rep["checks"] if c["id"] == "source_files_intact")
    print(("OK  " if chk["ok"] else "KO  ") + chk["detail"])
    return 0 if chk["ok"] else 1


def cmd_adopt(ctx: AppContext, a: argparse.Namespace) -> int:
    """Enregistre les fichiers déjà présents dans le dossier du périmètre (aucune copie) et lance leur traitement."""
    ws, kb_id = _resolve(ctx, a)
    rt = ctx.services["knowledge"]
    man = _manifest_index(a.manifest)
    meta = {k: v for k, v in (kv.split("=", 1) for kv in a.meta or [])}
    with session(ctx) as s:
        kb = s.get(KnowledgeBase, kb_id)
        todo = [f["path"] for f in kbops.list_unregistered(rt, s, kb)]
    if a.file:
        todo = [t for t in todo if t in a.file or Path(t).name in a.file]
    n_ok = n_err = 0
    for rel in todo:
        with session(ctx) as s:
            kb = s.get(KnowledgeBase, kb_id)
            try:
                sha = S.sha256_file(S.resolve(ctx.settings.sources_dir, rel))
                prov = {k: man[sha][k] for k in ("source_kind", "source_folder_label", "source_path", "migrated_at") if sha in man and man[sha].get(k)}
                dl = man[sha].get("download_name") if sha in man else None
                doc, ver = kbops.adopt_file(rt, s, kb, rel, dict(meta), provenance=prov, download_name=dl)
                s.commit()  # reste à l'état « uploaded » : la construction (ou `process`) le traitera
                print(f"enregistré  {rel}  -> document {doc.code} ({doc.id})")
                n_ok += 1
            except AppError as exc:
                s.rollback()
                print(f"REFUSÉ      {rel} : {exc.code} — {exc}")
                n_err += 1
    print(f"{n_ok} enregistré(s), {n_err} refusé(s) ; traitement : `process --{'country' if a.country else 'kb-id'} … ` ou `build`")
    return 0 if not n_err else 1


def cmd_curate(ctx: AppContext, a: argparse.Namespace) -> int:
    """Applique à UNE base les métadonnées d'un registre de curation ; le lien registre → PDF passe par le SHA-256 du manifeste."""
    from .knowledge.services import curation
    ws, kb_id = _resolve(ctx, a)
    rows = json.loads(Path(a.curation).read_text(encoding="utf-8"))
    manifest = [json.loads(x) for x in Path(a.manifest).read_text(encoding="utf-8").splitlines() if x.strip()]
    with session(ctx) as s:
        res = curation.apply_curation(s, s.get(KnowledgeBase, kb_id), rows, manifest)
        s.commit()
    counts: dict[str, int] = {}
    for r in res:
        counts[r["result"]] = counts.get(r["result"], 0) + 1
        if r["result"] != "applied":
            print(f"non appliqué : {r['code']} ({r['result']})")
    print(f"curation appliquée à la base : {counts}")
    return 0 if set(counts) <= {"applied"} else 1


def cmd_import(ctx: AppContext, a: argparse.Namespace) -> int:
    """Importe un ou plusieurs fichiers : chacun est un document INDÉPENDANT (échec isolé), rangé dans le dossier du périmètre."""
    ws, kb_id = _resolve(ctx, a)
    rt = ctx.services["knowledge"]
    meta = {k: v for k, v in (kv.split("=", 1) for kv in a.meta or [])}
    ids, bad = [], 0
    for f in a.files:
        path = Path(f).expanduser()
        try:
            with session(ctx) as s, path.open("rb") as fh:
                kb = s.get(KnowledgeBase, kb_id)
                sha, size, rel = kbops.store_original(rt, s, kb, fh, path.name)
                doc, ver = kbops.create_document(s, ws, kb, sha, size, path.name, dict(meta), storage_path=rel)
                s.commit()
                ids.append(ver.id)
                print(f"importé     {path.name}  -> {rel}  (document {doc.code}, {doc.id})")
        except (AppError, OSError) as exc:
            bad += 1
            print(f"REFUSÉ      {path.name} : {getattr(exc, 'code', 'io')} — {exc}")
    if not a.no_process:
        from .knowledge.ingest import ingest_version
        for vid in ids:
            r = ingest_version(rt, ConsoleJob(), vid, embed=False)
            print(f"traité      {vid}  état={r['status']} chunks={r['chunks']}")
    return 0 if not bad else 1


def cmd_status(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    rt = ctx.services["knowledge"]
    with session(ctx) as s:
        kb = s.get(KnowledgeBase, kb_id)
        _show(BLD.kb_status(rt, s, kb))
        if a.documents:
            names = {d.id: d.code for d in s.scalars(select(Document).where(Document.kb_id == kb_id))}
            for v in PL.latest_versions(s, kb_id):
                err = f"  ! {v.processing_error}" if v.processing_error else ""
                print(f"{names.get(v.document_id, '?'):12} {v.processing_state:14} v{v.version_no} {v.storage_path or '(ancien stockage)'}{err}")
    return 0


def cmd_process(ctx: AppContext, a: argparse.Namespace) -> int:
    """Traitement INDIVIDUEL d'un document (relance incluse), ou des seuls documents en attente d'UNE base."""
    from .knowledge.ingest import ingest_version
    rt = ctx.services["knowledge"]
    if a.document or a.version:
        ws = workspace_id(ctx, a.workspace)
        with session(ctx) as s:
            if a.version:
                vid = a.version
            else:
                d = s.get(Document, a.document)
                last = s.scalar(select(DocumentVersion).where(DocumentVersion.document_id == a.document)
                                .order_by(DocumentVersion.version_no.desc()).limit(1))
                if d is None or d.workspace_id != ws or last is None:
                    raise S.SourceError("document introuvable", "cli.document_unknown")
                vid = last.id  # dernière version, même si le document n'a jamais été traité
            PL.prepare_reprocess(s, ws, vid)
            s.commit()
        r = ingest_version(rt, ConsoleJob(), vid, embed=False)
        print(f"état={r['status']} chunks={r['chunks']} pages à relire={r['pages_to_review']}")
        return 0
    ws, kb_id = _resolve(ctx, a)
    rep = BLD.build_kb(rt, ConsoleJob(), kb_id, steps=("process",))
    _show({"documents": rep["documents"], "result": rep["result"]})
    return 0 if rep["result"] == "ok" else 1


def cmd_retry(ctx: AppContext, a: argparse.Namespace) -> int:
    """Relance les documents en échec (ou interrompus) d'UNE base, un par un."""
    from .knowledge.ingest import ingest_version
    ws, kb_id = _resolve(ctx, a)
    rt = ctx.services["knowledge"]
    with session(ctx) as s:
        failed = [(v.id, v.original_name) for v in PL.pending_versions(s, kb_id) if v.processing_state == "failed"]
    for vid, name in failed:
        with session(ctx) as s:
            PL.prepare_reprocess(s, ws, vid)
            s.commit()
        try:
            r = ingest_version(rt, ConsoleJob(quiet=True), vid, embed=False)
            print(f"relancé     {name}  état={r['status']} chunks={r['chunks']}")
        except Exception as exc:  # noqa: BLE001
            print(f"ÉCHEC       {name} : {str(exc)[:200]}")
    print(f"{len(failed)} document(s) relancé(s)")
    return 0


def cmd_recover(ctx: AppContext, a: argparse.Namespace) -> int:
    n = PL.recover_interrupted(ctx.session_factory)
    print(f"{n} version(s) interrompue(s) marquée(s) failed (relançables avec `retry`)")
    return 0


def cmd_embed(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    r = kbops.embed_kb(ctx.services["knowledge"], ConsoleJob(), kb_id, reembed=a.reembed)
    _show(r)
    return 0


def cmd_index(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    _show(kbops.reindex_kb(ctx.services["knowledge"], ConsoleJob(), kb_id))
    return 0


def cmd_check(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    with session(ctx) as s:
        rep = BLD.check_coherence(ctx.services["knowledge"], s, s.get(KnowledgeBase, kb_id))
    for c in rep["checks"]:
        print(("OK  " if c["ok"] else "KO  ") + f"{c['id']:26} {c['detail']}")
    return 0 if rep["ok"] else 1


def cmd_build(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    steps = tuple(x for x in a.steps.split(",") if x)
    rep = BLD.build_kb(ctx.services["knowledge"], ConsoleJob(), kb_id, steps=steps, reembed=a.reembed, publish=a.publish, note=a.note)
    _show({k: rep[k] for k in ("kb_id", "steps", "documents", "result", "published", "publish_refused", "embedding", "embedding_error") if k in rep})
    return 0 if rep["result"] == "ok" else 1


def cmd_publish(ctx: AppContext, a: argparse.Namespace) -> int:
    ws, kb_id = _resolve(ctx, a)
    with session(ctx) as s:
        kv = kbops.publish_kb(s, ws, kb_id, a.note)
        s.commit()
        print(f"version {kv.version_no} publiée (manifeste {kv.manifest_sha256[:12]}…)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__.split("\n")[0])
    top = p.add_subparsers(dest="group", required=True)

    w = top.add_parser("workspace", help="espaces de travail").add_subparsers(dest="cmd", required=True)
    wc = w.add_parser("create", help="crée un espace de travail (affiche le jeton propriétaire une seule fois)")
    wc.add_argument("--name", required=True)
    wc.set_defaults(fn=cmd_workspace_create)

    k = top.add_parser("knowledge", help="documents et bases de connaissances").add_subparsers(dest="cmd", required=True)
    c = k.add_parser("kb-create", help="crée une base ; son dossier de sources est blobs/knowledge_sources/<code>")
    c.add_argument("--code", required=True)
    c.add_argument("--name", required=True)
    c.add_argument("--kind", default="national", choices=["national", "global_practices", "scenario", "prior_reports", "mixed"])
    c.add_argument("--scope-kind", choices=["country", "global", "organization"], help="pays, base globale ou organisation (ITU)")
    c.add_argument("--domain")
    c.add_argument("--language", action="append")
    c.add_argument("--description")
    c.add_argument("--workspace")
    c.set_defaults(fn=cmd_kb_create)
    ls = k.add_parser("kb-list", help="liste les bases et leur état")
    ls.add_argument("--workspace")
    ls.set_defaults(fn=cmd_kb_list)

    m = k.add_parser("sources-migrate", help="copie NON destructive de PDF vers blobs/knowledge_sources (simulation par défaut)")
    m.add_argument("--map", action="append", required=True, metavar="PÉRIMÈTRE=DOSSIER",
                   help="ex. CM=../alerte/data/docs/CM ; organisations : organizations/ITU=…/ITU (répétable)")
    m.add_argument("--source-kind", default="legacy_project", choices=["legacy_project", "platform_existing", "upload"])
    m.add_argument("--label", help="libellé du dossier de départ (provenance)")
    m.add_argument("--apply", action="store_true", help="copier réellement (sinon simulation)")
    m.add_argument("--manifest", help="fichier JSONL où consigner la provenance (avec --apply)")
    m.set_defaults(fn=cmd_sources_migrate)

    for name, fn, hlp in (("sources-list", cmd_sources_list, "fichiers du dossier du périmètre sans enregistrement"),
                          ("sources-verify", cmd_sources_verify, "présence et SHA-256 des fichiers enregistrés"),
                          ("status", cmd_status, "état de la base (documents par état, chunks, vecteurs, index, version)"),
                          ("check", cmd_check, "cohérence documents/fichiers/chunks/FTS/vecteurs"),
                          ("index", cmd_index, "reconstruit l'index lexical de CETTE base (atomique)"),
                          ("retry", cmd_retry, "relance les documents en échec de CETTE base")):
        sp = k.add_parser(name, help=hlp)
        scope_args(sp)
        if name == "status":
            sp.add_argument("--documents", action="store_true", help="liste aussi l'état de chaque document")
        sp.set_defaults(fn=fn)

    ad = k.add_parser("adopt", help="enregistre les fichiers déjà présents dans le dossier du périmètre (sans copie)")
    scope_args(ad)
    ad.add_argument("--file", action="append", help="limiter à ces fichiers (nom ou chemin relatif)")
    ad.add_argument("--manifest", help="manifeste de migration (JSONL) pour reporter la provenance")
    ad.add_argument("--meta", action="append", metavar="CLÉ=VALEUR", help="métadonnée commune (language, doc_type, jurisdiction, redistribution…)")
    ad.set_defaults(fn=cmd_adopt)

    cu = k.add_parser("curate", help="applique un registre de curation (métadonnées validées) aux documents de CETTE base")
    scope_args(cu)
    cu.add_argument("--curation", required=True, help="registre JSON (ex. knowledge_bases/curation/documents.curation.json)")
    cu.add_argument("--manifest", required=True, help="manifeste de migration JSONL (lien fichier → SHA-256)")
    cu.set_defaults(fn=cmd_curate)

    im = k.add_parser("import", help="importe un ou plusieurs fichiers (chacun = un document indépendant)")
    scope_args(im)
    im.add_argument("files", nargs="+")
    im.add_argument("--meta", action="append", metavar="CLÉ=VALEUR")
    im.add_argument("--no-process", action="store_true", help="enregistre sans lancer le traitement")
    im.set_defaults(fn=cmd_import)

    pr = k.add_parser("process", help="traite UN document (--document/--version), ou les documents en attente d'une base")
    scope_args(pr)
    pr.add_argument("--document")
    pr.add_argument("--version")
    pr.set_defaults(fn=cmd_process)

    rc = k.add_parser("recover", help="marque failed les versions restées « en cours » après un arrêt")
    rc.set_defaults(fn=cmd_recover)

    em = k.add_parser("embed", help="calcule les embeddings MANQUANTS de cette base")
    scope_args(em)
    em.add_argument("--reembed", action="store_true", help="nouveau modèle : ancien index conservé jusqu'à la bascule")
    em.set_defaults(fn=cmd_embed)

    bd = k.add_parser("build", help="construit UNE base (documents en attente, embeddings, index, contrôle)")
    scope_args(bd)
    bd.add_argument("--steps", default="process,embed,index", help="parmi process,embed,index,check")
    bd.add_argument("--reembed", action="store_true")
    bd.add_argument("--publish", action="store_true", help="publie une version si tout est cohérent")
    bd.add_argument("--note")
    bd.set_defaults(fn=cmd_build)

    pu = k.add_parser("publish", help="publie une version de CETTE base")
    scope_args(pu)
    pu.add_argument("--note")
    pu.set_defaults(fn=cmd_publish)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    try:
        return a.fn(make_ctx(), a)
    except (S.SourceError, AppError) as exc:
        print(f"REFUS : {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except KeyboardInterrupt:
        print("interrompu : les documents en cours seront marqués failed et relançables (`retry`)", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
