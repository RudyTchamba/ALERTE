"""Rendu PDF : Jinja2 -> HTML + CSS d'impression -> moteur PDF derrière le port `PdfRenderer`.

Polices : UNIQUEMENT celles embarquées dans `render/fonts` (Noto Sans / Noto Sans Arabic, OFL, sous-ensembles) ; aucune
police système n'est requise. Sections arabes : `dir="rtl"` (filtre `bidi`). Repli prévu : xhtml2pdf (non implémenté)."""
from __future__ import annotations

import html as _html
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

RENDER_DIR = Path(__file__).resolve().parent
_ARABIC = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)


class RendererUnavailable(RuntimeError):
    pass


class PdfRenderer(Protocol):
    name: str

    def available(self) -> bool: ...
    def render(self, html: str, base_url: str, *, identifier: bytes | None = None) -> bytes: ...


class WeasyPrintRenderer:
    name = "weasyprint"

    def available(self) -> bool:
        return importlib.util.find_spec("weasyprint") is not None

    def render(self, html: str, base_url: str, *, identifier: bytes | None = None) -> bytes:
        if not self.available():  # pragma: no cover
            raise RendererUnavailable("weasyprint non installé")
        import weasyprint

        opts: dict[str, Any] = {"pdf_identifier": identifier} if identifier else {}
        pdf = weasyprint.HTML(string=html, base_url=base_url).write_pdf(**opts)
        if not pdf:  # pragma: no cover
            raise RuntimeError("le moteur PDF n'a produit aucun octet")
        return pdf


class Xhtml2PdfRenderer:
    """Emplacement du repli (non implémenté : interface seulement)."""

    name = "xhtml2pdf"

    def available(self) -> bool:
        return importlib.util.find_spec("xhtml2pdf") is not None

    def render(self, html: str, base_url: str, *, identifier: bytes | None = None) -> bytes:
        raise RendererUnavailable("repli xhtml2pdf non implémenté")


def get_pdf_renderer(preferred: str | None = None) -> PdfRenderer:
    for r in (WeasyPrintRenderer(), Xhtml2PdfRenderer()):
        if (preferred in (None, r.name)) and r.available():
            if isinstance(r, Xhtml2PdfRenderer):
                continue  # non implémenté
            return r
    raise RendererUnavailable("aucun moteur PDF disponible (WeasyPrint requis ; repli xhtml2pdf non implémenté)")


def is_rtl(text: str) -> bool:
    letters = _LETTER.findall(text)
    return bool(letters) and len(_ARABIC.findall(text)) / len(letters) > 0.3


def bidi(value: Any) -> Markup:
    """Échappe le texte ; l'enveloppe dans un bloc `dir="rtl" lang="ar"` s'il est majoritairement arabe."""
    text = "" if value is None else str(value)
    esc = _html.escape(text)
    return Markup(f'<span class="rtl" dir="rtl" lang="ar">{esc}</span>') if is_rtl(text) else Markup(esc)


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(RENDER_DIR / "templates"), autoescape=select_autoescape(["html", "j2"], default=True))
    env.filters["bidi"] = bidi
    env.filters["tojson_short"] = lambda v: json.dumps(v, ensure_ascii=False, sort_keys=True) if isinstance(v, (dict, list)) else ("" if v is None else str(v))
    return env


def render_html(content: dict[str, Any]) -> str:
    led = content["cover"]["ledger"]
    return _env().get_template("report.html.j2").render(c=content, led=led, ver=led.get("verify") or {})


def render_pdf(content: dict[str, Any], renderer: PdfRenderer | None = None, identifier: bytes | None = None) -> bytes:
    renderer = renderer or get_pdf_renderer()
    return renderer.render(render_html(content), RENDER_DIR.as_uri() + "/", identifier=identifier)
