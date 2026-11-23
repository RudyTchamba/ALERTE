"""The agent arena: an SVG picture of who talks to whom during one event of a drill.

Pure Python, no JavaScript and no extra dependency, so it works in Streamlit, in a plain
browser (HTML export) and in tests.  Nodes are the agents; arrows are the messages of the
coordination board for ONE event (or a whole act).  Colours:

    blue dashed   event injected to a seat          orange   request between seats
    green         request accepted                  red      refused / "not our role"
    purple        answer of the Legal Adviser       red mark gap flag raised by the seat
"""

from __future__ import annotations

import html
import math
from typing import Any, Iterable

W, H = 980, 560
CX, CY, RX, RY = 500, 285, 340, 188
RING_ORDER = ["HYDRO", "MET", "DPC", "OPS", "ART", "ANTIC", "MINSANTE", "DPA", "CTD", "LEGAL"]

C = {
    "inject": "#2563eb", "request": "#d97706", "ok": "#16a34a", "bad": "#dc2626", "legal": "#7c3aed",
    "ink": "#0f172a", "muted": "#64748b", "bg": "#f8fafc", "card": "#ffffff", "ai": "#b45309",
}
KIND_COLOR = {"institution": "#1d4ed8", "ai_system": C["ai"], "adviser": C["legal"], "coordinator": "#0f766e"}


def _esc(x: Any) -> str:
    return html.escape(str(x), quote=True)


def short(text: str, n: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def layout(codes: Iterable[str]) -> dict[str, tuple[float, float]]:
    """Place agents on an ellipse around the coordination board, in a stable order."""
    codes = [c for c in RING_ORDER if c in set(codes)] + [c for c in codes if c not in RING_ORDER]
    n = max(len(codes), 1)
    pos = {}
    for i, c in enumerate(codes):
        ang = math.radians(-112 + (i * 224 / (n - 1) if n > 1 else 112))   # right-hand arc: the left side is for the event source
        pos[c] = (CX + RX * math.cos(ang), CY + RY * math.sin(ang))
    return pos


def _edge(a: tuple[float, float], b: tuple[float, float], r_a: float, r_b: float, bend: float):
    (x1, y1), (x2, y2) = a, b
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    sx, sy = x1 + ux * r_a, y1 + uy * r_a
    ex, ey = x2 - ux * (r_b + 7), y2 - uy * (r_b + 7)
    mx, my = (sx + ex) / 2 - uy * bend, (sy + ey) / 2 + ux * bend
    return f"M{sx:.1f},{sy:.1f} Q{mx:.1f},{my:.1f} {ex:.1f},{ey:.1f}", (0.25 * sx + 0.5 * mx + 0.25 * ex, 0.25 * sy + 0.5 * my + 0.25 * ey)


def render_arena(roles: dict[str, dict[str, str]], messages: list[dict[str, Any]] | None = None,
                 decisions: list[dict[str, Any]] | None = None, recipients: Iterable[str] = (),
                 event: dict[str, Any] | None = None, show_labels: bool = True) -> str:
    """roles: code -> {name, institution, kind}.  messages/decisions: dicts of ONE event (or several)."""
    messages, decisions = messages or [], decisions or []
    recipients = set(recipients)
    agents = [c for c in roles if c != "COORD"]
    pos = layout(agents)
    src = (72.0, CY)
    out: list[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" '
                      f'aria-label="Agent arena: who talks to whom">']
    out.append("<defs>")
    for key in ("inject", "request", "ok", "bad", "legal"):
        out.append(f'<marker id="ar-{key}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
                   f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{C[key]}"/></marker>')
    out.append("</defs>")
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" rx="16" fill="{C["bg"]}" stroke="#cbd5e1"/>')
    # coordination board in the centre
    out.append(f'<ellipse cx="{CX}" cy="{CY}" rx="92" ry="52" fill="#ecfeff" stroke="#67e8f9" stroke-dasharray="5 4"/>')
    out.append(f'<text x="{CX}" y="{CY - 6}" text-anchor="middle" font-size="13" font-weight="700" fill="#0f766e">Coordination board</text>')
    out.append(f'<text x="{CX}" y="{CY + 12}" text-anchor="middle" font-size="11" fill="{C["muted"]}">5 message types · 2 rounds max</text>')

    # event source
    sender = (event or {}).get("sender", "")
    out.append(f'<g><rect x="12" y="{CY - 36}" width="120" height="72" rx="12" fill="{C["card"]}" stroke="{C["inject"]}" stroke-width="1.6"/>'
               f'<text x="72" y="{CY - 12}" text-anchor="middle" font-size="11" fill="{C["muted"]}">Event source</text>'
               f'<text x="72" y="{CY + 6}" text-anchor="middle" font-size="14" font-weight="700" fill="{C["inject"]}">{_esc(sender or "SCENARIO")}</text>'
               f'<text x="72" y="{CY + 24}" text-anchor="middle" font-size="11" fill="{C["muted"]}">{_esc((event or {}).get("sim_time", ""))}</text></g>')

    # per-seat state
    state: dict[str, dict[str, Any]] = {c: {"dec": 0, "flags": 0, "nobasis": False} for c in agents}
    for d in decisions:
        s = state.get(d.get("seat"))
        if s is None:
            continue
        s["dec"] += 1
        s["flags"] += len(d.get("gap_flags") or [])
        s["nobasis"] = s["nobasis"] or bool(d.get("no_legal_basis"))
    for m in messages:
        if m.get("type") == "GAP_FLAG" and m.get("sender") in state and m.get("sender") != "COORD":
            pass  # already counted through decisions

    R = 36
    edges: list[str] = []
    labels: list[str] = []
    # injections
    for code in recipients:
        if code in pos:
            path, mid = _edge(src, pos[code], 66, R, 0)
            edges.append(f'<path d="{path}" fill="none" stroke="{C["inject"]}" stroke-width="2.2" stroke-dasharray="7 5" '
                         f'marker-end="url(#ar-inject)" class="flow"/>')
    # board messages
    seen: dict[tuple[str, str, str], int] = {}
    for m in messages:
        t, a, b = m.get("type"), m.get("sender"), m.get("recipient")
        talk = t == "OBJECTION" or (t == "INFO" and m.get("status") in ("agree", "clarify"))
        if (t not in ("REQUEST", "ANSWER") and not talk) or a not in pos or (b not in pos and not (talk and b == "ALL")):
            continue
        if talk:
            kind = {"object": "bad", "agree": "ok", "clarify": "request"}[m.get("status")]
        elif t == "REQUEST":
            kind = "request"
        elif a == "LEGAL":
            kind = "legal"
        else:
            kind = "ok" if m.get("status") == "accepted" else "bad"
        k = (a, b, t)
        seen[k] = seen.get(k, 0) + 1
        bend = 30 + 12 * (seen[k] - 1)   # same sign for both directions: request and answer curve apart
        target, r_b = (pos[b], R) if b in pos else ((CX, CY), 46)       # a remark to everybody goes to the board
        path, mid = _edge(pos[a], target, R, r_b, bend)
        dash = ' stroke-dasharray="3 4"' if (kind == "bad" and not talk) else ""
        edges.append(f'<path d="{path}" fill="none" stroke="{C[kind]}" stroke-width="2.4"{dash} marker-end="url(#ar-{kind})" class="msg"/>')
        if show_labels:
            lab = {"object": "objects", "agree": "agrees", "clarify": "asks"}[m["status"]] if talk else short((m.get("action") or t).replace("_", " "), 22)
            labels.append(f'<g><rect x="{mid[0] - 3.2 * len(lab) - 4:.0f}" y="{mid[1] - 9:.0f}" width="{6.4 * len(lab) + 8:.0f}" height="16" '
                          f'rx="8" fill="#fff" stroke="{C[kind]}" stroke-opacity=".5"/>'
                          f'<text x="{mid[0]:.0f}" y="{mid[1] + 3:.0f}" text-anchor="middle" font-size="10" fill="{C[kind]}">{_esc(lab)}</text></g>')
    out += edges

    # nodes
    for code in agents:
        x, y = pos[code]
        role = roles[code]
        kind = role.get("kind", "institution")
        col = KIND_COLOR.get(kind, KIND_COLOR["institution"])
        st = state[code]
        got = code in recipients or st["dec"] > 0
        active = code in recipients
        fill = "#dcfce7" if st["dec"] and not st["nobasis"] else ("#fee2e2" if st["nobasis"] else C["card"])
        if kind == "adviser" and any(m.get("sender") == "LEGAL" for m in messages):
            fill = "#ede9fe"
        opacity = 1 if (got or kind in ("adviser",) and fill != C["card"]) else (0.55 if (recipients or messages) else 1)
        dash = ' stroke-dasharray="6 4"' if kind == "ai_system" else ""
        halo = f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{R + 7}" fill="none" stroke="{C["inject"]}" stroke-width="2" class="pulse"/>' if active else ""
        out.append(f'<g opacity="{opacity}">{halo}<circle cx="{x:.0f}" cy="{y:.0f}" r="{R}" fill="{fill}" stroke="{col}" stroke-width="3"{dash}/>'
                   f'<text x="{x:.0f}" y="{y + 5:.0f}" text-anchor="middle" font-size="14" font-weight="700" fill="{col}">{_esc(code)}</text>')
        name = role.get("institution") or role.get("name") or code
        if kind == "ai_system":
            name = "HydroSense (fictional AI)"
        elif kind == "adviser":
            name = "Policy and legal adviser"
        sub = "AI under test · scripted" if kind == "ai_system" else ("" if kind == "adviser" else "")
        out.append(f'<text x="{x:.0f}" y="{y + R + 16:.0f}" text-anchor="middle" font-size="11" fill="{C["ink"]}">{_esc(short(name, 26))}</text>')
        if sub:
            out.append(f'<text x="{x:.0f}" y="{y + R + 29:.0f}" text-anchor="middle" font-size="10" fill="{C["muted"]}">{_esc(sub)}</text>')
        if st["flags"] or st["nobasis"]:
            n = st["flags"] or 1
            out.append(f'<g><circle cx="{x + 28:.0f}" cy="{y - 28:.0f}" r="11" fill="{C["bad"]}"/>'
                       f'<text x="{x + 28:.0f}" y="{y - 24:.0f}" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">{n}</text></g>')
        if st["dec"]:
            out.append(f'<g><circle cx="{x - 28:.0f}" cy="{y - 28:.0f}" r="11" fill="{C["ok"]}"/>'
                       f'<text x="{x - 28:.0f}" y="{y - 24:.0f}" text-anchor="middle" font-size="11" font-weight="700" fill="#fff">✓{st["dec"]}</text></g>')
        out.append("</g>")
    out += labels
    out.append("</svg>")
    return "".join(out)


LEGEND = [("inject", "event delivered"), ("request", "request / question"), ("ok", "accepted / agrees"),
          ("bad", "refused / objects"), ("legal", "Legal Adviser answer")]


def arena_html(svg: str, caption: str = "") -> str:
    """Standalone HTML (used in Streamlit via components.html and for the HTML export)."""
    legend = "".join(f'<span><i style="background:{C[k]}"></i>{_esc(t)}</span>' for k, t in LEGEND)
    legend += '<span><i style="background:#dc2626;border-radius:50%"></i>gap flag</span><span><i style="background:#16a34a;border-radius:50%"></i>decisions</span>'
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:transparent}}
.flow{{animation:dash 1.1s linear infinite}} .msg{{stroke-dasharray:none}}
@keyframes dash{{to{{stroke-dashoffset:-24}}}}
.pulse{{animation:pulse 1.6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}
@keyframes pulse{{0%{{opacity:.9;transform:scale(1)}}100%{{opacity:0;transform:scale(1.25)}}}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#475569;margin:8px 4px}}
.legend i{{display:inline-block;width:18px;height:4px;border-radius:2px;margin-right:5px;vertical-align:middle}}
.cap{{font-size:13px;color:#334155;margin:6px 4px}}
@media (prefers-reduced-motion:reduce){{.flow,.pulse{{animation:none}}}}
</style></head><body>{svg}<div class="legend">{legend}</div>{f'<div class="cap">{_esc(caption)}</div>' if caption else ''}</body></html>"""
