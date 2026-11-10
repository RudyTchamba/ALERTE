"""World examples: how other jurisdictions handle each gap (at least two, from different places)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from alerte import config
from alerte.knowledge.store import KnowledgeStore
from alerte.models import ActionDef, Precedent
from alerte.textutil import shorten

_COUNTRY_NAMES = {"EU": "European Union", "PH": "Philippines", "US": "United States", "JP": "Japan", "MU": "Mauritius",
                  "AU": "African Union", "INT": "International", "AE": "United Arab Emirates", "CM": "Cameroon"}


@lru_cache(maxsize=2)
def _library(data_dir: str) -> dict:
    p = Path(data_dir) / "precedents.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def find_precedents(action: ActionDef | None, gap_type: str, store: KnowledgeStore | None,
                    exclude_country: str = "", k: int = 3) -> list[Precedent]:
    lib = _library(str(config.settings.data_dir))
    raw = []
    if action is not None:
        raw += lib.get("by_action", {}).get(action.code, [])
    raw += lib.get("by_gap_type", {}).get(gap_type, [])
    out: list[Precedent] = []
    seen_j: set[str] = set()
    for r in raw:
        p = Precedent(**r)
        if p.jurisdiction in seen_j or _COUNTRY_NAMES.get(exclude_country) == p.jurisdiction:
            continue
        if store is not None and p.doc_id and p.doc_id not in store.documents:
            continue
        out.append(p)
        seen_j.add(p.jurisdiction)
        if len(out) >= k:
            return out
    # Not enough ready-made examples: search the global collection
    if store is not None and action is not None and len(out) < 2:
        query = f"{action.label} " + " ".join(action.keywords)
        for hit in store.search(query, 8, collections=["GL"]):
            c = hit.chunk
            jur = _COUNTRY_NAMES.get(c.country, c.country)
            if jur in seen_j or c.country == exclude_country:
                continue
            out.append(Precedent(jurisdiction=jur, instrument=c.title, article=c.article, doc_id=c.doc_id, url=c.url,
                                 what_it_does=shorten(c.text, 220),
                                 fit_note="Found by search; relevance to be checked by the policy analyst.",
                                 binding=c.doc_type == "law"))
            seen_j.add(jur)
            if len(out) >= k:
                break
    return out
