"""Comparaisons (fonctions pures) : deux versions d'un même rapport (diff structurel) ; deux exercices (par fingerprint)."""
from __future__ import annotations

from typing import Any

from ..core.canonical_json import canonical_sha256

TRACKED = ("severity", "validation_status", "confidence", "evidence_basis", "title")


def _index(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {(i.get("fingerprint") or i.get("id")): i for i in items}


def _brief(g: dict[str, Any]) -> dict[str, Any]:
    return {"fingerprint": g.get("fingerprint"), "id": g.get("id"), "code": g.get("code"), "title": g.get("title"),
            "severity": g.get("severity"), "validation_status": g.get("validation_status")}


def compare_gap_lists(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> dict[str, Any]:
    """Base = a, comparé = b. new : dans b seulement ; resolved : dans a seulement ; persistent : dans les deux
    (avec sévérité/statut modifiés)."""
    ia, ib = _index(a), _index(b)
    new = [_brief(ib[k]) for k in ib if k not in ia]
    resolved = [_brief(ia[k]) for k in ia if k not in ib]
    persistent, severity_changed, status_changed = [], [], []
    for k in ia:
        if k in ib:
            row = {**_brief(ib[k]), "severity_before": ia[k].get("severity"), "status_before": ia[k].get("validation_status")}
            persistent.append(row)
            if ia[k].get("severity") != ib[k].get("severity"):
                severity_changed.append(row)
            if ia[k].get("validation_status") != ib[k].get("validation_status"):
                status_changed.append(row)
    return {"new": new, "resolved": resolved, "persistent": persistent, "severity_changed": severity_changed,
            "status_changed": status_changed,
            "counts": {"new": len(new), "resolved": len(resolved), "persistent": len(persistent),
                       "severity_changed": len(severity_changed), "status_changed": len(status_changed)}}


def compare_contents(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Diff structurel de deux contenus JSON : constats/hypothèses (par fingerprint), sections modifiées, mesures."""
    out: dict[str, Any] = {}
    for section in ("findings", "hypotheses"):
        ia, ib = _index(a.get(section, [])), _index(b.get(section, []))
        changed = []
        for k in ia:
            if k in ib:
                diff = {f: [ia[k].get(f), ib[k].get(f)] for f in TRACKED if ia[k].get(f) != ib[k].get(f)}
                if diff:
                    changed.append({"fingerprint": k, "title": ib[k].get("title"), "changes": diff})
        out[section] = {"added": [_brief(ib[k]) for k in ib if k not in ia], "removed": [_brief(ia[k]) for k in ia if k not in ib],
                        "changed": changed, "unchanged": sum(1 for k in ia if k in ib) - len(changed)}
    skip = {"cover"}
    out["sections_changed"] = sorted(k for k in set(a) | set(b) if k not in skip
                                     and canonical_sha256(a.get(k)) != canonical_sha256(b.get(k)))
    ma, mb = a.get("metrics", {}), b.get("metrics", {})
    out["metrics"] = {m: {"a": (ma.get(m) or {}).get("value"), "b": (mb.get(m) or {}).get("value")}
                      for m in sorted(set(ma) | set(mb)) if (ma.get(m) or {}).get("value") != (mb.get(m) or {}).get("value")}
    ca, cb = a.get("cover", {}), b.get("cover", {})
    out["cover"] = {"version_no": [ca.get("version_no"), cb.get("version_no")],
                    "ledger_head": [(ca.get("ledger") or {}).get("head_seq"), (cb.get("ledger") or {}).get("head_seq")],
                    "ai_mode": [ca.get("ai_mode"), cb.get("ai_mode")]}
    out["identical"] = canonical_sha256({k: v for k, v in a.items() if k != "cover"}) == \
        canonical_sha256({k: v for k, v in b.items() if k != "cover"})
    return out
