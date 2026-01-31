# 📁 extracting/keywords.py
# Centralized keywords, filters and patterns for all spiders
# Project: Database of New Religious Movements in the Czech Republic

from typing import List, Dict
import re
import os
import yaml

# ============================================================
# SEARCH TERMS (neutral + critical + academic)
# ============================================================

SEARCH_TERMS: List[str] = [
    # Critical / media-used
    "sekta",
    "kult",
    "destruktivní kult",
    "kontroverzní náboženská společnost",

    # Neutral / academic
    "náboženské hnutí",
    "duchovní hnutí",
    "spirituální hnutí",
    "nové náboženství",
    "nová religiozita",
    "alternativní náboženství",
    "alternativní religiozita",
    "ezoterické hnutí",
    "esoterické hnutí",

    # Institutional / legal
    "náboženská skupina",
    "náboženská komunita",
    "náboženská společnost",
    "registrovaná náboženská společnost",
    "neregistrovaná náboženská společnost",
    "církev a náboženská společnost",
    "duchovní centrum",
    "náboženský směr",

    # Sociological / abbreviations
    "nová náboženská hnutí",
    "nové náboženské hnutí",
    "NNH",
    "NRM",
    "NDH",
    "nové duchovní hnutí",
    "nová duchovní hnutí",
    "nové spirituální hnutí"
]

# ============================================================
# EXCLUDED TERMS (noise filtering)
# ============================================================

EXCLUDE_TERMS: List[str] = [
    # Entertainment & pop culture
    "film",
    "seriál",
    "videohra",
    "pc hra",
    "hudební skupina",
    "kapela",
    "album",
    "festival",

    # Tech / unrelated
    "software",
    "aplikace",
    "počítačová hra",

    # Politics & current events (noise reduction)
    "politika",
    "politiky",
    "volby",
    "prezident",
    "vláda",
    "parlament"
]

# Contextual exclude patterns (regex)
EXCLUDE_CONTEXT_PATTERNS: List[str] = [
    r"recenze\s+filmu",
    r"hra\s+roku",
    r"herní\s+recenze",
    r"soundtrack",
    r"trailer"
]

# ============================================================
# KNOWN RELIGIOUS MOVEMENTS (for entity boosting)
# ============================================================

KNOWN_MOVEMENTS = {
    "new_religious_movements": [
        "Hnutí Grálu",
        "Církev sjednocení",
        "Scientologická církev",
        "Buddhismus Diamantové cesty",
        "Imanuelité",
        "Raeliáni",
        "Osho",
        "Sahadža jóga",
        "Univerzální život",
        "Vesmírní lidé",
        "Universe People",
        "Děti Boží",
        "Rodina",
        "Dvanáct kmenů",
        "AllatRa",
        "Fa-lun-kung",
        "Anastasianismus",
        "Transcendentální meditace",
        "Subud",
        "Škola ekonomické vědy",
        "Teosofická společnost",
        "Baháʼí víra",
        "Hnutí Hare Kršna",
        "Církev Ježíše Krista Svatých posledních dnů",
        "Svědkové Jehovovi",
        "Satanská církev",
        "Chrám Satanův",
        "Církev univerzální a vítězná",
        "Církev všech světů",
        "Církev Všemohoucího Boha",
        "Ježíšova armáda",
        "Jediismus",
        "Křesťanská věda",
        "LaVeyův satanismus",
        "Kristadelfiáni",
        "Řád ochránců Boží vůle na Zemi",
        "Služebníci světla",
        "Společenství Josefa Zezulky",
        "Ánanda Márga",
        "Cesta Guru Járy",
        "Šinčchondži",
        "Tvořivá společnost",
        "The Revelation Spiritual Home",
        "Kruh přátel Bruna Gröninga",
        "Brahma Kumaris",
        "Protestantská církev Svaté korony",
        "Konopná církev",
        "Církev militantního ateismu",
        "Ček Árya Sabhá – Árjasamádž",
        "Silvova metoda",
        "Zodiakální škola",
        "Poetrie",
        "Kuřimská sekta",
        "Škola Aria",
        "Arnold Varvarinec",
        "Zprávy z galaxie",
        "Novija gána sepata",
        "Science 21",
        "Společenství legitimních věřitelů České republiky",
        "Boží rodina",
        "Radomír Wolf",
        "Rezonance",
        "AROPAL",
        "Loving Hut",
        "Bhakti Marga",
        "Život v srdci",
        "Zlatá éra",
        "Plaváček",
        "Slovanská košile",
        "O9A",
        "TVIND",
        "Jarilo",
        "Most ke svobodě",
        "Alan Jarkovský",
        "Jóga v denním životě",
        "Život v Radosti",
        "Dohnalité",
        "Avenna",
        "Ariadné",
        "Happy Science",
        "Tao Jóga",
        "V lásce spolu",
        "Mlýn Radunka",
        "Farma Lovětín"
    
    ]
}

# Flattened list for easier matching
ALL_KNOWN_MOVEMENTS: List[str] = [
    movement
    for group in KNOWN_MOVEMENTS.values()
    for movement in group
]

# ============================================================
# YEAR / FOUNDING DATE REGEX PATTERNS
# ============================================================

YEAR_PATTERNS: List[str] = [
    r"založen[aáoý]\s+v\s+roce\s+(\d{4})",
    r"vznik(?:lo|la|l)\s+v\s+roce\s+(\d{4})",
    r"vznikl[ao]?\s+kolem\s+roku\s+(\d{4})",
    r"od\s+roku\s+(\d{4})",
    r"působí\s+od\s+roku\s+(\d{4})",
    r"činnost\s+zahájena\s+v\s+roce\s+(\d{4})",
    r"registrován[aáoý]\s+v\s+(?:ČR|České\s+republice)\s+v\s+roce\s+(\d{4})",
    r"zaregistrován[ao]?\s+dne\s+\d{1,2}\.\s*\d{1,2}\.\s*(\d{4})"
]

# ============================================================
# CONFIG OVERRIDE (load from extracting/sources_config.yaml when present)
# ============================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sources_config.yaml")

try:
    with open(CONFIG_PATH, "r", encoding="utf8") as _f:
        _cfg = yaml.safe_load(_f) or {}
        # Be defensive: YAML may be a list or other non-mapping. Only call .get if it's a dict.
        if isinstance(_cfg, dict):
            _kw = _cfg.get("keywords", {})
        else:
            _kw = {}

        # Only override when the YAML block is a mapping - be defensive about types
        if isinstance(_kw, dict):
            SEARCH_TERMS = _kw.get("required", SEARCH_TERMS)
            EXCLUDE_TERMS = _kw.get("exclude", EXCLUDE_TERMS)
            EXCLUDE_CONTEXT_PATTERNS = _kw.get("exclude_context_patterns", EXCLUDE_CONTEXT_PATTERNS)
            KNOWN_MOVEMENTS = _kw.get("known_movements", KNOWN_MOVEMENTS)
            YEAR_PATTERNS = _kw.get("year_patterns", YEAR_PATTERNS)

            # flatten known movements if it's a mapping
            if isinstance(KNOWN_MOVEMENTS, dict):
                ALL_KNOWN_MOVEMENTS = [
                    movement
                    for group in KNOWN_MOVEMENTS.values()
                    for movement in group
                ]
except FileNotFoundError:
    # no config file — keep the hard-coded defaults
    pass
except Exception:
    # If yaml is invalid or other error, keep defaults but warn in logs when possible
    pass

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def contains_relevant_keywords(text: str, min_hits: int = 1) -> bool:
    """
    Checks whether text contains relevant religious movement keywords.
    Known movements have higher weight.
    """
    text = text.lower()
    hits = 0

    for kw in SEARCH_TERMS:
        if kw.lower() in text:
            hits += 1

    for movement in ALL_KNOWN_MOVEMENTS:
        if movement.lower() in text:
            hits += 2  # boost known entities

    return hits >= min_hits


def is_excluded_content(text: str) -> bool:
    """
    Checks whether text should be excluded based on noise terms or context patterns.
    """
    text = text.lower()

    # Simple term exclusion
    for term in EXCLUDE_TERMS:
        if term in text:
            return True

    # Contextual regex exclusion
    for pattern in EXCLUDE_CONTEXT_PATTERNS:
        if re.search(pattern, text):
            return True

    return False


def extract_years(text: str) -> List[str]:
    """
    Extracts founding or registration years from text.
    """
    years = []

    for pattern in YEAR_PATTERNS:
        matches = re.findall(pattern, text.lower())
        years.extend(matches)

    return list(set(years))
