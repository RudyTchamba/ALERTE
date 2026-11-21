"""Intégrité et pré-engagement (doc 09 §9.9 #12), alignés sur les empreintes écrites par la simulation au lancement :

* `snapshot_sha256` = hachage canonique du snapshot PRIVÉ de son identité d'instance (exercise.id/code, seat_id) ;
* `commitment_sha256` = hachage canonique de {demandes, mandats actifs, actions, registre (état de revue par institution
  porteuse d'un siège)}. Les règles G1-G10 (table versionnée avec le moteur) ont leur propre empreinte `rules_sha256`.
Le registre n'étant pas dans le snapshot, ses états sont relus en direct : l'empreinte d'engagement permet de VÉRIFIER
qu'ils n'ont pas changé depuis le lancement.
"""
from __future__ import annotations

import copy
from typing import Any

from ..core.canonical_json import canonical_sha256
from .rules import rules_digest


def normalized_for_hash(payload: dict[str, Any]) -> dict[str, Any]:
    p = copy.deepcopy(payload)
    p.get("exercise", {}).pop("id", None)
    p.get("exercise", {}).pop("code", None)
    for s in p.get("seats", []):
        s.pop("seat_id", None)
    return p


def snapshot_hash(payload: dict[str, Any]) -> str:
    return canonical_sha256(normalized_for_hash(payload))


def seat_institutions(snapshot: dict[str, Any]) -> list[str]:
    return sorted({s["institution_id"] for s in snapshot.get("seats", [])})


def compute_commitment(snapshot: dict[str, Any], registry: dict[str, str] | None = None) -> str:
    """`registry` : états de revue (institution -> état) ; défaut : `snapshot["registry_states"]` s'il existe."""
    reg = registry if registry is not None else (snapshot.get("registry_states") or {})
    seats = set(seat_institutions(snapshot))
    demands = sorted(
        ({"inject_ref": i["inject_ref"], "action_code": d.get("action_code"), "derivation": d.get("derivation")}
         for i in snapshot["scenario"]["injects"] for d in i.get("demands", [])),
        key=lambda d: (d["inject_ref"], str(d["action_code"])))
    return canonical_sha256({"demands": demands, "mandates": snapshot["mandates"], "actions": snapshot["actions"],
                             "registry": dict(sorted((k, str(v)) for k, v in reg.items() if k in seats))})


def rules_sha256() -> str:
    return canonical_sha256(rules_digest())
