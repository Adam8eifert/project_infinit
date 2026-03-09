# 📁 extracting/keywords.py
# Wrapper that loads all keywords from sources_config.yaml
# Project: Database of New Religious Movements in the Czech Republic

from typing import List, Dict, Optional, Tuple
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
FALLBACK_MOVEMENT_ID_BY_NAME: Dict[str, int] = {}
FALLBACK_MOVEMENT_NAME_BY_ID: Dict[int, str] = {282: "Neidentifikované hnutí"}
AMBIGUOUS_MOVEMENT_TERMS = {"rodina"}

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
                
                # Flatten known movements (simple list format with diacritics)
                if isinstance(KNOWN_MOVEMENTS, dict):
                    for group_movements in KNOWN_MOVEMENTS.values():
                        if isinstance(group_movements, list):
                            for entry in group_movements:
                                if isinstance(entry, str):
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

def _read_movement_config() -> Tuple[List[str], Dict[str, List[str]]]:
    """Read known movements and aliases from YAML config."""
    known_movements: List[str] = []
    aliases_config: Dict[str, List[str]] = {}

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            if isinstance(config, dict):
                keywords = config.get('keywords', {})
                if isinstance(keywords, dict):
                    known = keywords.get('known_movements', {}).get('new_religious_movements', [])
                    if isinstance(known, list):
                        known_movements = [entry.strip() for entry in known if isinstance(entry, str)]

                    loaded_aliases = keywords.get('movement_aliases', {})
                    if isinstance(loaded_aliases, dict):
                        aliases_config = {
                            name: [alias for alias in aliases if isinstance(alias, str)]
                            for name, aliases in loaded_aliases.items()
                            if isinstance(name, str) and isinstance(aliases, list)
                        }
    except Exception as e:
        logger.warning(f"Failed to load movement config: {e}")

    return known_movements, aliases_config


def _ensure_fallback_movement_maps(
    known_movements: List[str],
    aliases_config: Dict[str, List[str]]
) -> None:
    """Build stable fallback movement ID/name maps for DB-independent matching."""
    if FALLBACK_MOVEMENT_ID_BY_NAME:
        return

    names: List[str] = []
    seen: set[str] = set()

    for movement_name in known_movements + list(aliases_config.keys()):
        normalized = movement_name.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        names.append(movement_name.strip())

    if "Neidentifikované hnutí" not in names:
        names.append("Neidentifikované hnutí")

    next_id = 1000
    for movement_name in names:
        if movement_name == "Neidentifikované hnutí":
            movement_id = 282
        else:
            while next_id == 282:
                next_id += 1
            movement_id = next_id
            next_id += 1

        FALLBACK_MOVEMENT_ID_BY_NAME[movement_name] = movement_id
        FALLBACK_MOVEMENT_NAME_BY_ID[movement_id] = movement_name


def _find_db_movement_by_name(session, Movement, movement_name: str):
    """Find movement by name across legacy and new schemas."""
    query_candidates = []
    if hasattr(Movement, "canonical_name"):
        query_candidates.append("canonical_name")
    if hasattr(Movement, "name"):
        query_candidates.append("name")

    for attr_name in query_candidates:
        try:
            column = getattr(Movement, attr_name)
            movement = session.query(Movement).filter(column == movement_name).first()
            if movement is not None:
                return movement
        except Exception as query_error:
            logger.debug(f"Movement DB lookup skipped for '{movement_name}' on '{attr_name}': {query_error}")
            return None

    return None


def _movement_name_from_row(movement) -> Optional[str]:
    """Return canonical or legacy movement name from ORM row."""
    movement_name = getattr(movement, "canonical_name", None) or getattr(movement, "name", None)
    return str(movement_name) if movement_name else None


def _resolve_movement_id(movement_name: str, session=None, Movement=None) -> Optional[int]:
    """Resolve movement name to DB ID when possible, otherwise fallback ID."""
    if session is not None and Movement is not None:
        movement = _find_db_movement_by_name(session, Movement, movement_name)
        if movement is not None and getattr(movement, "id", None) is not None:
            return int(movement.id)  # type: ignore[arg-type]

    return FALLBACK_MOVEMENT_ID_BY_NAME.get(movement_name)


def _contains_term(text: str, term: str) -> bool:
    """Check term/phrase presence with word boundaries (avoids substring false positives)."""
    normalized_term = (term or "").strip().lower()
    if not normalized_term:
        return False

    escaped = re.escape(normalized_term).replace(r"\ ", r"\s+")
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None

def match_movement_from_text(text: str, min_score: int = 90) -> Optional[int]:
    """
    Match text to a known movement using keywords and aliases.
    Returns movement_id from database if found, None otherwise.
    
    Matching strategy:
    1. Direct substring match on canonical_name (with diacritics)
    2. Check movement aliases (from config, with diacritics)
    3. Fuzzy matching on canonical_name and aliases
    4. Return movement_id if match found
    
    Args:
        text: Text to search for movement mentions
        min_score: Minimum fuzzy match score (0-100, default 80)
    
    Returns:
        movement_id (int) or None
    """
    if not text:
        return None
        
    try:
        text_lower = text.lower()
        known_movements, aliases_config = _read_movement_config()
        _ensure_fallback_movement_maps(known_movements, aliases_config)

        session = None
        Movement = None
        try:
            from database.db_loader import DBConnector, Movement as MovementModel
            db = DBConnector()
            session = db.get_session()
            Movement = MovementModel
        except Exception as db_error:
            logger.debug(f"Movement DB lookup unavailable, using fallback map: {db_error}")

        try:
            # Strategy 1: Direct bounded match on canonical names
            for movement_name in known_movements:
                movement_norm = movement_name.strip().lower()
                if movement_norm in AMBIGUOUS_MOVEMENT_TERMS:
                    continue
                if _contains_term(text_lower, movement_norm):
                    resolved_id = _resolve_movement_id(movement_name, session, Movement)
                    if resolved_id is not None:
                        return resolved_id

            # Strategy 2: Check aliases (bounded; avoid tiny alias noise)
            for movement_name, aliases_list in aliases_config.items():
                for alias in aliases_list:
                    alias_norm = alias.strip().lower()
                    if len(alias_norm) < 3:
                        continue
                    if alias_norm in AMBIGUOUS_MOVEMENT_TERMS:
                        continue
                    if _contains_term(text_lower, alias_norm):
                        resolved_id = _resolve_movement_id(movement_name, session, Movement)
                        if resolved_id is not None:
                            return resolved_id
            return None
        finally:
            if session is not None:
                session.close()

    except Exception as e:
        logger.error(f"Error matching movement: {e}")
        return None


def get_movement_name_by_id(movement_id: int) -> Optional[str]:
    """Get canonical name for a movement ID"""
    try:
        from database.db_loader import DBConnector, Movement
        db = DBConnector()
        session = db.get_session()
        try:
            movement = session.query(Movement).filter(Movement.id == movement_id).first()
            if movement is not None:
                movement_name = _movement_name_from_row(movement)
                if movement_name:
                    return movement_name
        finally:
            session.close()

        if movement_id == 282:
            return "Neidentifikované hnutí"

        if not FALLBACK_MOVEMENT_NAME_BY_ID:
            known_movements, aliases_config = _read_movement_config()
            _ensure_fallback_movement_maps(known_movements, aliases_config)

        return FALLBACK_MOVEMENT_NAME_BY_ID.get(movement_id)
    except Exception:
        if movement_id == 282:
            return "Neidentifikované hnutí"
        return FALLBACK_MOVEMENT_NAME_BY_ID.get(movement_id)


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
        if _contains_term(text, kw):
            hits += 1

    for movement in ALL_KNOWN_MOVEMENTS:
        movement_normalized = movement.strip().lower()
        if movement_normalized in AMBIGUOUS_MOVEMENT_TERMS:
            continue
        if _contains_term(text, movement):
            hits += 2  # boost known entities

    return hits >= min_hits


def is_excluded_content(text: str) -> bool:
    """
    Checks whether text should be excluded based on noise terms or context patterns.
    """
    text = text.lower()

    # Simple term exclusion
    for term in EXCLUDE_TERMS:
        if _contains_term(text, term):
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
