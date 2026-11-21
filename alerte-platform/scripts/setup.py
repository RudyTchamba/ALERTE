#!/usr/bin/env python3
"""Installation reproductible (stdlib, Linux / Windows / macOS) : venv backend + dépendances + frontend.

Usage : python scripts/setup.py [--python python3.12] [--skip-frontend] [--dev]
* Backend : crée `backend/.venv` et installe `requirements-dev.txt` avec `python -m pip` (jamais de pip global, jamais sudo).
* Frontend : `npm ci` avec le Node actif (nvm : `nvm use` lit .nvmrc) ; jamais sudo.
"""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
IS_WIN = platform.system() == "Windows"


def sh(cmd: list[str], cwd: Path | None = None) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python", default=sys.executable, help="interpréteur utilisé pour créer le venv (3.11+)")
    ap.add_argument("--skip-frontend", action="store_true")
    ap.add_argument("--prod", action="store_true", help="n'installe pas les dépendances de développement")
    args = ap.parse_args()

    py = Path(args.python)
    out = subprocess.run([str(py), "-c", "import sys; print(sys.version_info[:2] >= (3, 11))"], capture_output=True, text=True)
    if out.stdout.strip() != "True":
        print("Python 3.11+ requis (3.12 recommandé) : utilisez --python /chemin/vers/python3.12", file=sys.stderr)
        return 2

    venv = BACKEND / ".venv"
    if not venv.exists():
        sh([str(py), "-m", "venv", str(venv)])
    vpy = venv / ("Scripts/python.exe" if IS_WIN else "bin/python")
    sh([str(vpy), "-m", "pip", "install", "--upgrade", "pip"])
    req = "requirements.txt" if args.prod else "requirements-dev.txt"
    sh([str(vpy), "-m", "pip", "install", "-r", req], cwd=BACKEND)

    env_file, example = BACKEND / ".env", ROOT / ".env.example"
    if not env_file.exists() and example.exists():
        shutil.copyfile(example, env_file)
        print(f"Créé {env_file} depuis .env.example (à adapter ; jamais commité).")

    if not args.skip_frontend:
        npm = shutil.which("npm")
        if not npm:
            print("npm introuvable : activez Node 22 (`nvm install && nvm use`) puis relancez, ou utilisez --skip-frontend.")
        else:
            sh([npm, "ci"], cwd=FRONTEND)

    print("\nInstallation terminée. Vérification : python scripts/doctor.py")
    print("Lancement développement : python scripts/dev.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
