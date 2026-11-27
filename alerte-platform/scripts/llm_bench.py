#!/usr/bin/env python3
"""Mesure de latence d'un serveur de génération compatible OpenAI (Ollama, vLLM…) avec une charge ressemblant à une activation d'agent ALERTE.

Sert au DIMENSIONNEMENT : combien de secondes par appel sur CETTE machine, avec CE modèle ? Aucune dépendance (bibliothèque standard).

    python scripts/llm_bench.py --url http://localhost:11434/v1 --model qwen2.5:1.5b-instruct                  # 3 appels, prompt ~3 500 jetons
    python scripts/llm_bench.py --url http://localhost:8001/v1 --model <nom> --key <clé> --calls 5 --parallel 2   # 2 requêtes simultanées

Ce qui est mesuré : durée de chaque appel, jetons d'entrée/sortie rapportés par le serveur (`usage`), débit de génération approximatif.
Ce qui NE l'est PAS : la qualité des réponses (voir le protocole d'évaluation) ni l'effet d'un contexte tronqué par le serveur : si
`prompt_tokens` est très inférieur à la cible, le serveur a coupé le prompt (Ollama : OLLAMA_CONTEXT_LENGTH trop bas).
La clé d'API, si fournie, n'est jamais affichée ni écrite. Le rapport (--out) ne contient ni URL ni clé.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request

FILLER = ("Article {n}. L'autorité compétente coordonne l'information du public, transmet les alertes validées aux opérateurs et rend compte "
          "de ses décisions au comité de crise ; les communes relaient localement les consignes et ouvrent des abris. ")


def build_prompt(target_tokens: int) -> str:
    # ~4 caractères par jeton en français : approximation, la valeur réelle est lue dans `usage.prompt_tokens`
    out, n = [], 0
    while sum(map(len, out)) < target_tokens * 4:
        n += 1
        out.append(FILLER.format(n=n))
    return "".join(out)


def one_call(url: str, model: str, key: str, prompt: str, max_tokens: int, timeout: float) -> dict:
    body = {"model": model, "temperature": 0.0, "stream": False, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": "You are an institutional agent. Reply with one JSON object."},
                         {"role": "user", "content": prompt + "\n\nGive your next action as one flat JSON object."}]}
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {key}"} if key else {})})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - URL fournie par l'utilisateur
            data = json.load(r)
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}", "s": time.monotonic() - t0}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": e.__class__.__name__, "s": time.monotonic() - t0}
    u = data.get("usage") or {}
    return {"ok": True, "s": time.monotonic() - t0, "in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", required=True, help="URL de base en /v1")
    ap.add_argument("--model", required=True, help="nom EXACT du modèle servi")
    ap.add_argument("--key", default="", help="clé d'API (jamais affichée)")
    ap.add_argument("--calls", type=int, default=3)
    ap.add_argument("--parallel", type=int, default=1, help="requêtes simultanées (le moteur d'ALERTE en émet 1 par exercice en cours, 2 exercices au plus)")
    ap.add_argument("--prompt-tokens", type=int, default=3500, help="taille visée du prompt (un prompt d'agent ALERTE ≈ 3 000 à 4 000 jetons)")
    ap.add_argument("--max-tokens", type=int, default=300, help="jetons générés au plus (une décision ≈ 200 à 400)")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--out", default="", help="écrire le rapport JSON (sans URL ni clé)")
    a = ap.parse_args()
    prompt = build_prompt(a.prompt_tokens)
    print(f"Mesure : {a.calls} appels, {a.parallel} en parallèle, prompt ≈ {a.prompt_tokens} jetons, ≤ {a.max_tokens} jetons générés")
    print("Appel de chauffe (chargement du modèle, exclu des statistiques)…", flush=True)
    warm = one_call(a.url, a.model, a.key, "ping", 8, a.timeout)
    if not warm["ok"]:
        print(f"ÉCHEC dès la chauffe : {warm['error']} (modèle absent ? nom exact : voir `ollama list` ou GET /v1/models)")
        return 1
    print(f"  chauffe : {warm['s']:.1f} s")
    results: list[dict] = []
    lock = threading.Lock()
    todo = list(range(a.calls))

    def worker() -> None:
        while True:
            with lock:
                if not todo:
                    return
                todo.pop()
            r = one_call(a.url, a.model, a.key, prompt, a.max_tokens, a.timeout)
            with lock:
                results.append(r)
                print(f"  appel {len(results)}/{a.calls} : {r['s']:.1f} s" + ("" if r["ok"] else f" ÉCHEC {r['error']}"), flush=True)

    t0 = time.monotonic()
    threads = [threading.Thread(target=worker) for _ in range(max(1, a.parallel))]
    [t.start() for t in threads]
    [t.join() for t in threads]
    wall = time.monotonic() - t0
    ok = [r for r in results if r["ok"]]
    if not ok:
        print("Aucun appel réussi.")
        return 1
    secs = sorted(r["s"] for r in ok)
    rep = {"calls_ok": len(ok), "calls_failed": len(results) - len(ok), "parallel": a.parallel, "wall_s": round(wall, 1),
           "median_s": round(statistics.median(secs), 1), "max_s": round(secs[-1], 1),
           "prompt_tokens_median": int(statistics.median(r["in"] for r in ok)), "completion_tokens_median": int(statistics.median(r["out"] for r in ok)),
           "throughput_calls_per_min": round(len(ok) / wall * 60, 2)}
    print("\nRésultat :")
    for k, v in rep.items():
        print(f"  {k}: {v}")
    if rep["prompt_tokens_median"] < a.prompt_tokens * 0.6:
        print(f"\nATTENTION : le serveur n'a compté que {rep['prompt_tokens_median']} jetons d'entrée pour ≈ {a.prompt_tokens} envoyés : "
              "le prompt a probablement été TRONQUÉ (contexte trop petit : Ollama → OLLAMA_CONTEXT_LENGTH=8192).")
    est = rep["median_s"]
    print(f"\nOrdre de grandeur (sans parallélisme) : un exercice de 150 appels ≈ {150 * est / 60:.0f} min ; de 300 appels ≈ {300 * est / 60:.0f} min.")
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"model": a.model, **rep}, f, indent=2)
        print(f"Rapport écrit : {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
