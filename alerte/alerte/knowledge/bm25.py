"""Okapi BM25 keyword search in pure Python (fast enough for tens of thousands of chunks)."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Iterable

from alerte.textutil import bridge_query, tokenize


class BM25:
    def __init__(self, texts: Iterable[str], k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        self.postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        self.lengths: list[int] = []
        for i, text in enumerate(texts):
            toks = tokenize(text)
            self.lengths.append(len(toks))
            for tok, tf in Counter(toks).items():
                self.postings[tok].append((i, tf))
        self.n = len(self.lengths)
        self.avgdl = (sum(self.lengths) / self.n) if self.n else 1.0
        self.idf = {t: math.log(1 + (self.n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def scores(self, query: str, allowed: set[int] | None = None) -> dict[int, float]:
        out: dict[int, float] = defaultdict(float)
        for tok in set(tokenize(bridge_query(query))):
            idf = self.idf.get(tok)
            if idf is None:
                continue
            for i, tf in self.postings[tok]:
                if allowed is not None and i not in allowed:
                    continue
                dl = self.lengths[i]
                out[i] += idf * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return out
