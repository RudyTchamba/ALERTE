#!/usr/bin/env python3
"""Lance le backend (uvicorn) et, sauf --no-frontend, le frontend Vite. Multiplateforme ; Ctrl-C arrête les deux.

Usage : python scripts/dev.py [--port 8000] [--no-frontend] [--host] [--data-dir ./backend/data]

`--host` expose le frontend sur le réseau local (téléphones des joueurs : QR code « faire jouer le public ») ;
le backend reste sur localhost, joint via le proxy de Vite.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND, FRONTEND = ROOT / "backend", ROOT / "frontend"
IS_WIN = platform.system() == "Windows"


def lan_ip() -> str:
    """Adresse de cette machine sur le réseau local (celle de la route par défaut)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-frontend", action="store_true")
    ap.add_argument("--host", action="store_true", help="expose le frontend sur le réseau local (téléphones)")
    ap.add_argument("--data-dir", default=str(BACKEND / "data"))
    args = ap.parse_args()

    vpy = BACKEND / ".venv" / ("Scripts/python.exe" if IS_WIN else "bin/python")
    if not vpy.exists():
        print("venv absent : lancez d'abord `python scripts/setup.py`", file=sys.stderr)
        return 2
    env = {**os.environ, "ALERTE_DATA_DIR": args.data_dir, "PYTHONUTF8": "1"}
    flags = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
    procs: list[subprocess.Popen] = []
    # --timeout-graceful-shutdown : les flux SSE ouverts (salles de simulation) ne bloquent plus le rechargement automatique.
    procs.append(subprocess.Popen([str(vpy), "-m", "uvicorn", "app.main:app_factory", "--factory", "--reload",
                                   "--timeout-graceful-shutdown", "3", "--port", str(args.port)], cwd=BACKEND, env=env, **flags))
    if not args.no_frontend:
        npm = shutil.which("npm")
        if npm:
            vite = [npm, "run", "dev"] + (["--", "--host"] if args.host else [])
            procs.append(subprocess.Popen(vite, cwd=FRONTEND, env=env, **flags))
        else:
            print("npm introuvable : frontend non lancé (activez Node avec nvm).")
    print(f"API : http://localhost:{args.port}/api/v1/docs   |   Frontend : http://localhost:5173")
    if args.host:
        print(f"Réseau local (téléphones) : http://{lan_ip()}:5173  — ouvrez l'interface via cette adresse pour que les QR codes fonctionnent")

    def stop(*_a) -> None:
        for p in procs:
            if p.poll() is None:
                try:
                    p.send_signal(signal.CTRL_BREAK_EVENT if IS_WIN else signal.SIGTERM)
                except OSError:
                    p.terminate()

    signal.signal(signal.SIGINT, lambda *a: stop())
    try:
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
