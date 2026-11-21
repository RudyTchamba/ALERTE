"""Découverte des modules : routeurs et modèles.

Chaque module métier peut fournir `app/<module>/models.py` (tables) et `app/<module>/router.py`
(variable `router`) et, optionnellement, `app/<module>/setup.py` avec `register(ctx)` appelée au démarrage
(enregistrement de services dans le contexte, hooks…). Un module absent est ignoré ; une erreur
d'import À L'INTÉRIEUR d'un module existant est propagée (jamais masquée).
"""
from __future__ import annotations

import importlib
import importlib.util
import logging

log = logging.getLogger("alerte.modules")

# ordre = ordre de dépendance autorisée (doc 05 §5.3)
MODULES = ("workspaces", "audit", "knowledge", "mandates", "agents", "scenarios", "simulation",
           "gaps", "evaluation", "reports")


def _has(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def import_all_models() -> list[str]:
    """Importe tous les `models.py` pour enregistrer les tables dans `Base.metadata`."""
    loaded = ["app.core.jobs"]
    importlib.import_module("app.core.jobs")
    for m in MODULES:
        name = f"app.{m}.models"
        if _has(name):
            importlib.import_module(name)
            loaded.append(name)
    return loaded


def routers():  # noqa: ANN201
    found = []
    for m in MODULES:
        name = f"app.{m}.router"
        if _has(name):
            mod = importlib.import_module(name)
            found.append((m, mod.router))
    return found


def run_setups(ctx) -> list[str]:  # noqa: ANN001
    done = []
    for m in MODULES:
        name = f"app.{m}.setup"
        if _has(name):
            mod = importlib.import_module(name)
            mod.register(ctx)
            done.append(m)
    return done
