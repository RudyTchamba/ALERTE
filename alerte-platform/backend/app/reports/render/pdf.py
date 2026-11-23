"""Rendu PDF : Jinja2 -> HTML + CSS d'impression -> moteur PDF derrière le port `PdfRenderer`.

Polices : UNIQUEMENT celles embarquées dans `render/fonts` (Noto Sans / Noto Sans Arabic, OFL, sous-ensembles) ; aucune
police système n'est requise. Sections arabes : `dir="rtl"` (filtre `bidi`).
Repli : `BasicPdfRenderer`, pur Python, sans dépendance (texte seul, police PDF standard Helvetica, latin) quand
WeasyPrint ou ses bibliothèques système (Pango) manquent : le rapport reste exportable, la mise en page en moins."""
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


class BasicPdfRenderer:
    """Repli pur Python : HTML -> texte structuré -> PDF 1.4 (Helvetica, A4). Toujours disponible, déterministe.
    Limites assumées : pas d'images ni de tableaux mis en forme ; caractères hors Latin-1 remplacés par « ? »."""

    name = "basic"
    W, H, M, FS, LH = 595, 842, 56, 10, 14  # A4 en points, marge, taille, interligne

    def available(self) -> bool:
        return True

    @staticmethod
    def _text(html: str) -> list[tuple[str, str]]:
        """(style, ligne) ; style : h (titre) ou p. Les blocs HTML deviennent des sauts de ligne."""
        html = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", "", html)
        html = re.sub(r"(?i)<(h[1-3])[^>]*>", "\n\u0001", html)
        html = re.sub(r"(?i)</h[1-3]>", "\n", html)
        html = re.sub(r"(?i)<(br|/p|/div|/li|/tr|/table|/section|/header|/footer)[^>]*>", "\n", html)
        html = re.sub(r"(?i)<li[^>]*>", "\n• ", html)
        html = re.sub(r"(?i)</t[dh]>", "  ", html)
        text = _html.unescape(re.sub(r"<[^>]+>", "", html))
        out: list[tuple[str, str]] = []
        for raw in text.split("\n"):
            line = re.sub(r"[ \t\r\f\v]+", " ", raw).strip()
            if line:
                out.append(("h", line[1:].strip()) if line.startswith("\u0001") else ("p", line))
        return out

    def _wrap(self, line: str, size: float) -> list[str]:
        maxc = max(20, int((self.W - 2 * self.M) / (size * 0.5)))
        words, cur, rows = line.split(" "), "", []
        for w in words:
            while len(w) > maxc:
                rows.append((cur + " " + w[:maxc - len(cur) - 1]).strip() if cur else w[:maxc])
                w, cur = w[maxc - len(cur) - 1 if cur else maxc:], ""
            if len(cur) + len(w) + 1 > maxc:
                rows.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        return rows + ([cur] if cur else [])

    @staticmethod
    def _esc(t: str) -> str:
        t = t.encode("latin-1", errors="replace").decode("latin-1")
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def render(self, html: str, base_url: str, *, identifier: bytes | None = None) -> bytes:
        pages: list[list[str]] = [[]]
        y = self.H - self.M
        for style, line in self._text(html):
            size = 13 if style == "h" else self.FS
            font = "F2" if style == "h" else "F1"
            if style == "h":
                y -= 6
            for row in self._wrap(line, size):
                if y < self.M:
                    pages.append([])
                    y = self.H - self.M
                pages[-1].append(f"BT /{font} {size} Tf {self.M} {y} Td ({self._esc(row)}) Tj ET")
                y -= self.LH + (3 if style == "h" else 0)
        objs: list[bytes] = []
        n_pages = len(pages)
        kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(n_pages))
        objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>".encode())
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        for i, ops in enumerate(pages):
            body = ("\n".join(ops + [f"BT /F1 8 Tf {self.M} 28 Td (ALERTE - {i + 1}/{n_pages}) Tj ET"])).encode("latin-1")
            objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.W} {self.H}] "
                        f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {6 + 2 * i} 0 R >>".encode())
            objs.append(b"<< /Length %d >>\nstream\n" % len(body) + body + b"\nendstream")
        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for k, o in enumerate(objs, start=1):
            offsets.append(len(out))
            out += f"{k} 0 obj\n".encode() + o + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
        out += b"".join(f"{off:010d} 00000 n \n".encode() for off in offsets)
        ident = (identifier or b"alerte").hex()
        out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /ID [<{ident}> <{ident}>] >>\nstartxref\n{xref}\n%%EOF\n".encode()
        return bytes(out)


def get_pdf_renderer(preferred: str | None = None) -> PdfRenderer:
    """WeasyPrint si disponible (et ses bibliothèques système chargeables), sinon le repli pur Python."""
    if preferred in (None, "weasyprint"):
        w = WeasyPrintRenderer()
        if w.available():
            try:
                import weasyprint  # noqa: F401 - échoue si Pango/cairo manquent
                return w
            except Exception:  # noqa: BLE001
                if preferred == "weasyprint":
                    raise RendererUnavailable("WeasyPrint installé mais inutilisable (bibliothèques système manquantes)") from None
        elif preferred == "weasyprint":
            raise RendererUnavailable("weasyprint non installé")
    return BasicPdfRenderer()


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
