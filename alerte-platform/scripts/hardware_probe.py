#!/usr/bin/env python3
"""Sonde matérielle d'ALERTE : Linux, Windows, macOS. Bibliothèque standard uniquement (Python 3.9+), aucune installation.

Sert à décider QUELLE machine hébergera les modèles d'IA (génération, embeddings), avant de choisir un modèle ou une
instance AWS. Elle ne mesure aucune performance : elle relève des FAITS (système, CPU, RAM, GPU, VRAM, disque, outils).

    python scripts/hardware_probe.py                      # affiche le rapport et écrit alerte-hardware-<OS>.txt/.json
    python scripts/hardware_probe.py --out C:\\temp        # choisir le dossier de sortie
    python scripts/hardware_probe.py --label linux-rudy    # étiquette libre (sans donnée personnelle) dans le nom de fichier

Confidentialité : le rapport ne contient NI nom de machine, NI nom d'utilisateur, NI adresse IP/MAC, NI chemin personnel,
NI variable d'environnement, NI clé. Relisez-le avant de le partager. Aucune connexion réseau n'est ouverte, sauf un GET
local sur http://localhost:11434 (Ollama) pour lister les NOMS des modèles installés. La sonde ne modifie rien.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

OS = platform.system()  # Linux | Darwin | Windows
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace",
                           creationflags=NO_WINDOW)
        return p.returncode, (p.stdout + ("\n" + p.stderr if p.returncode else "")).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def powershell(script: str) -> tuple[int, str]:
    exe = shutil.which("powershell") or shutil.which("pwsh")
    if not exe:
        return 1, "PowerShell introuvable"
    return run([exe, "-NoProfile", "-NonInteractive", "-Command", script], timeout=40)


# ------------------------------------------------------------------ CPU / RAM / disque

def cpu_info() -> dict:
    info: dict = {"model": platform.processor() or "inconnu", "logical_cores": None, "physical_cores": None}
    try:
        import os
        info["logical_cores"] = os.cpu_count()
    except Exception:  # noqa: BLE001
        pass
    if OS == "Linux":
        try:
            txt = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^model name\s*:\s*(.+)$", txt, re.M)
            if m:
                info["model"] = m.group(1).strip()
            ids = set(re.findall(r"^physical id\s*:\s*(\d+)$", txt, re.M))
            cores = re.findall(r"^cpu cores\s*:\s*(\d+)$", txt, re.M)
            if cores:
                info["physical_cores"] = int(cores[0]) * max(1, len(ids))
        except OSError:
            pass
    elif OS == "Darwin":
        c, out = run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if c == 0 and out:
            info["model"] = out
        c, out = run(["sysctl", "-n", "hw.physicalcpu"])
        if c == 0 and out.isdigit():
            info["physical_cores"] = int(out)
    elif OS == "Windows":
        c, out = powershell("Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores | ConvertTo-Json -Compress")
        if c == 0:
            try:
                d = json.loads(out)
                info["model"] = str(d.get("Name", info["model"])).strip()
                info["physical_cores"] = d.get("NumberOfCores")
            except ValueError:
                pass
    return info


def ram_info() -> dict:
    total = avail = None
    if OS == "Linux":
        try:
            txt = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
            t = re.search(r"^MemTotal:\s+(\d+) kB", txt, re.M)
            a = re.search(r"^MemAvailable:\s+(\d+) kB", txt, re.M)
            total = int(t.group(1)) * 1024 if t else None
            avail = int(a.group(1)) * 1024 if a else None
        except OSError:
            pass
    elif OS == "Darwin":
        c, out = run(["sysctl", "-n", "hw.memsize"])
        if c == 0 and out.isdigit():
            total = int(out)
    elif OS == "Windows":
        c, out = powershell("$o=Get-CimInstance Win32_OperatingSystem; "
                            "@{t=[int64]$o.TotalVisibleMemorySize*1024; a=[int64]$o.FreePhysicalMemory*1024} | ConvertTo-Json -Compress")
        if c == 0:
            try:
                d = json.loads(out)
                total, avail = int(d["t"]), int(d["a"])
            except (ValueError, KeyError, TypeError):
                pass
    gb = lambda v: round(v / 2**30, 1) if v else None  # noqa: E731
    return {"total_gb": gb(total), "available_now_gb": gb(avail)}


def disk_info() -> dict:
    here = Path.cwd()
    try:
        u = shutil.disk_usage(here)
        return {"checked_volume_free_gb": round(u.free / 2**30, 1), "checked_volume_total_gb": round(u.total / 2**30, 1),
                "note": "volume du dossier courant ; les modèles et la base vectorielle demandent de l'espace libre sur le volume de données"}
    except OSError as exc:
        return {"error": str(exc)}


# ------------------------------------------------------------------ GPU

def gpu_info() -> dict:
    out: dict = {"nvidia": [], "other": [], "notes": []}
    smi = shutil.which("nvidia-smi")
    if smi:
        c, txt = run([smi, "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"])
        if c == 0:
            for line in txt.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4 and parts[1].isdigit():
                    out["nvidia"].append({"name": parts[0], "vram_total_mib": int(parts[1]),
                                          "vram_free_mib": int(parts[2]) if parts[2].isdigit() else None, "driver": parts[3]})
        else:
            out["notes"].append("nvidia-smi présent mais en erreur : " + txt.splitlines()[0][:160])
        c, txt = run([smi])
        m = re.search(r"CUDA Version:\s*([\d.]+)", txt)
        if m:
            out["cuda_version_supported_by_driver"] = m.group(1)
    else:
        out["notes"].append("nvidia-smi absent : pas de GPU NVIDIA utilisable détecté (ou pilotes non installés)")
    if OS == "Linux":
        if shutil.which("rocm-smi"):
            out["other"].append({"name": "AMD ROCm détecté (rocm-smi présent)", "detail": "VRAM : lancer `rocm-smi --showmeminfo vram`"})
        if shutil.which("lspci"):
            c, txt = run(["lspci"])
            for ln in txt.splitlines():
                if re.search(r"VGA|3D controller|Display controller", ln):
                    out["other"].append({"name": re.sub(r"^\S+\s+", "", ln)[:140]})
    elif OS == "Windows":
        c, txt = powershell("Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion | ConvertTo-Json -Compress")
        if c == 0:
            try:
                data = json.loads(txt)
                for d in data if isinstance(data, list) else [data]:
                    ram = d.get("AdapterRAM")
                    out["other"].append({"name": d.get("Name"), "adapter_ram_gb_unreliable": round(ram / 2**30, 1) if ram else None,
                                         "note": "AdapterRAM plafonne à 4 Go (limite 32 bits) : fiez-vous à nvidia-smi pour la VRAM réelle"})
            except ValueError:
                pass
    elif OS == "Darwin":
        c, txt = run(["system_profiler", "SPDisplaysDataType"], timeout=40)
        for ln in txt.splitlines():
            if re.search(r"Chipset Model|VRAM|Metal", ln):
                out["other"].append({"name": ln.strip()[:140]})
        out["notes"].append("Apple Silicon : la mémoire est UNIFIÉE (partagée CPU/GPU) ; voir la RAM totale")
    return out


# ------------------------------------------------------------------ outils

def tool_version(cmd: list[str]) -> str | None:
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    c, out = run([exe] + cmd[1:])
    return out.splitlines()[0][:160] if out else ("présent" if c == 0 else "présent (version illisible)")


def tools_info() -> dict:
    t: dict = {
        "docker": tool_version(["docker", "--version"]),
        "docker_compose": None,
        "podman": tool_version(["podman", "--version"]),
        "ollama": tool_version(["ollama", "--version"]),
        "git": tool_version(["git", "--version"]),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "node": tool_version(["node", "--version"]),
        "tesseract": tool_version(["tesseract", "--version"]),
    }
    if t["docker"]:
        c, out = run(["docker", "compose", "version"])
        t["docker_compose"] = out.splitlines()[0][:100] if c == 0 and out else None
        c, out = run(["docker", "info", "--format", "{{json .Runtimes}}"], timeout=30)
        try:
            names = sorted(json.loads(out)) if c == 0 else None
        except ValueError:
            names = None
        t["docker_runtimes"] = ", ".join(names) if names else "docker info en erreur (démon arrêté ? droits ?)"
        t["docker_nvidia_runtime"] = ("oui" if "nvidia" in names else "non") if names else "inconnu"
    if OS == "Windows":
        c, out = run(["wsl", "--status"])
        t["wsl"] = "présent" if c == 0 else "absent ou non activé"
        if c == 0:
            c2, out2 = run(["wsl", "--list", "--verbose"])
            t["wsl_distributions"] = [re.sub(r"\s+", " ", ln.replace("\x00", "")).strip()
                                      for ln in out2.replace("\x00", "").splitlines()[1:] if ln.strip()][:6]
    if OS == "Linux":
        t["running_in_wsl"] = "oui" if "microsoft" in platform.release().lower() else "non"
    return t


def ollama_models() -> dict:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:  # noqa: S310 - local
            data = json.loads(r.read().decode("utf-8"))
        return {"reachable": True, "models": [{"name": m.get("name"), "size_gb": round(m.get("size", 0) / 2**30, 1)}
                                                for m in data.get("models", [])]}
    except Exception:  # noqa: BLE001
        return {"reachable": False, "models": []}


# ------------------------------------------------------------------ lecture indicative

def assess(report: dict) -> list[str]:
    """Constats indicatifs. Ce ne sont PAS des mesures de performance : voir docs/runbooks/dimensionnement-modeles.md."""
    notes: list[str] = []
    g = report["gpu"]["nvidia"]
    if g:
        total = sum(x["vram_total_mib"] for x in g) / 1024
        best = max(x["vram_total_mib"] for x in g) / 1024
        notes.append(f"GPU NVIDIA : {len(g)} carte(s), plus grosse VRAM {best:.0f} Go (cumul {total:.0f} Go).")
        notes.append("Les poids d'un modèle quantifié en 4 bits occupent très approximativement 0,55 Go par milliard de paramètres, "
                     "en 8 bits environ 1,05, en 16 bits environ 2 ; il faut AJOUTER le cache de contexte et une marge "
                     "(plusieurs Go). Estimation indicative, à confirmer par un essai.")
        if best < 12:
            notes.append("VRAM < 12 Go : seuls de petits modèles (≈ 7-8 B en 4 bits) sont envisageables ; contexte limité.")
    else:
        notes.append("Aucun GPU NVIDIA détecté : inférence sur CPU possible mais très lente avec des prompts de plusieurs milliers de "
                     "jetons (mesuré sur une machine à 4 cœurs : 15 à 33 s pour un modèle de 1,5 B) ; à réserver aux tests de câblage.")
    ram = report["ram"]["total_gb"]
    if ram is not None and ram < 16:
        notes.append(f"RAM {ram} Go : juste pour héberger l'application ET un modèle ; séparer les deux machines si possible.")
    if OS == "Windows":
        notes.append("Windows : Ollama natif est la voie la plus simple ; vLLM nécessite en général WSL2/Linux (à confirmer sur la "
                     "documentation officielle de la version utilisée).")
    return notes


def collect() -> dict:
    rep = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "probe_version": 1,
        "os": {"system": OS, "release": platform.release(), "version": platform.version()[:120], "machine": platform.machine()},
        "cpu": cpu_info(), "ram": ram_info(), "disk": disk_info(), "gpu": gpu_info(), "tools": tools_info(),
        "ollama": ollama_models(),
    }
    rep["indicative_notes"] = assess(rep)
    return rep


def to_text(r: dict) -> str:
    L: list[str] = ["ALERTE — rapport matériel (sonde v1) — " + r["generated_utc"] + " UTC", "=" * 64]
    L.append(f"Système      : {r['os']['system']} {r['os']['release']} ({r['os']['machine']})")
    L.append(f"Processeur   : {r['cpu']['model']} — {r['cpu']['physical_cores']} cœurs physiques / {r['cpu']['logical_cores']} logiques")
    L.append(f"RAM          : {r['ram']['total_gb']} Go au total, {r['ram']['available_now_gb']} Go disponibles maintenant")
    d = r["disk"]
    L.append(f"Disque       : {d.get('checked_volume_free_gb')} Go libres sur {d.get('checked_volume_total_gb')} Go (volume du dossier courant)")
    L.append("GPU NVIDIA   : " + ("aucun" if not r["gpu"]["nvidia"] else ""))
    for x in r["gpu"]["nvidia"]:
        L.append(f"   - {x['name']} : {x['vram_total_mib']} MiB de VRAM ({x['vram_free_mib']} MiB libres), pilote {x['driver']}")
    if r["gpu"].get("cuda_version_supported_by_driver"):
        L.append(f"   CUDA maximal accepté par le pilote : {r['gpu']['cuda_version_supported_by_driver']}")
    for x in r["gpu"]["other"]:
        L.append("   autre : " + "; ".join(f"{k}={v}" for k, v in x.items() if v))
    for n in r["gpu"]["notes"]:
        L.append("   note : " + n)
    L.append("Outils       :")
    for k, v in r["tools"].items():
        L.append(f"   - {k}: {v if v not in (None, '', []) else 'absent'}")
    o = r["ollama"]
    L.append("Ollama (localhost:11434) : " + ("joignable" if o["reachable"] else "injoignable ou absent"))
    for m in o["models"]:
        L.append(f"   - {m['name']} ({m['size_gb']} Go)")
    L.append("Lecture indicative (PAS une mesure de performance) :")
    for n in r["indicative_notes"]:
        L.append("   * " + n)
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=".", help="dossier où écrire le rapport (défaut : dossier courant)")
    ap.add_argument("--label", default="", help="étiquette libre sans donnée personnelle (ex. linux-gpu, windows-gpu, aws-g5)")
    ap.add_argument("--no-write", action="store_true", help="afficher seulement, sans écrire de fichier")
    a = ap.parse_args()
    rep = collect()
    text = to_text(rep)
    print(text)
    if not a.no_write:
        label = re.sub(r"[^A-Za-z0-9_-]", "", a.label) or OS.lower()
        out = Path(a.out).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        (out / f"alerte-hardware-{label}.txt").write_text(text, encoding="utf-8")
        (out / f"alerte-hardware-{label}.json").write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Rapports écrits : {out / ('alerte-hardware-' + label + '.txt')} et .json — relisez-les avant de les partager.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
