#!/usr/bin/env python3
"""Construit UNE base de connaissances à partir d'un dossier de PDF, de zéro, en une seule commande reprenable.

    cd alerte-platform/backend && source .venv/bin/activate          # Windows : .\\.venv\\Scripts\\Activate.ps1
    python scripts/build_kb_from_pdfs.py --country CM --src <dossier contenant les PDF du Cameroun>
    python scripts/build_kb_from_pdfs.py --country CM --src <dossier> --publish      # publie si, et seulement si, tout est complet
    python scripts/build_kb_from_pdfs.py --country GL --src <PDF>/GL                  # précédents mondiaux (16 PDF) ; AE : --country AE --src <PDF>/AE
    python scripts/build_kb_from_pdfs.py --country ITU --scope-kind organization --src <PDF>/ITU   # organisation (Y.3172, AI Readiness)

Ce que fait le script, dans l'ordre (chaque étape appelle `python -m app.cli …`, que vous pouvez lancer à la main) :
  0. contrôles préalables : dossier de PDF, fichier de curation, serveur d'embeddings joignable ET modèle servi ;
  1. espace de travail : crée « ALERTE — Demonstration » s'il n'y en a aucun (le JETON PROPRIÉTAIRE est affiché UNE FOIS : copiez-le) ;
  2. base : `knowledge kb-create` si la base n'existe pas ;
  3. copie des PDF dans le stockage (`sources-migrate --apply`, la source n'est jamais modifiée ; doublons ignorés par SHA-256) ;
  4. enregistrement des documents (`adopt`) ;
  5. métadonnées d'auteur (`curate`, titres, types, fiabilité) ;
  6. construction : extraction/OCR, découpage, VECTEURS, index lexical, contrôle de cohérence (`build --steps process,embed,index,check`) ;
  7. état final (`status`, `check`) ; avec --publish : publication (REFUSÉE si des vecteurs manquent).

Reprise : relancez la MÊME commande ; les étapes déjà faites sont ignorées ou reprises (documents déjà traités, vecteurs déjà calculés).
Le script n'écrit aucun secret sur disque et ne supprime rien. Les PDF ne sont PAS dans le dépôt git (droits non confirmés) : l'équipe les fournit.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
CURATION = BACKEND.parent / "knowledge_bases" / "curation" / "documents.curation.json"


def load_env_file() -> None:
    """Lit backend/.env sans écraser l'environnement (comme le backend) pour les contrôles préalables."""
    f = BACKEND / ".env"
    if f.is_file():
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.split(" #")[0].strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cli(*args: str, capture: bool = False) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "app.cli", *args]
    print("   $ python -m app.cli " + " ".join(a if " " not in a else f'"{a}"' for a in args), flush=True)
    return subprocess.run(cmd, cwd=BACKEND, text=True, encoding="utf-8", errors="replace",
                          capture_output=capture, stdin=subprocess.DEVNULL)


def step(n: int, total: int, title: str) -> None:
    print(f"\n[{n}/{total}] {title}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"\nARRÊT : {msg}", file=sys.stderr)
    sys.exit(code)


def check_embedder() -> None:
    url, model = os.environ.get("ALERTE_EMBED_BASE_URL"), os.environ.get("ALERTE_EMBED_MODEL")
    if not url or not model:
        die("serveur d'embeddings non configuré : définissez ALERTE_EMBED_BASE_URL et ALERTE_EMBED_MODEL dans backend/.env "
            "(ex. http://localhost:11434/v1 et bge-m3 ; Ollama : `ollama pull bge-m3`). Sans vecteurs la base ne peut pas être publiée.")
    try:
        req = urllib.request.Request(url.rstrip("/") + "/models")
        with urllib.request.urlopen(req, timeout=8) as r:  # noqa: S310 - URL configurée par l'utilisateur
            served = [str(m.get("id")) for m in json.load(r).get("data", [])]
    except (urllib.error.URLError, OSError, ValueError) as exc:
        die(f"serveur d'embeddings injoignable ({url}) : {exc.__class__.__name__}. Démarrez Ollama (ou le serveur configuré), "
            f"puis testez : curl {url.rstrip('/')}/models")
    if model not in served and f"{model}:latest" not in served:
        die(f"le modèle d'embeddings « {model} » n'est pas servi par {url} (servis : {', '.join(served) or 'aucun'}). "
            "Ollama : `ollama pull bge-m3` ; vérifiez le nom exact avec `ollama list`.")
    print(f"   embeddings : {url} — modèle « {model} » servi : OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", required=True, help="code de la base (ex. CM)")
    ap.add_argument("--src", required=True, help="dossier contenant DIRECTEMENT les PDF de cette base (ex. …/alerte/data/docs/CM)")
    ap.add_argument("--scope-kind", default="country", choices=["country", "global", "organization"],
                    help="type de base : country (CM, AE, GL : défaut) ; organization pour ITU (stockée sous blobs/knowledge_sources/organizations/ITU)")
    ap.add_argument("--curation", default=str(CURATION), help="fichier de métadonnées d'auteur (défaut : knowledge_bases/curation/documents.curation.json)")
    ap.add_argument("--workspace-name", default="ALERTE — Demonstration", help="nom de l'espace créé s'il n'en existe aucun")
    ap.add_argument("--allow-partial", action="store_true",
                    help="continuer même si le dossier ne contient pas TOUS les documents attendus par le fichier de curation (essai sur un échantillon)")
    ap.add_argument("--publish", action="store_true", help="publier la base à la fin (refusé si des vecteurs manquent)")
    ap.add_argument("--note", default="Base reconstruite à partir des PDF", help="note de publication")
    a = ap.parse_args()
    cc = a.country.upper()
    total = 8
    load_env_file()
    data_dir = Path(os.environ.get("ALERTE_DATA_DIR", "./data"))
    manifest = (data_dir if data_dir.is_absolute() else BACKEND / data_dir) / f"migration_manifest_{cc}.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)

    step(0, total, "Contrôles préalables")
    src = Path(a.src).expanduser().resolve()
    pdfs = sorted(src.glob("*.pdf")) if src.is_dir() else []
    if not pdfs:
        die(f"aucun PDF trouvé directement dans {src}. Le dossier doit contenir les fichiers .pdf de la base {cc} "
            "(ils ne sont pas dans le dépôt git : demandez le dossier `alerte/data/docs` à l'équipe).")
    cur = Path(a.curation)
    print(f"   {len(pdfs)} PDF dans {src}")
    if not cur.is_file():
        die(f"fichier de curation introuvable : {cur}")
    check_embedder()

    step(1, total, "Espace de travail")
    r = cli("knowledge", "kb-list", capture=True)
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 and ("aucun espace" in out or "cli.no_workspace" in out):
        c = cli("workspace", "create", "--name", a.workspace_name, capture=True)
        print(c.stdout, end="")
        if c.returncode != 0:
            die("création de l'espace impossible : " + (c.stderr or "").strip()[-300:])
        print("\n   >>> COPIEZ le jeton propriétaire ci-dessus : il ne sera PLUS affiché (il sert à vous connecter à l'interface, écran /access).")
        r = cli("knowledge", "kb-list", capture=True)
        out = (r.stdout or "") + (r.stderr or "")
    elif r.returncode != 0:
        die("lecture de l'espace impossible : " + out.strip()[-400:])
    else:
        print("   un espace existe déjà (son jeton n'est pas réaffiché : c'est celui noté lors de sa création).")

    step(2, total, f"Base « {cc} »")
    if re.search(rf"^{re.escape(cc)}\s", out, re.M):
        print(f"   la base {cc} existe déjà : conservée.")
    else:
        if cli("knowledge", "kb-create", "--code", cc, "--name", cc, "--scope-kind", a.scope_kind).returncode != 0:
            die(f"création de la base {cc} impossible.")

    step(3, total, "Copie des PDF dans le stockage (la source reste intacte)")
    scope_dir = f"organizations/{cc}" if a.scope_kind == "organization" else cc
    if cli("knowledge", "sources-migrate", "--map", f"{scope_dir}={src}", "--apply", "--manifest", str(manifest)).returncode != 0:
        die("copie des PDF impossible.")

    step(4, total, "Enregistrement des documents")
    if cli("knowledge", "adopt", "--country", cc, "--manifest", str(manifest)).returncode != 0:
        die("enregistrement des documents impossible.")

    step(5, total, "Métadonnées d'auteur (titres, types, fiabilité)")
    cu = cli("knowledge", "curate", "--country", cc, "--curation", str(cur), "--manifest", str(manifest))
    if cu.returncode != 0:
        if not a.allow_partial:
            die("des documents attendus par le fichier de curation sont ABSENTS du dossier source (lignes « non appliqué … not_in_manifest » "
                "ci-dessus) : la base serait incomplète. Complétez le dossier avec TOUS les PDF fournis par l'équipe, ou, pour un simple essai "
                "sur un échantillon, ajoutez --allow-partial. (Les documents déjà copiés sont conservés ; relancer est sans danger.)")
        print("   AVERTISSEMENT : base PARTIELLE (--allow-partial) : à ne pas présenter comme complète.")

    step(6, total, "Construction : extraction/OCR, découpage, vecteurs, index, cohérence (long : plusieurs minutes à plusieurs heures sur CPU)")
    b = cli("knowledge", "build", "--country", cc, "--steps", "process,embed,index,check")
    if b.returncode != 0:
        print("\n   La construction s'est arrêtée avant la fin. Relancez la MÊME commande : elle reprend là où elle s'est arrêtée "
              "(`ReadTimeout` : augmentez ALERTE_EMBED_TIMEOUT_S et baissez ALERTE_EMBED_BATCH_SIZE dans backend/.env).")

    step(7, total, "État final")
    cli("knowledge", "status", "--country", cc)
    ck = cli("knowledge", "check", "--country", cc)

    step(8, total, "Publication")
    if b.returncode != 0 or ck.returncode != 0:
        print("   NON publiée : la base n'est pas complète (voir ci-dessus). Corrigez puis relancez.")
        return 2
    if a.publish:
        if cli("knowledge", "publish", "--country", cc, "--note", a.note).returncode != 0:
            print("   Publication REFUSÉE (vecteurs incomplets ou documents en échec) : voir le message ci-dessus.")
            return 3
        print(f"\nBase {cc} construite, vérifiée et publiée.")
    else:
        print(f"   Base complète et vérifiée. Pour la publier : python -m app.cli knowledge publish --country {cc} --note \"v1\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
