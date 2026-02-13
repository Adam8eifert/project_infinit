# 📁 extracting/keywords.py
# Wrapper that loads all keywords from sources_config.yaml
# Project: Database of New Religious Movements in the Czech Republic

from typing import List, Dict
import re
import os
import yaml
import logging

logger = logging.getLogger(__name__)

# ============================================================
# LOAD CONFIG FROM sources_config.yaml
# ============================================================

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "sources_config.yaml")

# Default fallback values
SEARCH_TERMS: List[str] = []
EXCLUDE_TERMS: List[str] = []
EXCLUDE_CONTEXT_PATTERNS: List[str] = []
KNOWN_MOVEMENTS: Dict = {}
YEAR_PATTERNS: List[str] = []
ALL_KNOWN_MOVEMENTS: List[str] = []

def _load_keywords_config() -> None:
    """Load keywords configuration from sources_config.yaml"""
    global SEARCH_TERMS, EXCLUDE_TERMS, EXCLUDE_CONTEXT_PATTERNS, KNOWN_MOVEMENTS, YEAR_PATTERNS, ALL_KNOWN_MOVEMENTS
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf8") as f:
            cfg = yaml.safe_load(f) or {}
            if not isinstance(cfg, dict):
                logger.warning(f"⚠️  Config is not a dict, got {type(cfg).__name__}")
                return
            kw_cfg = cfg.get("keywords", {})
            
            if isinstance(kw_cfg, dict):
                SEARCH_TERMS = kw_cfg.get("required", [])
                EXCLUDE_TERMS = kw_cfg.get("exclude", [])
                EXCLUDE_CONTEXT_PATTERNS = kw_cfg.get("exclude_context_patterns", [])
                KNOWN_MOVEMENTS = kw_cfg.get("known_movements", {})
                YEAR_PATTERNS = kw_cfg.get("year_patterns", [])
                
                # Flatten known movements
                if isinstance(KNOWN_MOVEMENTS, dict):
                    ALL_KNOWN_MOVEMENTS = [
                        movement
                        for group in KNOWN_MOVEMENTS.values()
                        for movement in group
                    ]
                
                logger.info(f"✓ Loaded {len(SEARCH_TERMS)} search terms from sources_config.yaml")
    except FileNotFoundError:
        logger.error(f"❌ Config file not found: {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"❌ Error loading keywords config: {e}")

# Load on import
_load_keywords_config()

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
