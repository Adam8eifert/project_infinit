# 📁 extracting/keywords.py
# Wrapper that loads all keywords from sources_config.yaml
# Project: Database of New Religious Movements in the Czech Republic

from typing import List, Dict, Optional
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
                
                # Flatten known movements (new format: [{canonical, display}, ...])
                if isinstance(KNOWN_MOVEMENTS, dict):
                    for group_movements in KNOWN_MOVEMENTS.values():
                        if isinstance(group_movements, list):
                            for entry in group_movements:
                                if isinstance(entry, dict):
                                    display = entry.get('display', '')
                                    if display:
                                        ALL_KNOWN_MOVEMENTS.append(display)
                                elif isinstance(entry, str):
                                    # Fallback pro starý formát
                                    ALL_KNOWN_MOVEMENTS.append(entry)
                
                logger.info(f"✓ Loaded {len(SEARCH_TERMS)} search terms, {len(ALL_KNOWN_MOVEMENTS)} known movements from sources_config.yaml")
    except FileNotFoundError:
        logger.error(f"❌ Config file not found: {CONFIG_PATH}")
    except Exception as e:
        logger.error(f"❌ Error loading keywords config: {e}")

# Load on import
_load_keywords_config()

# ============================================================
# MOVEMENT MATCHING WITH FUZZY SEARCH
# ============================================================

def match_movement_from_text(text: str, min_score: int = 80) -> Optional[int]:
    """
    Match text to a known movement using keywords and aliases.
    Returns movement_id from database if found, None otherwise.
    
    Matching strategy:
    1. Direct substring match on display_name (with diacritics)
    2. Check movement aliases (config, with diacritics)
    3. Fuzzy matching on display_name and aliases
    4. Return movement_id by canonical_name lookup
    
    Args:
        text: Text to search for movement mentions
        min_score: Minimum fuzzy match score (0-100, default 80)
    
    Returns:
        movement_id (int) or None
    """
    if not text:
        return None
        
    try:
        from fuzzywuzzy import fuzz
        from database.db_loader import DBConnector, Movement
        
        text_lower = text.lower()
        
        # Load movement config from YAML
        display_to_canonical: Dict[str, str] = {}
        canonical_to_display: Dict[str, str] = {}
        aliases_config: Dict[str, List[str]] = {}
        
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                import yaml
                config = yaml.safe_load(f)
                if config and isinstance(config, dict):
                    keywords = config.get('keywords', {})
                    if isinstance(keywords, dict):
                        # Load known movements (new format: [{canonical, display}, ...])
                        known = keywords.get('known_movements', {}).get('new_religious_movements', [])
                        for entry in known:
                            if isinstance(entry, dict):
                                canonical = entry.get('canonical', '').strip()
                                display = entry.get('display', '').strip()
                                if canonical and display:
                                    display_to_canonical[display.lower()] = canonical
                                    canonical_to_display[canonical] = display
                        
                        # Load aliases (canonical_slug -> [display aliases])
                        aliases_config = keywords.get('movement_aliases', {})
        except Exception as e:
            logger.warning(f"Failed to load movement config: {e}")
        
        # Connect to database
        db = DBConnector()
        session = db.get_session()
        
        best_match_id = None
        best_score = 0
        
        # Strategy 1: Direct substring match on display names
        for display_name, canonical in display_to_canonical.items():
            if display_name in text_lower:
                # Find movement by canonical_name
                movement = session.query(Movement).filter(Movement.canonical_name == canonical).first()
                if movement is not None:
                    session.close()
                    return int(movement.id)  # type: ignore[arg-type]
        
        # Strategy 2: Check aliases
        for canonical_slug, aliases_list in aliases_config.items():
            for alias in aliases_list:
                if isinstance(alias, str) and alias.lower() in text_lower:
                    # Find movement by canonical_name
                    movement = session.query(Movement).filter(Movement.canonical_name == canonical_slug).first()
                    if movement is not None:
                        session.close()
                        return int(movement.id)  # type: ignore[arg-type]
        
        # Strategy 3: Fuzzy matching on display names
        for display_name, canonical in display_to_canonical.items():
            score = fuzz.partial_ratio(display_name, text_lower)
            if score >= min_score:
                movement = session.query(Movement).filter(Movement.canonical_name == canonical).first()
                if movement is not None and score > best_score:
                    best_score = score
                    best_match_id = int(movement.id)  # type: ignore[arg-type]
        
        # Strategy 4: Fuzzy matching on aliases
        if best_match_id is None:
            for canonical_slug, aliases_list in aliases_config.items():
                for alias in aliases_list:
                    if isinstance(alias, str):
                        score = fuzz.partial_ratio(alias.lower(), text_lower)
                        if score >= min_score:
                            movement = session.query(Movement).filter(Movement.canonical_name == canonical_slug).first()
                            if movement is not None and score > best_score:
                                best_score = score
                                best_match_id = int(movement.id)  # type: ignore[arg-type]
        
        session.close()
        return best_match_id
        
    except ImportError:
        logger.warning("fuzzywuzzy not installed - movement matching disabled")
        return None
    except Exception as e:
        logger.error(f"Error matching movement: {e}")
        return None


def get_movement_name_by_id(movement_id: int) -> Optional[str]:
    """Get canonical name for a movement ID"""
    try:
        from database.db_loader import DBConnector, Movement
        db = DBConnector()
        session = db.get_session()
        movement = session.query(Movement).filter(Movement.id == movement_id).first()
        # Explicit None check for SQLAlchemy Column type
        if movement is not None and movement.canonical_name is not None:
            name = str(movement.canonical_name)
        else:
            name = None
        session.close()
        return name
    except Exception:
        return None


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
