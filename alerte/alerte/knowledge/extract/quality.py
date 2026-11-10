"""Is a text layer trustworthy, and how much do two readings of the same page agree?"""

from __future__ import annotations

import re
import unicodedata

try:
    from rapidfuzz.distance import Levenshtein as _Lev
except ImportError:  # pragma: no cover
    _Lev = None

_ARABIC = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
_PUA = re.compile(r"[-�]")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_WORD = re.compile(r"[^\W\d_]{4,}", re.UNICODE)
_VOWEL = re.compile(r"[aeiouyàâäéèêëîïôöùûüœæ]", re.I)


def norm(text: str) -> str:
    """Normal form used for comparisons: Unicode compatibility form, one space, no zero-width marks."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[​-‏‪-‮⁦-⁩ـ]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def arabic_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    return sum(1 for c in letters if _ARABIC.match(c)) / len(letters) if letters else 0.0


def text_layer_trust(text: str) -> tuple[bool, list[str]]:
    """False when the embedded text looks like broken font encoding rather than language."""
    flat = re.sub(r"\s", "", text)
    n = len(flat)
    if n == 0:
        return False, ["empty"]
    reasons: list[str] = []
    bad = len(_PUA.findall(flat)) + len(_CTRL.findall(flat))
    if bad / n > 0.02:
        reasons.append("bad-encoding")
    if sum(c.isalpha() for c in flat) / n < 0.30 and n > 200:
        reasons.append("few-letters")
    words = _WORD.findall(text)
    latin = [w for w in words if not _ARABIC.search(w)]
    if len(latin) >= 8:
        novowel = sum(1 for w in latin if not _VOWEL.search(w))
        if novowel / len(latin) > (0.30 if len(latin) >= 25 else 0.5):
            reasons.append("garbled")
    return not reasons, reasons


def similarity(a: str, b: str) -> float:
    """0-1 character-level similarity of two readings, ignoring spacing and case."""
    a, b = norm(a).casefold(), norm(b).casefold()
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    if _Lev is not None:
        return float(_Lev.normalized_similarity(a, b))
    import difflib
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate (0 = perfect), after whitespace normalisation."""
    r, h = norm(reference), norm(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    if _Lev is not None:
        return _Lev.distance(r, h) / len(r)
    import difflib
    return 1 - difflib.SequenceMatcher(None, r, h, autojunk=False).ratio()
