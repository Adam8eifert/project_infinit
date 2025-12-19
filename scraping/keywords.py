# 📁 scraping/keywords.py
# Centralized keywords and filters for all spiders

# Basic keywords for searching
SEARCH_TERMS = [
    "sekta",
    "nové náboženské hnutí",
    "nová náboženská hnutí",
    "nové duchovní hnutí",
    "nová duchovní hnutí",
    "náboženská skupina",
    "náboženská komunita",
    "alternativní náboženství",
    "kontroverzní náboženská společnost",
    "destruktivní kult",
    "kult",
    "nové spirituální hnutí"
]

# Words to exclude from searching
EXCLUDE_TERMS = [
    "-politika",
    "-film",
    "-hudba",
    "-hra",
    "-počítačová"
]

# Known religious groups for better identification
KNOWN_MOVEMENTS = [
    "Hnutí Grálu",
    "Církev sjednocení",
    "Scientologická církev",
    "Svědkové Jehovovi",
    "Hare Kršna",
    "Církev Ježíše Krista Svatých posledních dnů",
    "Buddhismus Diamantové cesty",
    "Satanská církev",
    "Imanuelité",
    "Svobodná církev reformovaná"
]

# Regular expressions for finding founding dates
YEAR_PATTERNS = [
    r"založen[aáoý]\s+v\s+roce\s+(\d{4})",
    r"vznik(?:lo|la|l)\s+v\s+roce\s+(\d{4})",
    r"od\s+roku\s+(\d{4})",
    r"registrován[aáoý]\s+v\s+(?:ČR|České\s+republice)\s+v\s+roce\s+(\d{4})"
]

def contains_relevant_keywords(text: str) -> bool:
    """
    Kontroluje, zda text obsahuje relevantní klíčová slova.
    
    Args:
        text: Text k analýze
    
    Returns:
        bool: True pokud text obsahuje relevantní klíčová slova
    """
    text = text.lower()
    return any(keyword.lower() in text for keyword in SEARCH_TERMS + KNOWN_MOVEMENTS)

def is_excluded_content(text: str) -> bool:
    """
    Kontroluje, zda text obsahuje vyloučená slova.
    
    Args:
        text: Text k analýze
    
    Returns:
        bool: True pokud text obsahuje vyloučená slova
    """
    text = text.lower()
    exclude_words = [term.strip("-").lower() for term in EXCLUDE_TERMS]
    return any(word in text for word in exclude_words)
