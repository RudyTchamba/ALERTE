"""The ALERTE architecture diagram (SVG), laid out on the ITU-T Y.3172 pipeline:
SRC -> C -> PP -> M -> P -> D -> SINK, orchestrated by the MLFO, inside a Sandbox.

    python -m alerte.ui.architecture docs/architecture.svg
"""

from __future__ import annotations

import html
import sys
from pathlib import Path

W, H = 1500, 1010
COL = {"src": "#0ea5e9", "c": "#14b8a6", "pp": "#22c55e", "m": "#f59e0b", "p": "#ef4444", "d": "#8b5cf6", "sink": "#ec4899",
       "mlfo": "#475569", "sb": "#0f766e", "ext": "#94a3b8"}
FILL = {"src": "#e0f2fe", "c": "#ccfbf1", "pp": "#dcfce7", "m": "#fef3c7", "p": "#fee2e2", "d": "#ede9fe", "sink": "#fce7f3",
        "mlfo": "#f1f5f9", "sb": "#f0fdfa", "ext": "#f8fafc"}


def _e(x: str) -> str:
    return html.escape(x)


class Canvas:
    def __init__(self) -> None:
        self.p: list[str] = []

    def band(self, x, y, w, h, key, tag, title):
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{FILL[key]}" fill-opacity=".55" stroke="{COL[key]}" stroke-width="1.6" stroke-dasharray="6 4"/>')
        self.p.append(f'<rect x="{x + 12}" y="{y - 12}" width="{14 + 8 * len(tag)}" height="24" rx="12" fill="{COL[key]}"/>'
                      f'<text x="{x + 19}" y="{y + 5}" font-size="13" font-weight="700" fill="#fff">{_e(tag)}</text>')
        self.p.append(f'<text x="{x + 36 + 8 * len(tag)}" y="{y + 5}" font-size="13" font-weight="600" fill="#334155">{_e(title)}</text>')

    def box(self, x, y, w, h, key, title, lines=(), dashed=False):
        d = ' stroke-dasharray="5 3"' if dashed else ""
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="{COL[key]}" stroke-width="2"{d}/>')
        self.p.append(f'<text x="{x + w / 2}" y="{y + 20}" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">{_e(title)}</text>')
        for i, ln in enumerate(lines):
            self.p.append(f'<text x="{x + w / 2}" y="{y + 38 + 15 * i}" text-anchor="middle" font-size="11" fill="#475569">{_e(ln)}</text>')

    def arrow(self, x1, y1, x2, y2, color="#64748b", label="", dashed=False, curve=0):
        d = ' stroke-dasharray="6 4"' if dashed else ""
        if curve:
            mx, my = (x1 + x2) / 2 + curve, (y1 + y2) / 2
            path = f"M{x1},{y1} Q{mx},{my} {x2},{y2}"
        else:
            path = f"M{x1},{y1} L{x2},{y2}"
        self.p.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2"{d} marker-end="url(#ah)"/>')
        if label:
            self.p.append(f'<text x="{(x1 + x2) / 2 + curve / 2 + 4}" y="{(y1 + y2) / 2 - 4}" font-size="10.5" fill="{color}" font-style="italic">{_e(label)}</text>')

    def svg(self) -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" role="img" '
                f'aria-label="ALERTE architecture on the ITU-T Y.3172 pipeline" font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif">'
                '<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
                '<path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>'
                f'<rect width="{W}" height="{H}" rx="18" fill="#ffffff" stroke="#cbd5e1"/>')
        return head + "".join(self.p) + "</svg>"


def architecture_svg() -> str:
    c = Canvas()
    c.p.append('<text x="30" y="40" font-size="22" font-weight="800" fill="#0f172a">ALERTE · architecture on the ITU-T Y.3172 pipeline</text>')
    c.p.append('<text x="30" y="62" font-size="13" fill="#475569">Crisis-drill simulator for AI-assisted public alerting · fictional scenarios · runs offline on Windows, macOS, Linux · open source (MIT)</text>')

    # --- SRC
    c.band(20, 100, 1460, 112, "src", "SRC", "Sources (documents and events)")
    srcs = [("National texts", ["UAE (primary), Cameroon", "laws, decrees, plans (official /", "summary / not_found)"]),
            ("Global precedents", ["EU Code Art.110, AI Act, PH RA 10639,", "US 47 CFR 10, Hawaii 2018, JP J-Alert,", "Mauritius CAP, NIST AI RMF"]),
            ("ITU texts", ["Y.3172, X.1303 (CAP),", "AI Readiness Report 2.0,", "hackathon requirements"]),
            ("ITU reference corpus", ["seed documents of", "CrashingGuru/ITUAIReadiness", "(auto-detected, optional)"]),
            ("Scenario injects", ["12 timed events, 2 acts + stress test", "fictional HydroSense model card", "role cards, who-does-what map"])]
    for i, (t, ls) in enumerate(srcs):
        c.box(40 + i * 288, 118, 268, 84, "src", t, ls)

    # --- C + PP
    c.band(20, 250, 1460, 128, "pp", "C · PP", "Collector and pre-processor  →  knowledge base")
    steps = [("c", "Collector", ["manifest.csv + EVERY file in data/docs", "(any folder), extra folders, upload", "dedupe by SHA-256 · none skipped"]),
             ("pp", "Read (knowledge/extract/)", ["digital: exact text layer + tables", "scans: clean-up, 2-3 OCR passes, cells", "pictures with text · Word · Excel"]),
             ("pp", "Chunk by article", ["country, type, article, language,", "institutions, topics, evidence tag,", "how read: text layer / OCR % / human"]),
             ("pp", "Embed (optional)", ["none = BM25 + FR/EN bridge", "Ollama bge-m3 · fastembed", "OpenAI-compatible"]),
             ("pp", "Knowledge base", ["index/ chunks + BM25 + vectors", "review queue → human proofread", "export-chroma → ITU ChromaDB"])]
    for i, (k, t, ls) in enumerate(steps):
        x = 40 + i * 288
        c.box(x, 268, 268, 92, k, t, ls)
        if i:
            c.arrow(x - 20, 314, x, 314)
    for i in range(5):
        c.arrow(174 + i * 288, 202, 174 + i * 288, 268, "#0ea5e9")

    # --- M + P
    c.band(20, 418, 1460, 250, "m", "M · P", "Model layer (agents)  and  policy layer (checks)")
    # gateway
    c.box(40, 440, 270, 210, "m", "LLM gateway (one AI door)", ["sim/llm_client.py · every call logged", "retries, JSON repair, fallback", "", "OFFLINE rule brain (default)", "Ollama · vLLM · llama.cpp", "LM Studio · ITU sandbox", "LoRA fine-tune (sandbox/)"])
    # agents
    c.p.append('<rect x="340" y="440" width="560" height="210" rx="12" fill="#fff" stroke="#f59e0b" stroke-width="2"/>')
    c.p.append('<text x="620" y="460" text-anchor="middle" font-size="13" font-weight="700" fill="#0f172a">Six agents · private inbox · mandate-filtered retrieval</text>'
               '<text x="620" y="476" text-anchor="middle" font-size="10.5" fill="#92400e">AI mode: each reasons from its own perspective, asks, objects, agrees · rule-engine mode: labelled templates, no AI</text>')
    ag = [("MET", "weather", 360), ("DPC", "civil protection", 440), ("OPS", "operator", 520), ("ART", "regulator", 600), ("ANTIC", "security", 680)]
    for code, sub, x in ag:
        c.p.append(f'<circle cx="{x + 30}" cy="515" r="31" fill="#fffbeb" stroke="#1d4ed8" stroke-width="2.6"/>'
                   f'<text x="{x + 30}" y="520" text-anchor="middle" font-size="13" font-weight="700" fill="#1d4ed8">{code}</text>'
                   f'<text x="{x + 30}" y="562" text-anchor="middle" font-size="10.5" fill="#475569">{sub}</text>')
    c.p.append('<circle cx="810" cy="515" r="31" fill="#f5f3ff" stroke="#7c3aed" stroke-width="2.6"/><text x="810" y="520" text-anchor="middle" font-size="13" font-weight="700" fill="#7c3aed">LEGAL</text>'
               '<text x="810" y="562" text-anchor="middle" font-size="10.5" fill="#475569">adviser</text>')
    c.p.append('<circle cx="860" cy="600" r="0" />')
    c.p.append('<rect x="358" y="582" width="262" height="52" rx="8" fill="#fef3c7" stroke="#b45309" stroke-dasharray="5 3"/>'
               '<text x="489" y="603" text-anchor="middle" font-size="12" font-weight="700" fill="#92400e">HydroSense (fictional AI under test)</text>'
               '<text x="489" y="621" text-anchor="middle" font-size="10.5" fill="#92400e">scripted: fails on cue, model card: ≥5 of 7 sensors</text>')
    c.p.append('<text x="640" y="596" font-size="10.5" fill="#475569">4 tools: search · ask LEGAL · post · decide</text>')
    c.p.append('<text x="640" y="612" font-size="10.5" fill="#475569">decision record: known, unknown, options,</text>')
    c.p.append('<text x="640" y="627" font-size="10.5" fill="#475569">choice, legal basis, confidence</text>')
    # policy
    c.box(930, 440, 530, 210, "p", "Policy layer (rules, not opinions)", [
        "Mandate map: who may / must do what (powers, duties, leads)", "each line: article + evidence (documented / inferred / assumed)", "",
        "Citation checker: rejects articles or quotes not in the library", "Gap rules G1 G2 G3 G6 G7 G8 G9 → severity, confidence",
        "Precedent library: ≥2 jurisdictions per gap", "Readiness scorecard: ITU Report 2.0, 13 dimensions"])
    c.arrow(310, 545, 340, 545, "#f59e0b")
    c.arrow(900, 545, 930, 545, "#ef4444")
    c.arrow(1195, 378, 1195, 440, "#22c55e", "retrieval")
    c.arrow(620, 378, 620, 440, "#22c55e", "passages (filtered)")

    # --- D + MLFO
    c.band(20, 708, 1460, 96, "d", "D · MLFO", "Distributor (coordination board)  and  orchestrator (drill engine)")
    c.box(40, 724, 520, 72, "d", "Coordination board · 6 message types", ["INFO · REQUEST · ANSWER · DECISION · OBJECTION · GAP_FLAG", "no agent reads another inbox · max 2 rounds per inject"])
    c.box(580, 724, 880, 72, "mlfo", "MLFO: Drill engine (sim/engine.py)", ["config: country · scenario · mode · brain · language · humans · autopilot / replay / pause / surprise inject",
                                                                          "budget: ≤2 rounds per inject · ≤150 model calls · simulated clock · human-seat forms"])
    c.arrow(620, 668, 620, 724, "#8b5cf6", "messages")

    # --- SINK
    c.band(20, 842, 1460, 92, "sink", "SINK", "Outputs")
    outs = [("Streamlit interface", ["agent arena · live exercise · decisions", "gap report · replay · adviser · readiness"]),
            ("Reports", ["HTML + Markdown + JSON", "gap report, timeline, assumptions"]),
            ("Open knowledge", ["ChromaDB export (ITU format)", "contribution to the ITU open asset"]),
            ("Fine-tuning data", ["export-sft → LoRA", "(sandbox GPU credits)"]),
            ("Notifications", ["Slack webhook (optional)", "run summary"])]
    for i, (t, ls) in enumerate(outs):
        c.box(40 + i * 288, 856, 268, 70, "sink", t, ls)
    c.arrow(1000, 796, 1000, 856, "#ec4899")

    # --- Sandbox
    c.p.append('<rect x="20" y="948" width="1460" height="50" rx="12" fill="#f0fdfa" stroke="#0f766e" stroke-width="2"/>'
               '<text x="750" y="970" text-anchor="middle" font-size="13" font-weight="700" fill="#0f766e">SANDBOX = the whole simulator · SHA-256 hash-chained ledger (ledger.jsonl)</text>'
               '<text x="750" y="988" text-anchor="middle" font-size="11" fill="#115e59">records events, retrievals, model calls, messages, decisions, citation checks, gaps, expert reviews · replay without calling the AI · verify button detects any edit</text>')
    return c.svg()


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "architecture.svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(architecture_svg(), encoding="utf-8")
    print(f"written {out}")


if __name__ == "__main__":
    main()
