"""Garde-fous d'architecture (doc 09 §9.9 #7) : `gaps` ne lit jamais les fixtures privées d'`evaluation`."""
from __future__ import annotations

import ast
import pathlib

APP = pathlib.Path(__file__).resolve().parents[2] / "app"
FORBIDDEN = ("evaluation.fixtures",)
# `gaps` ne dépend que de core, contracts, audit (constantes), workspaces/mandates (services) ; le reste passe par ctx.services
ALLOWED_TOP = {"core", "contracts", "audit", "workspaces", "mandates", "gaps"}


def _imports_src(src: str, package: str):  # noqa: ANN202
    tree = ast.parse(src)
    pkg_parts = package.split(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name, a.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                base = ".".join(anchor + ([base] if base else []))
            yield base, base
            for a in node.names:  # `from app.evaluation import fixtures`
                yield f"{base}.{a.name}", base
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and "evaluation" in node.value:
            yield node.value, node.value  # importlib.import_module("app.evaluation.fixtures")


def _imports(path: pathlib.Path, package: str):  # noqa: ANN202
    return _imports_src(path.read_text(encoding="utf-8"), package)


def _module_files(module: str):  # noqa: ANN202
    return sorted((APP / module).rglob("*.py"))


def test_gaps_never_imports_evaluation_fixtures():
    offenders = []
    for f in _module_files("gaps"):
        pkg = "app.gaps" + ("." + ".".join(f.relative_to(APP / "gaps").parent.parts) if f.parent != APP / "gaps" else "")
        for full, _base in _imports(f, pkg):
            if any(bad in full.replace("/", ".") for bad in FORBIDDEN) or full.endswith("evaluation.fixtures"):
                offenders.append((f.name, full))
    assert offenders == []


def test_gaps_and_mandates_depend_only_on_allowed_modules():
    for module, allowed in (("gaps", ALLOWED_TOP), ("mandates", {"core", "contracts", "workspaces", "mandates"})):
        for f in _module_files(module):
            pkg = f"app.{module}"
            for full, _ in _imports(f, pkg):
                parts = full.split(".")
                if parts[0] == "app" and len(parts) > 1 and full.startswith("app.") is not False:
                    assert parts[1] in allowed or parts[1] in {"__init__"}, (f.name, full)


def test_gaps_does_not_know_other_modules_tables():
    for f in _module_files("gaps"):
        src = f.read_text(encoding="utf-8")
        assert "eval_fixture" not in src and "expected_gap_key" not in src, f.name


def test_the_scanner_itself_detects_every_import_style():
    styles = ["import app.evaluation.fixtures", "from app.evaluation.fixtures import x", "from app.evaluation import fixtures",
              "from ..evaluation.fixtures import x", "from ..evaluation import fixtures",
              "import importlib\nimportlib.import_module('app.evaluation.fixtures')"]
    for src in styles:
        assert any(f.endswith("evaluation.fixtures") for f, _ in _imports_src(src, "app.gaps")), src
    assert not any(f.endswith("evaluation.fixtures") for f, _ in _imports_src("from ..core import db", "app.gaps"))
