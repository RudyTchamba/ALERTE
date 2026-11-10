"""Language-light text helpers for French, English (and basic Arabic)."""

from __future__ import annotations

import re
import unicodedata

_STOP = set(
    """
a an and are as at be been but by can could do does for from had has have how if in into is it its
may might must no not of on or our shall should so such than that the their them then there these
they this those to under upon was were what when where which while who whom why will with would you
your we us i me my he she his her also any each other only same some all both more most very
au aux avec ce ces cet cette dans de des du elle en et eux il ils je la le les leur leurs lui ma
mais me meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes
toi ton tu un une vos votre vous est sont etre ete fait faire peut doit doivent selon ainsi lors
afin dont tout tous toute toutes plus moins sans entre leur sera seront avoir aussi
""".split()
)

_TOKEN = re.compile(r"[a-z0-9؀-ۿ]+", re.UNICODE)


def fold(text: str) -> str:
    """Lowercase and remove accents (é -> e) so French queries match unaccented text."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _stem(tok: str) -> str:
    # Very light suffix stripping shared by FR/EN; enough for BM25 recall.
    for suf in ("ations", "ation", "ements", "ement", "ments", "ment", "ities", "ity", "ings", "ing",
                "ions", "ion", "ers", "er", "es", "s"):
        if len(tok) > len(suf) + 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in _TOKEN.findall(fold(text)) if t not in _STOP and len(t) > 1]


def normalize_ws(text: str) -> str:
    text = text.replace(" ", " ").replace("\r", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def shorten(text: str, n: int = 240) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")
    return s[:n] or "x"


# French -> English bridge for keyword search when no multilingual embedding model is running.
_FR_EN = {
    "inondation": "flood", "inondations": "floods", "crue": "flood", "pluie": "rain", "pluies": "rain",
    "alerte": "alert warning", "alertes": "alerts warnings", "avertissement": "warning",
    "personnes": "people", "touchees": "affected", "touches": "affected", "sinistres": "affected",
    "donnees": "data", "personnelles": "personal", "personnel": "personal", "etranger": "abroad foreign",
    "transfert": "transfer", "transferer": "transfer", "autorisation": "authorisation authorization",
    "prealable": "prior", "operateur": "operator", "operateurs": "operators", "telephone": "phone",
    "telephones": "phones", "localisation": "location", "sante": "health", "cholera": "cholera",
    "epidemie": "epidemic outbreak", "protection": "protection", "civile": "civil", "loi": "law",
    "decret": "decree", "strategie": "strategy", "intelligence": "intelligence", "artificielle": "artificial",
    "responsable": "responsible liable", "responsabilite": "liability responsibility", "evacuation": "evacuation",
    "secours": "rescue relief", "urgence": "emergency", "plan": "plan", "regulateur": "regulator",
    "cybersecurite": "cybersecurity", "faux": "fake false", "fausse": "false fake", "langue": "language",
    "langues": "languages", "couverture": "coverage", "reseau": "network", "meteo": "weather",
    "meteorologie": "meteorology weather", "prevision": "forecast", "capteurs": "sensors", "extreme": "far",
    "nord": "north", "combien": "how many", "qui": "who", "quelle": "which what", "doit": "must",
}


def bridge_query(query: str) -> str:
    """Append English equivalents of French words (keyword search only)."""
    extra = [_FR_EN[w] for w in re.findall(r"[a-z]+", fold(query)) if w in _FR_EN]
    return query if not extra else query + " " + " ".join(extra)
