"""Normalisation, défense contre les instructions cachées, détection de langue, analyseur lexical FR/AR."""
from __future__ import annotations

import re
import threading
import unicodedata
from collections import Counter

ANALYZER_VERSION = "1"

# --------------------------------------------------------------------------- normalisation
_INVISIBLE = {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x180E, 0x2061, 0x2062, 0x2063, 0x2064}
_BIDI_CONTROLS = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A))  # embeddings/overrides/isolats (Trojan Source)
_KEEP_MARKS = {0x200E, 0x200F, 0x061C}  # LRM/RLM/ALM : direction RTL préservée


def _is_tag(cp: int) -> bool:
    return 0xE0000 <= cp <= 0xE007F


def normalize_text(text: str, stats: Counter | None = None) -> str:
    """NFC ; retire invisibles, balises Unicode « tag », surcharges bidi et caractères de contrôle (\\n et \\t gardés)."""
    stats = stats if stats is not None else Counter()
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n")
    out: list[str] = []
    for ch in unicodedata.normalize("NFC", text):
        cp = ord(ch)
        if cp in _KEEP_MARKS:
            out.append(ch)
        elif cp in _INVISIBLE:
            stats["invisible_removed"] += 1
        elif _is_tag(cp):
            stats["tag_chars_removed"] += 1
        elif cp in _BIDI_CONTROLS:
            stats["bidi_controls_removed"] += 1
        elif ch in "\n\t":
            out.append(ch)
        elif unicodedata.category(ch) in ("Cc", "Cf", "Cs") or cp == 0:
            stats["control_removed"] += 1
        elif ch == " ":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


_PAGE_NUM = re.compile(r"^\s*(?:page\s*)?[-–—]?\s*\d{1,4}\s*(?:/|of|sur)?\s*\d{0,4}\s*[-–—]?\s*$", re.I)


def _line_key(line: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line.strip().lower()))


def strip_repeated_lines(pages: list[str], stats: Counter | None = None) -> list[str]:
    """Retire en-têtes/pieds répétés (2 premières/dernières lignes présentes sur ≥ 50 % des pages, ≥ 3 pages)."""
    stats = stats if stats is not None else Counter()
    n = len(pages)
    split = [p.split("\n") for p in pages]
    repeated: set[str] = set()
    if n >= 3:
        cnt: Counter = Counter()
        for lines in split:
            nonempty = [ln for ln in lines if ln.strip()]
            cand = {_line_key(x) for x in nonempty[:2] + nonempty[-2:] if len(x.strip()) >= 3}
            cnt.update(cand)
        repeated = {k for k, c in cnt.items() if c >= max(3, n * 0.5)}
    out: list[str] = []
    for lines in split:
        nonempty_idx = [i for i, ln in enumerate(lines) if ln.strip()]
        drop: set[int] = set()
        for i in nonempty_idx[:2] + nonempty_idx[-2:]:
            if _line_key(lines[i]) in repeated or _PAGE_NUM.match(lines[i]):
                drop.add(i)
        if drop:
            stats["header_footer_lines_removed"] += len(drop)
        out.append("\n".join(ln for i, ln in enumerate(lines) if i not in drop))
    return out


# --------------------------------------------------------------------------- motifs d'injection (signalés, jamais retirés)
_INJECTION = {
    "ignore_instructions": re.compile(r"ignore\s+(?:all\s+|any\s+|your\s+|the\s+)?(?:previous|prior|above|earlier|your)\s+"
                                      r"(?:instructions?|prompts?|rules)", re.I),
    "disregard_instructions": re.compile(r"disregard\s+(?:all\s+|the\s+|your\s+)?(?:previous|prior|above)?\s*"
                                         r"(?:instructions?|rules)", re.I),
    "ignore_fr": re.compile(r"(?:ignore[zr]?|oublie[zr]?)\s+(?:toutes?\s+)?(?:tes|vos|les|ses)\s+(?:instructions|consignes)",
                            re.I),
    "ignore_ar": re.compile(r"تجاهل\s+(?:جميع\s+|كل\s+)?(?:التعليمات|الأوامر)"),
    "role_override": re.compile(r"you\s+are\s+now\s+(?:a|an|the)\b|act\s+as\s+(?:a|an)\s+\w+\s+with\s+no", re.I),
    "system_prompt": re.compile(r"(?:reveal|print|show)\s+(?:your\s+)?system\s+prompt|<\s*/?\s*system\s*>", re.I),
    "tool_call": re.compile(r"\b(?:call|invoke|appelle[rz]?)\s+(?:the\s+|la\s+fonction\s+)?(?:decide|post|search_kb|ask_legal)\b"
                            r"|<\s*tool_call|<\|im_start\|>|\[INST\]", re.I),
    "force_decision": re.compile(r"decide\s*\(\s*['\"]?accept", re.I),
}


def scan_injection(text: str, page: int | None = None) -> list[dict]:
    flags = []
    for name, rx in _INJECTION.items():
        for m in rx.finditer(text):
            s = max(0, m.start() - 20)
            flags.append({"pattern": name, "page": page, "snippet": text[s:m.end() + 20].replace("\n", " ")[:120]})
            if len(flags) >= 50:
                return flags
    return flags


# --------------------------------------------------------------------------- langue
_AR_RANGE = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
_FR_WORDS = set("le la les des du de un une et est sont dans pour par sur avec que qui au aux ce cette ces en ou "
                "ne pas il elle nous vous sera être article loi décret conformément présent".split())
_EN_WORDS = set("the of and to in is are for by on with that which shall this be as or an at from not it its "
                "article law act section".split())


def detect_language(text: str) -> str:
    """Heuristique : 'ar' (proportion de lettres arabes), sinon 'fr' / 'en' par mots grammaticaux, sinon 'und'."""
    sample = text[:20000]
    letters = [c for c in sample if c.isalpha()]
    if len(letters) < 20:
        return "und"
    if sum(1 for c in letters if _AR_RANGE.match(c)) / len(letters) > 0.3:
        return "ar"
    words = re.findall(r"[^\W\d_]+", sample.lower())
    fr = sum(1 for w in words if w in _FR_WORDS)
    en = sum(1 for w in words if w in _EN_WORDS)
    if fr == en == 0:
        return "und"
    return "fr" if fr > en else "en"


# --------------------------------------------------------------------------- analyseur lexical
_AR_DIAC = re.compile("[ً-ٰٟۖ-ۭـ]")  # voyelles brèves, signes coraniques, tatwīl
_AR_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي",
                         **{chr(0x0660 + i): str(i) for i in range(10)}, **{chr(0x06F0 + i): str(i) for i in range(10)}})
_TOKEN = re.compile(r"[\w]+", re.U)
_STOP = set("le la les des du de un une et est sont dans pour par sur avec que qui au aux ce cette ces en ou ne pas il "
            "elle the of and to in is are for by on with that this be as or an at from it its a l d s qu "
            "في من على الى إلى عن مع هذا هذه التي الذي او أو و ان أن".split())


_local = threading.local()


def _stemmer(lang: str):  # noqa: ANN202
    """Un stemmer PAR THREAD : les stemmers Snowball gardent un état interne (`current`, curseurs) et ne sont pas réentrants ;
    partagés entre deux jobs d'ingestion simultanés ils lèvent des IndexError aléatoires (constaté avec job_workers=2)."""
    cache = getattr(_local, "stemmers", None)
    if cache is None:
        cache = _local.stemmers = {}
    if lang not in cache:
        import snowballstemmer
        cache[lang] = snowballstemmer.stemmer(lang)
    return cache[lang]


def normalize_arabic(text: str) -> str:
    return _AR_DIAC.sub("", text).translate(_AR_MAP)


# Thésaurus du vocabulaire de crise (requêtes seulement) : relie les termes courants des agents au vocabulaire des
# textes juridiques de protection civile (FR/EN). Il ÉLARGIT la requête lexicale (OR), il ne retire jamais rien.
CRISIS_THESAURUS: dict[str, tuple[str, ...]] = {
    "orsec": ("plan", "urgence", "secours", "déclenchement"),
    "crue": ("catastrophe", "risque", "majeur", "inondation"),
    "crues": ("catastrophe", "risque", "majeur", "inondation"),
    "inondation": ("catastrophe", "risque", "majeur", "crue"),
    "inondations": ("catastrophe", "risque", "majeur", "crue"),
    "flood": ("disaster", "catastrophe", "risque", "majeur"),
    "floods": ("disaster", "catastrophe", "risque", "majeur"),
    "alerte": ("diffusion", "information", "public"),
    "alert": ("warning", "diffusion", "alerte", "public"),
    "warning": ("alert", "alerte", "diffusion"),
    "évacuation": ("secours", "évacuer", "population"),
    "evacuation": ("secours", "évacuation", "population"),
    "populations": ("public", "population"),
    "disaster": ("catastrophe", "risque", "majeur"),
}


def expand_query(text: str) -> str:
    """Ajoute les termes du thésaurus de crise aux mots de la requête (avant analyse)."""
    words = re.findall(r"[\w'’-]+", unicodedata.normalize("NFKC", text).casefold())
    extra = [x for w in words for x in CRISIS_THESAURUS.get(w, ())]
    return text + (" " + " ".join(extra) if extra else "")


def analyze(text: str, *, for_query: bool = False) -> str:
    """NFKC, minuscules, normalisation arabe, racinisation Snowball (arabe pour l'écriture arabe, français pour le latin)."""
    text = normalize_arabic(unicodedata.normalize("NFKC", text)).casefold()
    toks: list[str] = []
    for tok in _TOKEN.findall(text):
        tok = tok.strip("_")
        if not tok or (for_query and (len(tok) < 2 and not tok.isdigit() or tok in _STOP)):
            continue
        stem = _stemmer("arabic" if _AR_RANGE.search(tok) else "french").stemWord(tok)
        toks.append(stem or tok)
    return " ".join(toks)


def article_number(label: str | None) -> str | None:
    """Clé canonique d'un libellé d'article : 'Article 33', 'Art. 33', 'المادة ٣٣' -> '33' ; '5 bis' -> '5bis'."""
    if not label:
        return None
    s = normalize_arabic(unicodedata.normalize("NFKC", label)).casefold()
    if re.search(r"\b(?:premier|1er)\b|الاولي", s):
        return "1"
    m = re.search(r"(\d+(?:[.\-]\d+)*)\s*(bis|ter|quater)?", s)
    return (m.group(1) + (m.group(2) or "")) if m else None


_ART_IN_QUERY = re.compile(r"(?:\barticle|\bart\.?|المادة|مادة)\s*\(?\s*([0-9٠-٩]+(?:\s*(?:bis|ter|quater))?)", re.I)


def article_in_query(query: str) -> str | None:
    m = _ART_IN_QUERY.search(unicodedata.normalize("NFKC", query))
    return article_number(m.group(1)) if m else None
