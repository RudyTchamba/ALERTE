#!/usr/bin/env python3
"""Démontre, sur une COPIE ISOLÉE, qu'une altération du ledger est détectée. Ne touche JAMAIS à la base d'origine.

    python scripts/ledger_tamper_demo.py --data-dir ./data-demo --exercise <id_exercice>

Étapes : copie de la base SQLite (API `backup`) dans un dossier temporaire → modification d'UNE ligne de `ledger_event` dans la copie →
démarrage d'une instance de l'application sur la copie → vérification du ledger (attendu : `ok=false`, première entrée altérée) ;
puis vérification de la base d'origine (attendu : `ok=true`). Le jeton propriétaire est demandé par variable d'environnement
ALERTE_TOKEN (jamais en argument, jamais journalisé).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def verify(settings: Settings, exercise: str, token: str) -> dict:
    with TestClient(create_app(settings)) as c:
        r = c.get(f"/api/v1/exercises/{exercise}/ledger/verify", headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--exercise", required=True)
    ap.add_argument("--seq", type=int, default=None, help="n° de l'entrée à altérer (défaut : première décision)")
    a = ap.parse_args()
    token = os.environ.get("ALERTE_TOKEN")
    if not token:
        sys.exit("définissez ALERTE_TOKEN (jeton propriétaire ou auditeur)")
    src = Path(a.data_dir).resolve() / "db" / "alerte.sqlite"
    if not src.exists():
        sys.exit(f"base introuvable : {src}")
    tmp = Path(tempfile.mkdtemp(prefix="alerte-tamper-"))
    (tmp / "db").mkdir()
    s, d = sqlite3.connect(src), sqlite3.connect(tmp / "db" / "alerte.sqlite")
    s.backup(d)
    s.close()
    if a.seq:
        row = d.execute("SELECT seq, payload FROM ledger_event WHERE exercise_id=? AND seq=?", (a.exercise, a.seq)).fetchone()
    else:
        row = d.execute("SELECT seq, payload FROM ledger_event WHERE exercise_id=? AND type='DECISION' ORDER BY seq LIMIT 1",
                        (a.exercise,)).fetchone()
    if not row:
        sys.exit("aucune entrée à altérer")
    content = json.loads(row[1])
    content["falsifie"] = True  # changement de CONTENU (un simple espace ne change pas les octets canoniques)
    d.execute("UPDATE ledger_event SET payload=? WHERE exercise_id=? AND seq=?", (json.dumps(content), a.exercise, row[0]))
    d.commit()
    d.close()
    cfg = dict(log_json=False, log_level="ERROR", llm_mode="scripted", embed_provider="fixture")
    print(f"copie altérée : {tmp} (entrée n° {row[0]} modifiée)")
    print("COPIE   :", verify(Settings(data_dir=tmp, **cfg), a.exercise, token))
    print("ORIGINAL:", verify(Settings(data_dir=Path(a.data_dir), **cfg), a.exercise, token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
