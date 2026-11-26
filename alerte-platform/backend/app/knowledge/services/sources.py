"""Documents sources par périmètre : stockage physique de référence et migration NON destructive.

Racine : `<ALERTE_DATA_DIR>/blobs/knowledge_sources/` (un SEUL emplacement, pas de lien physique ni symbolique, pas de 2ᵉ racine) :
    CM/ AE/ GL/                  périmètres nationaux et global : `<CODE>/<fichier>.pdf`
    organizations/ITU/           organisations (l'ITU n'est pas un pays)
Un PDF = un fichier dans le dossier de son périmètre, sans sous-dossier par document. Le chemin RELATIF est enregistré en base
(`document_version.storage_path`) : jamais de chemin absolu, donc portable d'une machine à l'autre.

Règles (jamais de dépendance au nom du fichier) :
* le périmètre est CHOISI (base de destination) ; le nom d'un fichier ne sert jamais à déduire pays, éditeur, année ou type ;
* le nom physique est le nom fourni, nettoyé ; en cas de collision avec un AUTRE contenu, un suffixe technique `__<sha8>` est ajouté ;
* aucun écrasement ; un contenu déjà enregistré (SHA-256) est un doublon ;
* la migration ne déplace, ne renomme et ne modifie jamais la source ; la copie est vérifiée par SHA-256 ; tout est consigné (JSONL).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import BinaryIO

SCOPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,31}$")
SCOPE_KINDS = ("country", "global", "organization")
ORG_DIR = "organizations"
_BAD = re.compile(r"[\x00-\x1f\x7f/\\:*?\"<>|]")
MAX_NAME = 180


class SourceError(Exception):
    """Erreur lisible destinée à l'utilisateur (CLI ou API)."""

    def __init__(self, message: str, code: str = "sources.error") -> None:
        super().__init__(message)
        self.code = code


def validate_scope(scope: str | None) -> str:
    """Code de périmètre (ex. `CM`, `AE`, `GL`, `ITU`) ; un chemin `organizations/ITU` est accepté (relatif au dossier racine)."""
    if not scope:
        raise SourceError("un périmètre explicite est obligatoire (code de pays ou de base, ex. CM)", "sources.scope_required")
    parts = scope.split("/")
    ok = (len(parts) == 1 and SCOPE_RE.match(parts[0]) and parts[0].lower() != ORG_DIR) or (len(parts) == 2 and parts[0] == ORG_DIR and SCOPE_RE.match(parts[1]))
    if not ok:
        raise SourceError(f"code de périmètre invalide : {scope!r} (attendu : 2 à 32 caractères A-Z a-z 0-9 _ -, ex. CM)", "sources.scope_invalid")
    return scope


def scope_relpath(scope_kind: str | None, code: str) -> str:
    """Dossier (relatif à la racine des sources) d'une base : `CM`, `GL` ou `organizations/ITU`."""
    code = re.sub(r"[^A-Za-z0-9_-]", "_", code or "").strip("_-")
    if not SCOPE_RE.match(code):
        raise SourceError(f"code de base inutilisable comme dossier : {code!r}", "sources.scope_invalid")
    return f"{ORG_DIR}/{code}" if scope_kind == "organization" else code


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def safe_physical_name(name: str) -> str:
    """Nom de fichier sûr : sans séparateurs ni caractères de contrôle, longueur bornée, extension conservée ; jamais vide."""
    base = _BAD.sub("_", (name or "").replace("\\", "/").rsplit("/", 1)[-1]).strip(" .")
    stem, dot, ext = base.rpartition(".")
    if not dot:
        stem, ext = base, ""
    stem = (stem or "document")[: MAX_NAME - len(ext) - 1]
    return f"{stem}.{ext.lower()}" if ext else stem


def scope_dir(sources_root: Path, scope: str) -> Path:
    return sources_root.joinpath(*validate_scope(scope).split("/"))


def index_scope(sources_root: Path, scope: str) -> dict[str, str]:
    """SHA-256 -> nom physique, pour les fichiers déjà présents dans le dossier de la portée."""
    d = scope_dir(sources_root, scope)
    return {sha256_file(p): p.name for p in sorted(d.iterdir()) if p.is_file()} if d.is_dir() else {}


def unique_physical_name(directory: Path, name: str, sha: str, taken: set[str]) -> str:
    """Nom libre dans `directory` : le nom d'origine, sinon `<stem>__<sha8>.<ext>` ; jamais d'écrasement."""
    name = safe_physical_name(name)
    if name not in taken and not (directory / name).exists():
        return name
    stem, dot, ext = name.rpartition(".")
    stem, ext = (stem, "." + ext) if dot else (name, "")
    cand = f"{stem}__{sha[:8]}{ext}"
    i = 2
    while cand in taken or (directory / cand).exists():
        cand = f"{stem}__{sha[:8]}-{i}{ext}"
        i += 1
    return cand


@dataclass
class MigrationItem:
    scope: str
    source_path: str
    source_kind: str                 # legacy_project | platform_existing | upload
    source_folder_label: str | None  # dossier de départ choisi par l'opérateur (à vérifier), jamais le nom du fichier
    migration_filename: str          # nom du fichier AU MOMENT de la migration (pas forcément le nom de téléchargement)
    download_name: str | None = None  # nom de téléchargement d'origine : None tant qu'il n'est pas réellement connu
    sha256: str = ""
    size: int = 0
    decision: str = "planned"        # copied | duplicate_skipped | renamed_collision | planned
    destination: str | None = None   # relatif à <storage>/knowledge_sources
    duplicate_of: str | None = None
    note: str | None = None
    migrated_at: str | None = None


@dataclass
class MigrationReport:
    dry_run: bool
    items: list[MigrationItem] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for it in self.items:
            out[it.decision] = out.get(it.decision, 0) + 1
        return out


def _list_pdfs(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def migrate(sources_root: Path, jobs: Iterable[tuple[str, Path, str, str | None]], *, dry_run: bool = True) -> MigrationReport:
    """Copie non destructive. `jobs` = (portée, dossier source, nature de la source, libellé du dossier de départ).

    * lit la source en lecture seule (aucun déplacement, renommage ni écriture) ;
    * refuse un dossier de destination situé dans la source ;
    * ne recopie jamais un contenu déjà présent dans la portée (SHA-256) ;
    * copie dans un fichier créé en exclusivité (jamais d'écrasement) puis VÉRIFIE le SHA-256 de la copie.
    """
    report = MigrationReport(dry_run=dry_run)
    sources_root = sources_root.resolve()
    seen: dict[str, dict[str, str]] = {}
    taken: dict[str, set[str]] = {}
    for scope, folder, kind, label in jobs:
        validate_scope(scope)
        folder = folder.resolve()
        if not folder.is_dir():
            raise SourceError(f"dossier source introuvable : {folder}", "sources.source_missing")
        if sources_root == folder or sources_root in folder.parents or folder in sources_root.parents:
            raise SourceError("le dossier de destination ne doit pas être dans (ou contenir) le dossier source", "sources.overlap")
        seen.setdefault(scope, index_scope(sources_root, scope))
        taken.setdefault(scope, set(seen[scope].values()))
        dest_dir = scope_dir(sources_root, scope)
        for pdf in _list_pdfs(folder):
            sha = sha256_file(pdf)
            item = MigrationItem(scope, str(pdf), kind, label, pdf.name, sha256=sha, size=pdf.stat().st_size)
            if sha in seen[scope]:
                item.decision, item.duplicate_of = "duplicate_skipped", f"{scope}/{seen[scope][sha]}"
                item.note = "même contenu déjà présent dans la portée : non recopié"
                report.items.append(item)
                continue
            name = unique_physical_name(dest_dir, pdf.name, sha, taken[scope])
            item.decision = "renamed_collision" if name != safe_physical_name(pdf.name) else "copied"
            if item.decision == "renamed_collision":
                item.note = "un autre fichier de même nom (contenu différent) existe : suffixe technique ajouté"
            item.destination = f"{scope}/{name}"
            if not dry_run:
                dest_dir.mkdir(parents=True, exist_ok=True)
                target = dest_dir / name
                with pdf.open("rb") as src, target.open("xb") as dst:  # 'x' : échoue plutôt qu'écraser
                    shutil.copyfileobj(src, dst, 1 << 20)
                shutil.copystat(pdf, target, follow_symlinks=True)
                if sha256_file(target) != sha:
                    target.unlink(missing_ok=True)
                    raise SourceError(f"copie corrompue pour {pdf.name} (SHA-256 différent) : abandon", "sources.copy_mismatch")
                item.migrated_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")
            seen[scope][sha] = name
            taken[scope].add(name)
            report.items.append(item)
    return report


def write_manifest(path: Path, report: MigrationReport) -> None:
    """Ajoute les lignes du manifeste de provenance (JSONL, une ligne par fichier traité)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for it in report.items:
            f.write(json.dumps(asdict(it), ensure_ascii=False, sort_keys=True) + "\n")


def verify_scope(sources_root: Path, scope: str, expected: dict[str, str]) -> dict[str, list[str]]:
    """Compare le dossier d'une portée à une liste attendue {chemin relatif: sha256} ; signale manquants, modifiés, inconnus."""
    d = scope_dir(sources_root, scope)
    present = {f"{scope}/{p.name}": sha256_file(p) for p in sorted(d.iterdir()) if p.is_file()} if d.is_dir() else {}
    return {"missing": sorted(k for k in expected if k not in present),
            "modified": sorted(k for k, v in expected.items() if k in present and present[k] != v),
            "unknown": sorted(k for k in present if k not in expected)}


# --------------------------------------------------------------------------- dépôt d'un fichier (import individuel ou multiple)
_PLACE_LOCK = threading.Lock()


@dataclass
class Staged:
    """Fichier reçu, écrit dans un fichier temporaire du MÊME volume (rename atomique), pas encore rangé."""

    tmp: Path
    sha256: str
    size: int

    def discard(self) -> None:
        self.tmp.unlink(missing_ok=True)


def stage_stream(sources_root: Path, stream: BinaryIO, *, max_bytes: int | None = None, chunk: int = 1 << 20) -> Staged:
    """Écrit un flux sans le charger en mémoire ; calcule le SHA-256. Lève `ValueError` si la taille maximale est dépassée."""
    tmpdir = sources_root / ".incoming"
    tmpdir.mkdir(parents=True, exist_ok=True)
    h, size = hashlib.sha256(), 0
    fd, name = tempfile.mkstemp(dir=tmpdir, prefix="up-")
    try:
        with os.fdopen(fd, "wb") as out:
            while True:
                buf = stream.read(chunk)
                if not buf:
                    break
                size += len(buf)
                if max_bytes is not None and size > max_bytes:
                    raise ValueError("fichier trop volumineux")
                h.update(buf)
                out.write(buf)
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Staged(Path(name), h.hexdigest(), size)


def place(sources_root: Path, staged: Staged, scope: str, filename: str) -> str:
    """Range le fichier dans le dossier du périmètre sous un nom libre (jamais d'écrasement). Renvoie le chemin RELATIF
    (`CM/nom.pdf`) à enregistrer en base."""
    d = scope_dir(sources_root, scope)
    d.mkdir(parents=True, exist_ok=True)
    with _PLACE_LOCK:
        name = unique_physical_name(d, filename, staged.sha256, set())
        os.replace(staged.tmp, d / name)
    return f"{validate_scope(scope)}/{name}"


def resolve(sources_root: Path, relpath: str) -> Path:
    """Chemin absolu d'un `storage_path` ; refuse toute évasion du dossier racine (`..`, chemin absolu)."""
    root = sources_root.resolve()
    p = (root / relpath).resolve()
    if root != p and root not in p.parents:
        raise SourceError("chemin de stockage hors de la racine des sources", "sources.path_escape")
    return p
