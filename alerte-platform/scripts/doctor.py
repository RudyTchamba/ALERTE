#!/usr/bin/env python3
"""Vérifie l'environnement (stdlib uniquement, Linux / Windows / macOS) et explique comment corriger.

Usage : python scripts/doctor.py [--backend-only] [--strict]
Code de sortie : 0 si aucun point BLOQUANT ; 1 sinon (avec --strict, les avertissements bloquent aussi).
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
OS = platform.system()  # Linux | Darwin | Windows
results: list[tuple[str, str, str]] = []  # (niveau, titre, détail)


def add(level: str, title: str, detail: str = "") -> None:
    results.append((level, title, detail))


def load_dotenv() -> None:
    """Lit `backend/.env` (clé=valeur, commentaires ignorés) SANS écraser l'environnement existant, comme le fait le backend."""
    f = BACKEND / ".env"
    if not f.is_file():
        return
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.split(" #")[0].strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def venv_python() -> Path:
    return BACKEND / ".venv" / ("Scripts/python.exe" if OS == "Windows" else "bin/python")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def hint(linux: str, mac: str, win: str) -> str:
    return {"Linux": linux, "Darwin": mac, "Windows": win}.get(OS, linux)


def check_python() -> None:
    v = sys.version_info
    if v < (3, 11):
        add("BLOQUANT", f"Python {v.major}.{v.minor} trop ancien", "Python 3.11+ requis (3.12 recommandé).")
    else:
        add("OK", f"Python {v.major}.{v.minor}.{v.micro}")
    vp = venv_python()
    if vp.exists():
        code, out = run([str(vp), "-c", "import fastapi, sqlalchemy, chromadb; print('ok')"])
        add("OK" if code == 0 else "BLOQUANT", "Environnement virtuel backend/.venv" + ("" if code == 0 else " incomplet"),
            "" if code == 0 else "Relancer : python scripts/setup.py")
    else:
        add("BLOQUANT", "Environnement virtuel absent (backend/.venv)", "Créer : python scripts/setup.py")


def check_node() -> None:
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        nvm_dir = Path(os.environ.get("NVM_DIR", Path.home() / ".nvm")) / "versions" / "node"
        found = sorted(nvm_dir.glob("v*")) if nvm_dir.is_dir() else []
        if found:
            add("AVERTISSEMENT", "Node.js installé via nvm mais non activé dans ce shell",
                f"versions trouvées : {', '.join(p.name for p in found)}. Activez-la : `nvm use` (dans frontend/, lit .nvmrc).")
        else:
            add("AVERTISSEMENT", "Node.js/npm introuvables dans le PATH",
                "Installez/activez Node 22 avec nvm : `nvm install && nvm use` (le fichier .nvmrc fixe la version). "
                + hint("", "", "Windows : nvm-windows ou fnm."))
        return
    code, out = run([node, "--version"])
    ver = out.lstrip("v").split(".")
    ok = code == 0 and ((int(ver[0]) == 22 and int(ver[1]) >= 12) or int(ver[0]) >= 23 or (int(ver[0]) == 20 and int(ver[1]) >= 19))
    add("OK" if ok else "BLOQUANT", f"Node {out}", "" if ok else "Vite 8 exige Node ≥ 20.19 ou ≥ 22.12 : `nvm use`.")
    if (FRONTEND / "package.json").exists() and not (FRONTEND / "node_modules").exists():
        add("AVERTISSEMENT", "Dépendances frontend non installées", "cd frontend && npm ci")


def check_tesseract() -> None:
    exe = shutil.which("tesseract")
    if not exe:
        add("AVERTISSEMENT", "Tesseract OCR introuvable (OCR des PDF scannés désactivé)",
            hint("sudo apt install tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara", "brew install tesseract tesseract-lang",
                 "Installeur UB Mannheim, puis ajouter au PATH et définir TESSDATA_PREFIX"))
        return
    tess = os.environ.get("ALERTE_TESSDATA_DIR")
    if tess and not Path(tess).is_absolute():
        cands = [Path.cwd() / tess, BACKEND / tess, ROOT / tess, ROOT.parent / tess]
        found = next((c for c in cands if c.is_dir()), None)
        add("AVERTISSEMENT", f"ALERTE_TESSDATA_DIR est un chemin RELATIF ({tess}) : il dépend du dossier de lancement",
            (f"Il n'existe que depuis {'le dossier courant' if found == cands[0] else 'un autre dossier'} ({found}). " if found else "Introuvable depuis ce dossier. ")
            + "Utilisez un chemin ABSOLU (le backend est lancé depuis backend/).")
        tess = str(found) if found else tess
    cmd = [exe, "--list-langs"] + (["--tessdata-dir", tess] if tess else [])
    code, out = run(cmd)
    langs = {ln.strip() for ln in out.splitlines() if re.fullmatch(r"[A-Za-z_]{2,12}", ln.strip())} if code == 0 else set()
    missing = {"fra", "ara", "eng"} - langs
    if missing:
        add("AVERTISSEMENT", f"Tesseract : langues manquantes {sorted(missing)}",
            "Installer les paquets de langues ou définir ALERTE_TESSDATA_DIR vers un dossier tessdata (ara, fra, eng).")
    else:
        add("OK", "Tesseract disponible", f"langues : {sorted(langs)}" + (f" (tessdata : {tess})" if tess else ""))


def check_pdf() -> None:
    vp = venv_python()
    if not vp.exists():
        return
    code, out = run([str(vp), "-c", "import weasyprint; print(weasyprint.__version__)"])
    if code == 0:
        add("OK", f"WeasyPrint {out}")
    else:
        add("AVERTISSEMENT", "WeasyPrint indisponible (bibliothèque Pango manquante ?)",
            hint("sudo apt install libpango-1.0-0 libpangoft2-1.0-0", "brew install pango",
                 "Installer GTK/Pango via MSYS2 (voir docs/runbooks/install.md) — ou utiliser le rendu de repli"))


def _served_models(url: str, key: str = "") -> tuple[bool, list[str], str]:
    """GET <url>/models : (joignable, identifiants des modèles servis, détail d'erreur). Ollama et vLLM répondent tous deux ainsi."""
    import json
    req = urllib.request.Request(url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req, timeout=6) as r:  # noqa: S310 - URL d'administration configurée par l'utilisateur
            data = json.load(r)
        return True, [str(m.get("id")) for m in data.get("data", [])], ""
    except urllib.error.HTTPError as exc:
        return exc.code < 500 and exc.code not in (401, 403), [], f"HTTP {exc.code}" + (" : clé d'API manquante ou invalide ?" if exc.code in (401, 403) else "")
    except Exception as exc:  # noqa: BLE001
        return False, [], exc.__class__.__name__


def _check_one_model_server(label: str, url_var: str, model_var: str, key_var: str, needed_for: str) -> None:
    url, model = os.environ.get(url_var), os.environ.get(model_var)
    if not url:
        add("AVERTISSEMENT", f"Serveur de {label} non configuré ({url_var})",
            f"Requis pour {needed_for}. Exemple : {url_var}=http://localhost:11434/v1 (Ollama) — voir .env.example.")
        return
    if not model:
        add("AVERTISSEMENT", f"Modèle de {label} non configuré ({model_var})", f"Requis pour {needed_for}. Nom EXACT du modèle servi (voir `ollama list`).")
    up, served, err = _served_models(url, os.environ.get(key_var, ""))
    if not up:
        add("AVERTISSEMENT", f"Serveur de {label} injoignable : {url}", f"{err}. Vérifiez l'adresse, le port, le pare-feu / tunnel SSH. Test : curl {url.rstrip('/')}/models")
    elif model and served and model not in served and f"{model}:latest" not in served:  # Ollama : « bge-m3 » = « bge-m3:latest »
        add("BLOQUANT" if label == "génération" else "AVERTISSEMENT", f"Serveur de {label} joignable, mais le modèle « {model} » n'y est pas servi",
            f"Modèles servis : {', '.join(served) or '(aucun)'}. Corrigez {model_var} (nom exact, Ollama : « nom:tag ») ou installez le modèle.")
    else:
        add("OK", f"Serveur de {label} : {url}", f"modèle « {model} » servi" if model and served else (err or "joignable"))


def check_model_servers() -> None:
    mode = os.environ.get("ALERTE_LLM_MODE", "openai_compat")
    if mode == "openai_compat":
        _check_one_model_server("génération", "ALERTE_LLM_BASE_URL", "ALERTE_LLM_MODEL", "ALERTE_LLM_API_KEY", "un exercice « Modèle réel »")
    else:
        add("INFO", f"ALERTE_LLM_MODE={mode} : exercices SANS IA ; aucun serveur de génération n'est vérifié")
    _check_one_model_server("embeddings", "ALERTE_EMBED_BASE_URL", "ALERTE_EMBED_MODEL", "ALERTE_EMBED_API_KEY",
                            "construire une base avec vecteurs et la recherche hybride")
    cap = os.environ.get("ALERTE_MAX_LLM_CALLS", "199")
    add("INFO", f"Plafond d'appels par défaut : {cap} (le budget de l'exercice, fixé dans le formulaire, prime)")


def check_data_dir() -> None:
    d = Path(os.environ.get("ALERTE_DATA_DIR", BACKEND / "data")).expanduser()
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".doctor"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        free = shutil.disk_usage(d).free // (1 << 30)
        add("OK" if free >= 5 else "AVERTISSEMENT", f"Dossier de données {d} inscriptible, {free} Go libres")
    except OSError as exc:
        add("BLOQUANT", f"Dossier de données {d} non inscriptible", str(exc))


def check_containers() -> None:
    eng = shutil.which("docker") or shutil.which("podman")
    add("OK" if eng else "INFO", f"Docker/Podman : {'présent (' + Path(eng).name + ')' if eng else 'absent (optionnel)'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend-only", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    load_dotenv()
    add("INFO", f"Système : {OS} {platform.release()} — {platform.machine()}")
    check_python()
    if not args.backend_only:
        check_node()
    check_tesseract()
    check_pdf()
    check_model_servers()
    check_data_dir()
    check_containers()
    icons = {"OK": "✔", "INFO": "·", "AVERTISSEMENT": "!", "BLOQUANT": "✘"}
    for level, title, detail in results:
        print(f"[{icons[level]}] {level:<13} {title}" + (f"\n      → {detail}" if detail else ""))
    blockers = [r for r in results if r[0] == "BLOQUANT" or (args.strict and r[0] == "AVERTISSEMENT")]
    print(f"\n{len(blockers)} point(s) bloquant(s).")
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
