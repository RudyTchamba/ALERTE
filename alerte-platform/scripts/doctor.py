#!/usr/bin/env python3
"""Vérifie l'environnement (stdlib uniquement, Linux / Windows / macOS) et explique comment corriger.

Usage : python scripts/doctor.py [--backend-only] [--strict]
Code de sortie : 0 si aucun point BLOQUANT ; 1 sinon (avec --strict, les avertissements bloquent aussi).
"""
from __future__ import annotations

import argparse
import os
import platform
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
    code, out = run([exe, "--list-langs"])
    langs = set(out.split()[4:]) if code == 0 else set()
    missing = {"fra", "ara", "eng"} - langs
    tess = os.environ.get("ALERTE_TESSDATA_DIR")
    if missing and not tess:
        add("AVERTISSEMENT", f"Tesseract : langues manquantes {sorted(missing)}",
            "Installer les paquets de langues ou définir ALERTE_TESSDATA_DIR vers un dossier tessdata (ara, fra, eng).")
    else:
        add("OK", "Tesseract disponible", f"langues : {sorted(langs)}" if not missing else f"tessdata externe : {tess}")


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


def _reachable(url: str) -> bool:
    try:
        req = urllib.request.Request(url.rstrip("/") + "/models", method="GET")
        with urllib.request.urlopen(req, timeout=4) as r:  # noqa: S310 - URL d'administration locale
            return 200 <= r.status < 500
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except Exception:  # noqa: BLE001
        return False


def check_model_servers() -> None:
    for label, var in (("génération", "ALERTE_LLM_BASE_URL"), ("embeddings", "ALERTE_EMBED_BASE_URL")):
        url = os.environ.get(var)
        if not url:
            add("AVERTISSEMENT", f"Serveur de {label} non configuré ({var})",
                "Pointez vers une machine de l'équipe (Ollama/vLLM/TEI) pour les tests IA réels ; les tests unitaires n'en ont pas besoin.")
        else:
            add("OK" if _reachable(url) else "AVERTISSEMENT", f"Serveur de {label} : {url}",
                "" if _reachable(url) else "injoignable depuis cette machine")


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
