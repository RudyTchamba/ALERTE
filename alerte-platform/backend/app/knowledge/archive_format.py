"""Format d'archive `alerte-kb-archive` 1.0.0 (doc 07 §7.6, inspiré de BagIt) : écriture et lecture DURCIE, sans base de données.

L'archive ne dépend ni de SQLite, ni de FTS5, ni de ChromaDB. Aucun chemin absolu, identifiant de machine ou secret.
Lecture : zip-slip, chemins absolus, liens symboliques, bombes (500 Mo / 10 000 entrées / ratio 100:1), liste blanche de
chemins, hash du manifest, hash de chaque fichier, cohérence croisée. Le moindre défaut = rejet de l'archive entière.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import jsonschema
import numpy as np

from ..core.canonical_json import canonical_bytes

FORMAT = "alerte-kb-archive"
FORMAT_VERSION = "1.0.0"
MAX_UNCOMPRESSED = 500 * 1024 * 1024
MAX_ENTRIES = 10_000
MAX_RATIO = 100
MODES = ("full_reimportable", "processed_only", "documents_only", "selection", "open_publication")
_FIXED_DATE = (2020, 1, 1, 0, 0, 0)  # archive reproductible

_EXACT = {"manifest.json", "manifest.sha256", "bag-info.txt", "signature.json", "data/kb.json", "data/documents.jsonl",
          "data/chunks.jsonl", "data/mandates.jsonl", "data/references.jsonl", "data/embeddings/embeddings.index.jsonl"}
_RX = [re.compile(r"^data/embeddings/[0-9a-f]{16}\.f32\.npy$"), re.compile(r"^data/sources/[A-Za-z0-9][A-Za-z0-9._-]{0,150}$")]
_DIRS = {"data/", "data/sources/", "data/embeddings/"}
_SHA = re.compile(r"^[0-9a-f]{64}$")

_S = {"type": "string"}
_NS = {"type": ["string", "null"]}
MANIFEST_SCHEMA = {
    "type": "object", "additionalProperties": True,
    "required": ["format", "format_version", "kb", "created_at", "exporter", "mode", "files", "embedding", "chunking",
                 "documents_summary", "provenance", "warnings"],
    "properties": {
        "format": {"const": FORMAT}, "format_version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
        "kb": {"type": "object", "required": ["id", "code", "name"], "properties": {"id": _S, "code": _S, "name": _S}},
        "created_at": _S, "exporter": {"type": "object", "required": ["name", "version"]},
        "mode": {"enum": list(MODES)},
        "files": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                             "required": ["path", "sha256", "bytes", "records"],
                                             "properties": {"path": _S, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                                            "bytes": {"type": "integer", "minimum": 0},
                                                            "records": {"type": ["integer", "null"], "minimum": 0}}}},
        "embedding": {"type": "object", "required": ["included"]},
        "chunking": {"type": "object"}, "documents_summary": {"type": "object"}, "provenance": {"type": "object"},
        "warnings": {"type": "array", "items": _S},
    },
}
KB_SCHEMA = {"type": "object", "required": ["id", "code", "name", "kind"],
             "properties": {"id": _S, "code": _S, "name": _S, "kind": _S, "languages": {"type": ["array", "null"]},
                            "description": _NS, "domain": _NS, "chunking_params": {"type": ["object", "null"]},
                            "embedder_fingerprint": {"type": ["object", "null"]}}}
DOC_SCHEMA = {
    "type": "object", "required": ["document_id", "code", "title", "reliability", "validity", "redistribution", "version"],
    "properties": {
        "document_id": _S, "code": {"type": "string", "maxLength": 64}, "title": {"type": "string", "maxLength": 500},
        "reliability": {"enum": ["official", "summary", "unofficial", "unknown", "not_found"]},
        "validity": {"enum": ["in_force", "replaced", "unknown"]},
        "redistribution": {"enum": ["allowed", "restricted", "unknown"]},
        "evidence_default": {"enum": ["documented", "inferred", "assumed"]},
        "version": {"type": "object", "required": ["id", "version_no", "blob_sha256", "status"],
                    "properties": {"id": _S, "version_no": {"type": "integer", "minimum": 1},
                                   "blob_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                                   "status": {"enum": ["ready", "needs_review"]}, "source_file": _NS}}}}
CHUNK_SCHEMA = {"type": "object", "required": ["id", "document_version_id", "ordinal", "text", "text_sha256"],
                "properties": {"id": _S, "document_version_id": _S, "ordinal": {"type": "integer", "minimum": 0},
                               "text": _S, "text_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                               "evidence_tag": {"enum": ["documented", "inferred", "assumed"]}}}


class ArchiveError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code, self.message, self.details = code, message, details or {}


def jsonl_bytes(records: list[dict]) -> bytes:
    return b"".join(canonical_bytes(r) + b"\n" for r in records)


def safe_source_name(code: str, version_no: int, ext: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", code).strip("._-") or "doc"
    name = f"{base}-v{version_no}{ext}"
    n = 2
    while name in used:
        name = f"{base}-{n}-v{version_no}{ext}"
        n += 1
    used.add(name)
    return name


# --------------------------------------------------------------------------- écriture
def archive_message(manifest_sha256: str) -> bytes:
    return f"ALERTE-KB-ARCHIVE-v1|{manifest_sha256}".encode()


class ArchiveWriter:
    def __init__(self, out: Path) -> None:
        self._z = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
        self.files: list[dict] = []

    def _info(self, name: str) -> zipfile.ZipInfo:
        zi = zipfile.ZipInfo(name, _FIXED_DATE)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = (stat.S_IFREG | 0o644) << 16
        return zi

    def add_bytes(self, name: str, data: bytes, records: int | None = None, *, listed: bool = True) -> None:
        self._z.writestr(self._info(name), data)
        if listed:
            self.files.append({"path": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "records": records})

    def add_file(self, name: str, src: Path) -> None:
        h, n = hashlib.sha256(), 0
        with src.open("rb") as fh, self._z.open(self._info(name), "w") as out:
            for buf in iter(lambda: fh.read(1 << 20), b""):
                h.update(buf)
                n += len(buf)
                out.write(buf)
        self.files.append({"path": name, "sha256": h.hexdigest(), "bytes": n, "records": None})

    def finish(self, manifest: dict, signer: Any = None) -> str:
        """Écrit bag-info.txt, manifest.json (JSON canonique), manifest.sha256 et, si une clé est fournie,
        signature.json (Ed25519 sur `ALERTE-KB-ARCHIVE-v1|<sha256 du manifest>`) ; renvoie l'empreinte du manifest."""
        kb = manifest["kb"]
        info = (f"Bag-Software-Agent: {manifest['exporter']['name']} {manifest['exporter']['version']}\n"
                f"Source-Organization: ALERTE\nExternal-Description: KB {kb['code']} - {kb['name']}\n"
                f"Format: {FORMAT} {FORMAT_VERSION}\nMode: {manifest['mode']}\nPayload-Oxum: "
                f"{sum(f['bytes'] for f in self.files)}.{len(self.files)}\n").encode()
        self.add_bytes("bag-info.txt", info)
        manifest = {**manifest, "files": sorted(self.files, key=lambda f: f["path"])}
        data = canonical_bytes(manifest)
        sha = hashlib.sha256(data).hexdigest()
        self._z.writestr(self._info("manifest.json"), data)
        self._z.writestr(self._info("manifest.sha256"), f"{sha}  manifest.json\n".encode())
        if signer is not None:
            sig = {"algorithm": "Ed25519", "key_id": signer.key_id(), "public_key_pem": signer.public_pem(),
                   "manifest_sha256": sha, "signature": signer.sign_bytes(archive_message(sha))}
            self._z.writestr(self._info("signature.json"), canonical_bytes(sig))
        self._z.close()
        return sha


def npy_bytes(matrix: np.ndarray) -> bytes:
    buf = io.BytesIO()
    np.save(buf, np.ascontiguousarray(matrix, dtype="<f4"), allow_pickle=False)
    return buf.getvalue()


# --------------------------------------------------------------------------- lecture durcie
@dataclass
class ParsedArchive:
    manifest: dict
    manifest_sha256: str
    kb: dict
    documents: list[dict]
    chunks: list[dict]
    sources: dict[str, int]                      # nom dans le zip -> taille
    embeddings: tuple[list[str], np.ndarray] | None = None
    warnings: list[str] = field(default_factory=list)
    signature: dict | None = None  # {valid, key_id} si signature.json présent (une signature invalide est refusée)


def _check_name(name: str) -> None:
    if not name or "\x00" in name or "\\" in name or name.startswith("/") or re.match(r"^[A-Za-z]:", name) \
            or name.startswith(("//", "~")):
        raise ArchiveError("kb.import.integrity_failed", f"chemin invalide dans l'archive : {name!r}", {"path": name})
    if any(part in ("..", ".") for part in name.split("/")):
        raise ArchiveError("kb.import.integrity_failed", f"traversée de chemin refusée : {name!r}", {"path": name})
    if name in _DIRS or name in _EXACT or any(r.match(name) for r in _RX):
        return
    raise ArchiveError("kb.import.integrity_failed", f"chemin hors liste blanche : {name!r}", {"path": name})


def _read_member(z: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    """Lit en bornant la taille RÉELLE (un en-tête de zip peut mentir)."""
    out = io.BytesIO()
    with z.open(info) as fh:
        for buf in iter(lambda: fh.read(1 << 20), b""):
            out.write(buf)
            if out.tell() > info.file_size or out.tell() > MAX_UNCOMPRESSED:
                raise ArchiveError("kb.import.integrity_failed", f"taille décompressée incohérente : {info.filename}")
    return out.getvalue()


def hash_member(z: zipfile.ZipFile, info: zipfile.ZipInfo) -> tuple[str, int]:
    h, n = hashlib.sha256(), 0
    with z.open(info) as fh:
        for buf in iter(lambda: fh.read(1 << 20), b""):
            n += len(buf)
            if n > info.file_size:
                raise ArchiveError("kb.import.integrity_failed", f"taille décompressée incohérente : {info.filename}")
            h.update(buf)
    return h.hexdigest(), n


_VALIDATORS: dict[int, Any] = {}


def _validate(schema: dict, obj: Any, what: str) -> None:
    v = _VALIDATORS.get(id(schema))
    if v is None:  # validateur compilé une seule fois par schéma (jsonschema.validate() est trop lent par chunk)
        jsonschema.Draft202012Validator.check_schema(schema)
        v = _VALIDATORS[id(schema)] = jsonschema.Draft202012Validator(schema)
    err = next(iter(v.iter_errors(obj)), None)
    if err is not None:
        raise ArchiveError("kb.import.integrity_failed", f"{what} invalide : {err.message[:200]}")


def _jsonl(data: bytes, what: str) -> list[dict]:
    out = []
    for i, line in enumerate(data.decode("utf-8").split("\n")):
        if line.strip():
            try:
                rec = json.loads(line)
            except ValueError as exc:
                raise ArchiveError("kb.import.integrity_failed", f"{what} ligne {i + 1} : JSON invalide") from exc
            if not isinstance(rec, dict):
                raise ArchiveError("kb.import.integrity_failed", f"{what} ligne {i + 1} : objet attendu")
            out.append(rec)
    return out


def open_and_validate(path: Path) -> ParsedArchive:
    """Valide TOUT avant le moindre effet de bord. Lève ArchiveError (code `kb.import.integrity_failed`)."""
    if not zipfile.is_zipfile(path):
        raise ArchiveError("kb.import.integrity_failed", "le fichier n'est pas une archive ZIP")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ArchiveError("kb.import.too_large", f"trop d'entrées ({len(infos)} > {MAX_ENTRIES})")
        total = sum(i.file_size for i in infos)
        if total > MAX_UNCOMPRESSED:
            raise ArchiveError("kb.import.too_large", f"taille décompressée excessive ({total} octets)")
        if total > MAX_RATIO * max(1, path.stat().st_size) and total > 1 << 20:
            raise ArchiveError("kb.import.too_large", "ratio de compression suspect (bombe de décompression)")
        seen: set[str] = set()
        for i in infos:
            _check_name(i.filename)
            if i.filename in seen:
                raise ArchiveError("kb.import.integrity_failed", f"entrée dupliquée : {i.filename}")
            seen.add(i.filename)
            mode = (i.external_attr >> 16) & 0o170000
            if mode and mode not in (stat.S_IFREG, stat.S_IFDIR):
                raise ArchiveError("kb.import.integrity_failed", f"lien symbolique ou fichier spécial refusé : {i.filename}")
            if i.flag_bits & 0x1:
                raise ArchiveError("kb.import.integrity_failed", f"entrée chiffrée refusée : {i.filename}")
            if i.file_size > (1 << 20) and i.file_size > MAX_RATIO * max(1, i.compress_size):
                raise ArchiveError("kb.import.too_large", f"ratio de compression suspect : {i.filename}")
        by_name = {i.filename: i for i in infos}
        for need in ("manifest.json", "manifest.sha256"):
            if need not in by_name:
                raise ArchiveError("kb.import.integrity_failed", f"{need} absent")
        mbytes = _read_member(z, by_name["manifest.json"])
        msha = hashlib.sha256(mbytes).hexdigest()
        declared = _read_member(z, by_name["manifest.sha256"]).decode("utf-8", "replace").split()
        if not declared or declared[0] != msha:
            raise ArchiveError("kb.import.integrity_failed", "manifest.sha256 ne correspond pas au manifest")
        try:
            manifest = json.loads(mbytes)
        except ValueError as exc:
            raise ArchiveError("kb.import.integrity_failed", "manifest.json illisible") from exc
        _validate(MANIFEST_SCHEMA, manifest, "manifest")
        if canonical_bytes(manifest) != mbytes:
            raise ArchiveError("kb.import.integrity_failed", "manifest.json n'est pas en JSON canonique")
        if manifest["format_version"].split(".")[0] != FORMAT_VERSION.split(".")[0]:
            raise ArchiveError("kb.import.unsupported_version", f"version de format non supportée : {manifest['format_version']}")
        listed = {f["path"]: f for f in manifest["files"]}
        if len(listed) != len(manifest["files"]):
            raise ArchiveError("kb.import.integrity_failed", "fichier listé deux fois dans le manifest")
        signature = None
        if "signature.json" in by_name:
            from ..audit.signing import verify_with_public_pem
            try:
                sj = json.loads(_read_member(z, by_name["signature.json"]))
            except ValueError as exc:
                raise ArchiveError("kb.import.integrity_failed", "signature.json illisible") from exc
            ok, kid = (verify_with_public_pem(str(sj.get("public_key_pem", "")), archive_message(msha), str(sj.get("signature", "")))
                       if sj.get("manifest_sha256") == msha else (False, None))
            if not ok:
                raise ArchiveError("kb.import.integrity_failed", "signature Ed25519 de l'archive invalide")
            signature = {"valid": True, "key_id": kid, "algorithm": "Ed25519"}
        content = {n for n in by_name if not n.endswith("/") and n not in ("manifest.json", "manifest.sha256", "signature.json")}
        if content != set(listed):
            raise ArchiveError("kb.import.integrity_failed", "fichiers de l'archive ≠ fichiers du manifest",
                               {"unlisted": sorted(content - set(listed)), "missing": sorted(set(listed) - content)})
        blobs: dict[str, bytes] = {}
        for name, f in listed.items():
            info = by_name[name]
            if name.startswith("data/sources/"):
                sha, n = hash_member(z, info)
            else:
                blobs[name] = _read_member(z, info)
                sha, n = hashlib.sha256(blobs[name]).hexdigest(), len(blobs[name])
            if sha != f["sha256"] or n != f["bytes"]:
                raise ArchiveError("kb.import.integrity_failed", f"empreinte ou taille incorrecte : {name}", {"path": name})
        for need in ("data/kb.json", "data/documents.jsonl", "data/chunks.jsonl"):
            if need not in blobs:
                raise ArchiveError("kb.import.integrity_failed", f"{need} absent")
        try:
            kb = json.loads(blobs["data/kb.json"])
        except ValueError as exc:
            raise ArchiveError("kb.import.integrity_failed", "kb.json illisible") from exc
        _validate(KB_SCHEMA, kb, "kb.json")
        docs, chunks = _jsonl(blobs["data/documents.jsonl"], "documents.jsonl"), _jsonl(blobs["data/chunks.jsonl"], "chunks.jsonl")
        for d in docs:
            _validate(DOC_SCHEMA, d, "document")
        for c in chunks:
            _validate(CHUNK_SCHEMA, c, "chunk")
        for name, f in listed.items():
            if f["records"] is not None and name == "data/documents.jsonl" and f["records"] != len(docs):
                raise ArchiveError("kb.import.integrity_failed", "nombre de documents ≠ manifest")
            if f["records"] is not None and name == "data/chunks.jsonl" and f["records"] != len(chunks):
                raise ArchiveError("kb.import.integrity_failed", "nombre de chunks ≠ manifest")
        vids, dids, cids = set(), set(), set()
        for d in docs:
            v = d["version"]
            dids.add(d["document_id"])
            if v["id"] in vids:
                raise ArchiveError("kb.import.integrity_failed", f"version dupliquée : {v['id']}")
            vids.add(v["id"])
            src = v.get("source_file")
            if src and (src not in listed or not src.startswith("data/sources/")):
                raise ArchiveError("kb.import.integrity_failed", f"original manquant : {src}")
        for c in chunks:
            if c["document_version_id"] not in vids:
                raise ArchiveError("kb.import.integrity_failed", f"chunk {c['id']} sans version de document")
            if c["id"] in cids:
                raise ArchiveError("kb.import.integrity_failed", f"chunk dupliqué : {c['id']}")
            cids.add(c["id"])
            if hashlib.sha256(c["text"].encode("utf-8")).hexdigest() != c["text_sha256"]:
                raise ArchiveError("kb.import.integrity_failed", f"text_sha256 incorrect pour le chunk {c['id']}")
        emb = None
        e = manifest["embedding"]
        if e.get("included"):
            key = e.get("key", "")
            npy, idx = f"data/embeddings/{key}.f32.npy", "data/embeddings/embeddings.index.jsonl"
            if npy not in blobs or idx not in blobs:
                raise ArchiveError("kb.import.integrity_failed", "embeddings annoncés mais absents")
            try:
                mat = np.load(io.BytesIO(blobs[npy]), allow_pickle=False)
            except Exception as exc:  # noqa: BLE001
                raise ArchiveError("kb.import.integrity_failed", "matrice d'embeddings illisible") from exc
            index = _jsonl(blobs[idx], "embeddings.index.jsonl")
            if mat.dtype != np.dtype("<f4") or mat.ndim != 2 or mat.shape[0] != len(index) or mat.shape[1] != e.get("dimension"):
                raise ArchiveError("kb.import.integrity_failed", "matrice d'embeddings incohérente (forme/type)")
            ids = [r.get("chunk_id") for r in index]
            if [r.get("row") for r in index] != list(range(len(index))) or len(set(ids)) != len(ids) or not set(ids) <= cids:
                raise ArchiveError("kb.import.integrity_failed", "index d'embeddings incohérent avec les chunks")
            emb = (ids, mat)
        sources = {n: by_name[n].file_size for n in listed if n.startswith("data/sources/")}
    return ParsedArchive(manifest, msha, kb, docs, chunks, sources, emb, list(manifest["warnings"]), signature)
