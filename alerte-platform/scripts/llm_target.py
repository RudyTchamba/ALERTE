#!/usr/bin/env python3
"""Bascule le modèle de GÉNÉRATION d'ALERTE entre le serveur local (Ollama) et un serveur distant (AWS, vLLM).

Les embeddings (recherche) ne changent jamais : ils restent locaux. Rien n'est supprimé : les deux configurations
sont gardées dans backend/.env sous forme de préréglages, et chaque bascule fait une copie de sauvegarde du fichier.

    python3 scripts/llm_target.py status                    # configuration active + test des deux serveurs
    python3 scripts/llm_target.py init-aws --url http://localhost:8001/v1 --model Qwen/Qwen2.5-32B-Instruct-AWQ --key <clé>
    python3 scripts/llm_target.py aws                       # bascule vers AWS (refuse si le serveur ne répond pas)
    python3 scripts/llm_target.py local                     # revient au modèle local

Après une bascule, redémarrer le backend (Ctrl+C puis `python3 scripts/dev.py --host`).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(os.environ.get("ALERTE_ENV_FILE") or Path(__file__).resolve().parents[1] / "backend" / ".env")
ACTIVE = ("ALERTE_LLM_BASE_URL", "ALERTE_LLM_MODEL", "ALERTE_LLM_API_KEY")
FIELDS = ("BASE_URL", "MODEL", "API_KEY")


def read() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.*)$", line)
        if m:
            out[m.group(1)] = re.sub(r"\s+#.*$", "", m.group(2)).strip()
    return out


def write(values: dict[str, str]) -> None:
    """Met à jour les variables données en conservant le reste du fichier (commentaires compris)."""
    lines = ENV.read_text(encoding="utf-8").splitlines()
    done: set[str] = set()
    # 1) les lignes ACTIVES d'abord (dotenv garde la dernière : une ligne commentée remplacée ne suffirait pas)
    for pattern in (r"^\s*([A-Z0-9_]+)\s*=", r"^\s*#\s*([A-Z0-9_]+)\s*="):
        for i, line in enumerate(lines):
            m = re.match(pattern, line)
            if m and m.group(1) in values and m.group(1) not in done:
                lines[i] = f"{m.group(1)}={values[m.group(1)]}"
                done.add(m.group(1))
    # 2) toute autre ligne active en double pour ces variables est commentée (une seule valeur fait foi)
    seen: set[str] = set()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=", line)
        if m and m.group(1) in values:
            if m.group(1) in seen:
                lines[i] = "# (doublon désactivé) " + line
            seen.add(m.group(1))
    lines += [f"{k}={v}" for k, v in values.items() if k not in done]
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def backup() -> Path:
    dst = ENV.with_name(f".env.bak-{dt.datetime.now():%Y%m%d-%H%M%S-%f}")
    shutil.copy2(ENV, dst)
    dst.chmod(0o600)
    return dst


def preset(env: dict[str, str], name: str) -> dict[str, str]:
    return {f: env.get(f"ALERTE_LLM_{name}_{f}", "") for f in FIELDS}


def probe(url: str, key: str, model: str) -> str:
    """Interroge GET <url>/models : « ok », « modèle absent » ou la cause de l'échec."""
    if not url:
        return "non configuré"
    req = urllib.request.Request(url.rstrip("/") + "/models", headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            ids = [m.get("id") for m in json.load(r).get("data", [])]
    except urllib.error.HTTPError as e:
        return f"refusé (HTTP {e.code}{' : clé invalide ?' if e.code in (401, 403) else ''})"
    except Exception as e:  # noqa: BLE001
        return f"injoignable ({e.__class__.__name__})"
    return "ok" if (not model or model in ids) else f"joignable, mais modèle « {model} » absent (servis : {', '.join(map(str, ids))})"


def which(env: dict[str, str]) -> str:
    cur = {f: env.get(a, "") for f, a in zip(FIELDS, ACTIVE, strict=True)}
    for name in ("LOCAL", "AWS"):
        p = preset(env, name)
        if p["BASE_URL"] and p["BASE_URL"] == cur["BASE_URL"] and p["MODEL"] == cur["MODEL"]:
            return name.lower()
    return "personnalisé"


def ensure_local_preset(env: dict[str, str]) -> dict[str, str]:
    """À la première utilisation, la configuration active (locale) devient le préréglage LOCAL."""
    if not env.get("ALERTE_LLM_LOCAL_BASE_URL"):
        backup()
        write({f"ALERTE_LLM_LOCAL_{f}": env.get(a, "") for f, a in zip(FIELDS, ACTIVE, strict=True)})
        env = read()
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("local")
    a = sub.add_parser("aws")
    a.add_argument("--force", action="store_true", help="basculer même si le serveur AWS ne répond pas")
    i = sub.add_parser("init-aws")
    i.add_argument("--url", required=True, help="ex. http://localhost:8001/v1 (tunnel SSH)")
    i.add_argument("--model", required=True)
    i.add_argument("--key", required=True, help="clé d'API définie sur le serveur vLLM")
    args = ap.parse_args()
    if not ENV.is_file():
        sys.exit(f"{ENV} introuvable : lancer d'abord scripts/setup.py")
    env = ensure_local_preset(read())

    if args.cmd == "init-aws":
        if "://" not in args.url or not args.url.rstrip("/").endswith("/v1"):
            sys.exit("--url doit être une URL se terminant par /v1 (ex. http://localhost:8001/v1)")
        b = backup()
        write({"ALERTE_LLM_AWS_BASE_URL": args.url, "ALERTE_LLM_AWS_MODEL": args.model, "ALERTE_LLM_AWS_API_KEY": args.key})
        print(f"préréglage AWS enregistré (sauvegarde : {b.name}). Test : {probe(args.url, args.key, args.model)}")
        return 0

    if args.cmd == "status":
        print(f"configuration active : {which(env)} — {env.get('ALERTE_LLM_MODEL')} @ {env.get('ALERTE_LLM_BASE_URL')}")
        for name in ("LOCAL", "AWS"):
            p = preset(env, name)
            print(f"  {name.lower():5} : {p['MODEL'] or '—'} @ {p['BASE_URL'] or '—'} → {probe(p['BASE_URL'], p['API_KEY'], p['MODEL'])}")
        print("embeddings (inchangés) :", env.get("ALERTE_EMBED_MODEL"), "@", env.get("ALERTE_EMBED_BASE_URL"))
        return 0

    target = args.cmd.upper()
    p = preset(env, target)
    if not p["BASE_URL"]:
        sys.exit("préréglage AWS absent : lancer d'abord `init-aws`" if target == "AWS" else "préréglage LOCAL absent")
    state = probe(p["BASE_URL"], p["API_KEY"], p["MODEL"])
    if state != "ok" and not getattr(args, "force", False):
        sys.exit(f"serveur {target.lower()} : {state}. Rien n'a été modifié (ajouter --force pour basculer quand même).")
    b = backup()
    write(dict(zip(ACTIVE, (p["BASE_URL"], p["MODEL"], p["API_KEY"]), strict=True)))
    print(f"modèle actif : {target.lower()} — {p['MODEL']} @ {p['BASE_URL']} (serveur : {state}; sauvegarde : {b.name})")
    print("→ redémarrer le backend pour appliquer : Ctrl+C dans le terminal de dev.py, puis `python3 scripts/dev.py --host`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
