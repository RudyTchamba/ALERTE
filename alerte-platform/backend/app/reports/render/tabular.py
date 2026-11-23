"""Rendus CSV (liste des lacunes) et XLSX (lacunes, preuves, références, plan, revues, intégrité). Anti-injection de formules."""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

CSV_COLUMNS = ["section", "gap_id", "fingerprint", "code", "category", "title", "domain", "institutions", "severity",
               "confidence", "evidence_basis", "validation_status", "origin", "registry_state", "cause", "corpus_coverage",
               "absence_statement", "references_status", "description"]


def safe(v: Any) -> Any:
    """Neutralise l'injection de formules (=, +, -, @, tab, CR en tête de cellule)."""
    if isinstance(v, (list, dict)):
        v = json.dumps(v, ensure_ascii=False, sort_keys=True)
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def gap_rows(c: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for section, items in (("constat", c["findings"]), ("hypothese", c["hypotheses"])):
        for f in items:
            row = {k: f.get(k) for k in CSV_COLUMNS if k not in ("section", "gap_id", "institutions")}
            row.update(section=section, gap_id=f["id"], institutions="; ".join(f.get("institutions") or []))
            rows.append(row)
    return rows


def render_csv(c: dict[str, Any]) -> bytes:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\r\n")
    w.writeheader()
    for r in gap_rows(c):
        w.writerow({k: safe(r.get(k)) for k in CSV_COLUMNS})
    return ("\ufeff" + buf.getvalue()).encode("utf-8")  # BOM : ouverture correcte (accents, arabe) dans Excel


def render_xlsx(c: dict[str, Any]) -> bytes:
    wb = Workbook()
    wb.properties.creator = "ALERTE"
    created = dt.datetime.fromisoformat(c["cover"]["generated_at"].replace("Z", "+00:00")).replace(tzinfo=None)
    wb.properties.created = wb.properties.modified = created
    head = PatternFill("solid", fgColor="1F3A5F")

    def sheet(ws: Any, cols: list[str], rows: list[list[Any]], widths: dict[int, int] | None = None) -> None:
        ws.append(cols)
        for cell in ws[1]:
            cell.font, cell.fill = Font(bold=True, color="FFFFFF"), head
        for r in rows:
            ws.append([safe(v) for v in r])
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                if isinstance(cell.value, str):
                    cell.data_type = "s"  # jamais interprété comme formule
        for i in range(1, len(cols) + 1):
            ws.column_dimensions[ws.cell(1, i).column_letter].width = (widths or {}).get(i, 22)
        ws.freeze_panes = "A2"

    led = c["cover"]["ledger"]
    ws = wb.active
    ws.title = "Intégrité"
    sheet(ws, ["Champ", "Valeur"], [
        ["Rapport", c["title"]], ["Version", c["cover"]["version_no"]], ["Généré le", c["cover"]["generated_at"]],
        ["Exercice", f"{c['cover']['exercise'].get('code')} {c['cover']['exercise'].get('id')}"],
        ["Mode IA", c["cover"].get("ai_mode")], ["Étiquette", c["cover"].get("ai_label") or ""],
        ["Hash du snapshot", c["cover"].get("snapshot_sha256")], ["Tête du ledger (seq)", led.get("head_seq")],
        ["Tête du ledger (hash)", led.get("head_hash")], ["Ledger vérifié", "intact" if (led.get("verify") or {}).get("ok") else "ÉCHEC"]],
        {1: 28, 2: 90})
    rows = gap_rows(c)
    sheet(wb.create_sheet("Lacunes"), CSV_COLUMNS, [[r.get(k) for k in CSV_COLUMNS] for r in rows], {6: 48, 19: 70})
    sheet(wb.create_sheet("Preuves"), ["Lacune", "Type", "Rôle", "Référence", "Extrait"],
          [[e["gap_id"], e["kind"], e["role"], e["ref"], e["excerpt"]] for e in c["annexes"]["evidence_index"]], {4: 40, 5: 70})
    sheet(wb.create_sheet("Références"), ["Lacune", "Juridiction", "Instrument", "Article", "Résumé", "Contraignant", "URL", "Statut", "Message"],
          [[r["gap_title"], x.get("jurisdiction"), x.get("instrument"), x.get("article"), x.get("summary"), x.get("binding"), x.get("url"),
            x.get("status"), r.get("message")]
           for r in c["references"] for x in (r["references"] or [{}])], {5: 60})  # une lacune SANS référence : ligne avec le seul message
    sheet(wb.create_sheet("Plan"), ["Lacune", "Recommandation", "Propriétaire", "Échéance", "Statut", "KPI"],
          [[a["gap_title"], a["recommendation"], a["owner"], a["due_date"], a["status"], a["kpi"]] for a in c["improvement_plan"]], {2: 60})
    sheet(wb.create_sheet("Revues"), ["Lacune", "Relecteur", "Action", "De", "À", "Réalité", "Commentaire", "Date"],
          [[h["gap_title"], h["reviewer"], h["action"], h["from_status"], h["to_status"], h["reality_label"], h["comment"], h["created_at"]]
           for h in c["reviews"]["history"]], {7: 50})
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def render_json(c: dict[str, Any]) -> bytes:
    return (json.dumps(c, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
