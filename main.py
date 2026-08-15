# 📁 main.py
# ETL Pipeline for Project Infinit
# New simplified schema: Articles → Movements, Persons, Locations

import subprocess
import os
import re
import unicodedata
import yaml
import builtins
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from sqlalchemy import or_
from database.db_loader import DBConnector, Article, Movement, Person, Location, SentimentLabel, RiskLevel
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader
from processing.relevance_report import print_suspicious_articles_report, export_suspicious_articles_csv
from fuzzywuzzy import fuzz
from logging_utils import configure_project_logger
from extracting.configured_collectors import run_configured_collectors


PIPELINE_LOGGER = configure_project_logger("pipeline.main", "pipeline/main.log")


def print(*args, **kwargs):
    """Mirror pipeline console output to a dedicated pipeline log file."""
    builtins.print(*args, **kwargs)
    try:
        sep = kwargs.get("sep", " ")
        message = sep.join(str(arg) for arg in args)
        if message:
            PIPELINE_LOGGER.info(message)
    except Exception:
        return


def run_configured_acquisition_sources():
    """Run config-driven sitemap/API/Wayback collectors before Scrapy spiders."""
    print("📦 Running config-driven acquisition sources...")
    summary = run_configured_collectors()
    if summary:
        print(f"   ✅ Collected from {len(summary)} configured source(s): {summary}")
    else:
        print("   ℹ️  No enabled sitemap/API/Wayback sources found")


def run_google_trends(save_to_db=True):
    """Run the Google Trends collector at the end of the pipeline."""
    print("📈 Running Google Trends collection...")
    try:
        from trends.google_trends_collector import GoogleTrendsCollector
    except ImportError as e:
        print(f"   ⚠️  Google Trends module not available: {e}")
        return

    try:
        collector = GoogleTrendsCollector()
        collector.run(save_to_db=save_to_db)
        print("   ✅ Google Trends collection completed")
    except Exception as e:
        print(f"   ❌ Google Trends collection failed: {e}")


def run_spiders():
    """Run all defined Scrapy spiders for data collection"""
    spiders = [
        "extracting/rss_spider.py",              # Universal RSS spider
        "extracting/api_spider.py",              # Universal API spider
        "extracting/sekty_tv_spider.py",         # Sekty.TV web scraper
        "extracting/idnes_archive_spider.py",    # iDNES archive rubric scraper
        "extracting/social_media_spider.py",     # Reddit spider
        "extracting/medium_seznam_spider.py",    # Medium.seznam.cz
        "extracting/google_spider.py"            # Google News search
    ]
    
    print("🕷️  Starting spiders...")
    for spider in spiders:
        try:
            print(f"\n🚀 Running spider: {spider}")
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path(__file__).parent)
            subprocess.run(["scrapy", "runspider", spider], check=True, env=env)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running {spider}: {e}")
            continue
        except FileNotFoundError as e:
            print(f"⚠️  Spider file not found: {spider}")
            continue
    
    print("\n✅ Spider phase completed")


def create_db():
    """Initialize database with new schema"""
    try:
        print("🗄️  Creating database tables...")
        db = DBConnector()
        db.create_tables()
        print("✅ Database tables created successfully")
        return db
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise


def import_csv_data(db):
    """Import CSV files from spiders to database"""
    try:
        print("\n📊 Importing CSV data...")
        importer = CSVtoDatabaseLoader(db)
        
        csv_dir = Path("export/csv")
        csv_files = list(csv_dir.glob("*_raw.csv"))
        
        if not csv_files:
            print("⚠️  No CSV files found for import")
            return
        
        print(f"📁 Found {len(csv_files)} CSV files")
        
        total_imported = 0
        for csv_file in csv_files:
            try:
                count = importer.load_csv_to_articles(str(csv_file))
                total_imported += count
                print(f"   ✅ {csv_file.name}: {count} articles")
            except Exception as e:
                print(f"   ❌ Error processing {csv_file.name}: {e}")
                continue
        
        print(f"\n✅ CSV import completed: {total_imported} total articles imported")
        return total_imported
    except Exception as e:
        print(f"❌ Error importing CSV data: {e}")
        raise


def analyze_sentiment_and_risk(db):
    """Run NLP analysis on articles"""
    try:
        print("\n🧠 Running NLP analysis...")
        analyzer = CzechTextAnalyzer()
        
        session = db.get_session()
        articles = session.query(Article).filter(
            or_(
                Article.sentiment_label.is_(None),
                Article.sentiment_score.is_(None),
                Article.risk_level.is_(None),
                Article.risk_score.is_(None),
            )
        ).all()
        
        print(f"📝 Analyzing {len(articles)} articles...")
        
        analyzed = 0
        for article in articles:
            try:
                # Sentiment analysis
                sentiment_result = analyzer.analyze_sentiment(article.content)
                if sentiment_result:
                    sentiment_value = float(sentiment_result.get('score', 0.0))
                    sentiment_label_raw = str(sentiment_result.get('label', 'neutral')).lower()
                    if sentiment_label_raw not in SentimentLabel._value2member_map_:
                        sentiment_label_raw = 'neutral'

                    article.sentiment_score = sentiment_value
                    article.sentiment_label = SentimentLabel(sentiment_label_raw)
                
                # Risk analysis (basic - can be expanded)
                risk_score = float(analyzer.calculate_risk_score(article.content))
                article.risk_score = risk_score
                risk_level_raw = analyzer.get_risk_level(risk_score)
                if risk_level_raw not in RiskLevel._value2member_map_:
                    risk_level_raw = 'low'
                article.risk_level = RiskLevel(risk_level_raw)
                
                analyzed += 1
                
                if analyzed % 50 == 0:
                    print(f"   {analyzed} articles analyzed...")
            
            except Exception as e:
                print(f"   ⚠️  Error analyzing article {article.id}: {e}")
                continue
        
        session.commit()
        session.close()
        
        print(f"✅ NLP analysis completed: {analyzed} articles analyzed")
        return analyzed
    except Exception as e:
        print(f"❌ Error in NLP analysis: {e}")
        raise


def prune_irrelevant_articles(db):
    """Remove irrelevant articles and normalize wrong movement links."""
    try:
        from extracting.keywords import (
            contains_relevant_keywords,
            is_excluded_content,
            match_movement_from_text,
        )

        print("\n🧹 Pruning irrelevant articles...")
        session = db.get_session()
        candidates = session.query(Article).all()

        removed = 0
        relinked = 0
        unlinked = 0
        for article in candidates:
            combined = f"{article.title or ''} {article.content or ''}".strip()
            if not combined:
                session.delete(article)
                removed += 1
                continue

            matched_movement_id = match_movement_from_text(combined, min_score=90)
            has_keywords = contains_relevant_keywords(combined, min_hits=2)

            if is_excluded_content(combined) or (matched_movement_id is None and not has_keywords):
                session.delete(article)
                removed += 1
                continue

            if matched_movement_id is None:
                if article.movements:
                    article.movements.clear()
                    unlinked += 1
                continue

            matched_movement = session.query(Movement).filter(Movement.id == matched_movement_id).first()
            if matched_movement is None:
                continue

            if len(article.movements) != 1 or matched_movement not in article.movements:
                article.movements = [matched_movement]
                relinked += 1

        session.commit()
        session.close()

        print(
            f"✅ Irrelevant prune completed: removed {removed}, "
            f"relinked {relinked}, unlinked {unlinked} / {len(candidates)}"
        )
        return removed
    except Exception as e:
        print(f"⚠️  Error pruning irrelevant articles: {e}")
        return 0


def _normalize_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _clean_person_name(raw_name: str) -> str:
    name = (raw_name or "").strip()
    name = name.replace("/", " ")
    name = re.sub(r"\s*-\s*", "-", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" .,:;!?\"'()[]{}")


def _is_valid_person_name(name: str) -> bool:
    if not name:
        return False
    if "##" in name:
        return False

    normalized = _normalize_text(name)
    if not normalized:
        return False

    blocked = {
        "se", "jeho", "jeji", "pan", "pani", "rod", "bro", "listu", "alla"
    }
    if normalized in blocked:
        return False

    tokens = [token for token in normalized.split() if token]
    if len(tokens) < 2:
        return False
    if any(len(token) < 2 for token in tokens):
        return False
    return True


def _stem_name_token(token: str) -> str:
    """Remove Czech grammatical suffixes from a name token."""
    token_lower = token.lower()
    suffixes = [
        "ove", "ova", "ovi", "ove", "ech", "ich", "emu", "eho", "ami", "emi",
        "ou", "em", "om", "mi", "mu", "ho", "ch", "y", "i", "a", "e", "u"
    ]
    stem = token_lower
    for suffix in suffixes:
        if len(stem) > 4 and stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    return stem


def _tokenize_person(name: str) -> List[str]:
    normalized = _normalize_text(name)
    return [token for token in normalized.split() if token]


def _is_same_person_name(name_a: str, name_b: str, analyzer=None, debug: bool = False) -> bool:
    """
    Check if two person names refer to the same person.
    Handles Czech declension variants like "Jana Kyslíková" vs "Jany Kyslíkové".
    """
    norm_a = _normalize_text(name_a)
    norm_b = _normalize_text(name_b)

    if debug:
        print(f"[DEBUG] Comparing: '{name_a}' vs '{name_b}'")

    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True

    tokens_a = _tokenize_person(name_a)
    tokens_b = _tokenize_person(name_b)
    if len(tokens_a) < 1 or len(tokens_b) < 1:
        if debug:
            print(f"[DEBUG] Not enough tokens: {len(tokens_a)} vs {len(tokens_b)}")
        return False

    # For single token names, just compare them
    if len(tokens_a) == 1 and len(tokens_b) == 1:
        ratio = fuzz.ratio(tokens_a[0].lower(), tokens_b[0].lower())
        if debug:
            print(f"[DEBUG] Single token: {ratio}")
        return ratio >= 85

    # For two+ token names: compare first 3 chars of first name + first 3 chars of last name
    first_a_short = tokens_a[0].lower()[:3]
    last_a_short = tokens_a[-1].lower()[:3]
    first_b_short = tokens_b[0].lower()[:3]
    last_b_short = tokens_b[-1].lower()[:3]

    # Also compute fuzzy
    full_score = fuzz.token_set_ratio(norm_a, norm_b)
    
    if debug:
        print(f"[DEBUG]   1st3: {first_a_short}vs{first_b_short}, Last3: {last_a_short}vs{last_b_short}, Full={full_score}")

    # Match if first 3 chars AND last 3 chars are similar
    first_match = fuzz.ratio(first_a_short, first_b_short) >= 60
    last_match = fuzz.ratio(last_a_short, last_b_short) >= 80
    
    if first_match and last_match:
        if debug:
            print(f"[DEBUG] MATCH: first and last 3-char match")
        return True
    
    # Fallback: very high token_set_ratio
    if full_score >= 92:
        if debug:
            print(f"[DEBUG] MATCH: full_score >= 92")
        return True

    if debug:
        print(f"[DEBUG] NO MATCH")
    return False


def _is_bad_person_entity(name: str) -> bool:
    """
    Detect poorly extracted person entities from NER.
    Examples: "Terén Kristiny Cirokové", "Boží Jan", "Josef SV", "Buddha Shiva Yaktshi"
    """
    if not name:
        return True
    
    # Check for whitespace-delimited corruption patterns
    patterns = [
        r'Boží\s',  # "Boží X" pattern (likely error)
        r'\s(SV|FA|ST|AB)$',  # Abbreviations at end (likely corrupted)
        r'Buddha\s+Shiva',  # Multiple titles
        r'Panem\s',  # "Panem X" (Latin nominative error)
        r'Terén\s',  # "Terén X" (place instead of person)
        r'^Commona\s',  # Old English proper adjective mistagged
    ]
    
    for pattern in patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return True
    
    # Too many words (likely corruption)
    words = name.split()
    if len(words) > 5:
        return True
    
    # Single letter or very short names are suspicious
    if len(name.strip()) <= 3:
        return True
    
    return False


def _load_entity_linking_config() -> Tuple[List[str], Dict[str, List[str]], Dict[str, str], Dict[str, List[str]], Dict[str, int]]:
    """Load known movements, movement categories, persons and their aliases from config.

    This function now uses the `extracting.config_loader` KeywordsAccessor which
    supports both the merged `keywords.movements` layout and the legacy layout.
    """
    from extracting.config_loader import get_config_loader, KeywordsAccessor

    loader = get_config_loader()
    ka = KeywordsAccessor(loader.config)
    movements_map = ka.movements_map()

    # Build outputs expected by the rest of the pipeline
    known_movements = list(movements_map.keys())
    movement_aliases: Dict[str, List[str]] = {}
    movement_categories: Dict[str, str] = {}
    founded_years: Dict[str, int] = {}

    for name, entry in movements_map.items():
        aliases = entry.get('aliases') or []
        movement_aliases[name] = aliases
        if entry.get('category'):
            movement_categories[name] = entry.get('category')
        if entry.get('founded_year') is not None:
            try:
                founded_years[name] = int(entry.get('founded_year'))
            except Exception:
                pass

    person_aliases = ka.person_aliases() or {}

    print(f"✅ Načteno {len(known_movements)} known_movements ze config")
    print(f"✅ Načteno {len(movement_aliases)} movement_aliases ze config")
    print(f"✅ Načteno {len(movement_categories)} movement_categories ze config")
    print(f"✅ Načteno {len(founded_years)} founded_years ze config")
    print(f"✅ Načteno {len(person_aliases)} known_persons_aliases ze config")

    return known_movements, movement_aliases, movement_categories, person_aliases, founded_years


def _seed_known_movements(
    session,
    known_movements: List[str],
    movement_aliases: Dict[str, List[str]],
    movement_categories: Dict[str, str],
    movement_founded_years: Optional[Dict[str, int]] = None,
) -> Dict[str, Movement]:
    """Seed known movements into DB with aliases, category and founding year."""
    movement_by_name: Dict[str, Movement] = {
        movement.name: movement for movement in session.query(Movement).all()
    }

    for movement_name in known_movements:
        name = (movement_name or "").strip()
        if not name:
            continue

        explicit_category = movement_categories.get(name) if movement_categories else None
        category = explicit_category or _infer_movement_category(name)
        founded_year = _infer_movement_founded_year(
            name,
            {"keywords": {"founded_years": movement_founded_years or {}}},
        )

        if name not in movement_by_name:
            aliases = movement_aliases.get(name, [])
            alias_str = ", ".join(aliases) if aliases else None

            movement = Movement(
                name=name,
                alias=alias_str,
                category=category,
                founded_year=founded_year,
            )
            session.add(movement)
            session.flush()
            movement_by_name[name] = movement

            if aliases:
                print(f"  ➕ {name} (aliasy: {len(aliases)})")
        else:
            movement = movement_by_name[name]
            current_alias = cast(Optional[str], getattr(movement, "alias", None))
            if not current_alias:
                aliases = movement_aliases.get(name, [])
                if aliases:
                    setattr(movement, "alias", ", ".join(aliases))
                    print(f"  🔄 Aktualizováno aliasy pro: {name} ({len(aliases)} aliasů)")
            current_category = cast(Optional[str], getattr(movement, "category", None))
            if not current_category or str(current_category).strip().lower() == "nové náboženské hnutí":
                setattr(movement, "category", category)

            current_founded_year = cast(Optional[int], getattr(movement, "founded_year", None))
            if current_founded_year is None and founded_year is not None:
                setattr(movement, "founded_year", founded_year)

    session.commit()
    print(f"\n✅ Celkem movements v DB: {len(movement_by_name)}")
    return movement_by_name


def _infer_movement_founded_year(movement_name: str, config_data: Optional[Dict] = None) -> Optional[int]:
    """Infer a movement founding year from config data.

    This stays lightweight and config-driven so the project can keep a small
    explicit list of well-known movements without introducing a heavyweight
    knowledge base.
    """
    if isinstance(config_data, dict):
        keywords = config_data.get("keywords", {}) if isinstance(config_data.get("keywords", {}), dict) else {}
        founded_years = keywords.get("founded_years", {}) if isinstance(keywords.get("founded_years", {}), dict) else {}
    else:
        founded_years = {}

    if not founded_years:
        try:
            config_path = Path("extracting/sources_config.yaml")
            with open(config_path, "r", encoding="utf-8") as file:
                loaded = yaml.safe_load(file)
            loaded_config = loaded if isinstance(loaded, dict) else {}
            keywords = loaded_config.get("keywords", {}) if isinstance(loaded_config.get("keywords", {}), dict) else {}
            founded_years = keywords.get("founded_years", {}) if isinstance(keywords.get("founded_years", {}), dict) else {}
        except Exception:
            founded_years = {}

    name = (movement_name or "").strip()
    if not name:
        return None

    direct_match = founded_years.get(name)
    if direct_match is not None:
        try:
            return int(direct_match)
        except (TypeError, ValueError):
            return None

    normalized_name = name.lower()
    for candidate_name, year_value in founded_years.items():
        if str(candidate_name).lower() == normalized_name:
            try:
                return int(year_value)
            except (TypeError, ValueError):
                return None

    return None


def _infer_movement_category(movement_name: str) -> str:
    """Infer a movement category from its canonical name.

    This is a lightweight fallback. For reliable categories, add explicit
    mappings in extracting/sources_config.yaml under keywords.movement_categories.
    """
    name = (movement_name or "").strip().lower()
    if not name:
        return "nové náboženské hnutí"

    psychospiritual_terms = [
        "scientolog",
        "eckankar",
        "happy science",
        "teal swan",
        "sadhguru",
        "paramahansa",
        "spirituální",
        "psychospiritual",
        "psychospirit",
        "meditace",
    ]
    ufo_terms = [
        "raeli",
        "vesmír",
        "unarius",
        "universe",
        "cosmic",
        "ufo",
        "extrater",
        "alien",
        "zkoumat",
    ]
    eastern_terms = [
        "buddh",
        "jóga",
        "kršna",
        "mait",
        "guru",
        "tibetsk",
        "hind",
        "zen",
        "dharm",
        "sahad",
        "ved",
        "shincheonji",
        "osho",
        "parama",
    ]
    esoteric_terms = [
        "esoter",
        "anthroposof",
        "teosof",
        "rosicruc",
        "satan",
        "tempel",
        "set",
        "okult",
        "magi",
        "mystick",
        "zlatého úsvitu",
        "světlo",
        "čaroděj",
    ]
    christian_terms = [
        "církev",
        "church",
        "ježíš",
        "christ",
        "křesťan",
        "evangel",
        "rodina",
        "poslední soud",
        "jednota",
    ]
    new_age_terms = [
        "nového věku",
        "new age",
        "alternativní náboženství",
        "univerzální",
        "zlatá éra",
        "vesmírní",
        "nová duchovní",
    ]

    if any(term in name for term in psychospiritual_terms):
        return "psychospiritual"
    if any(term in name for term in ufo_terms):
        return "ufo"
    if any(term in name for term in eastern_terms):
        return "eastern"
    if any(term in name for term in esoteric_terms):
        return "esoteric"
    if any(term in name for term in christian_terms):
        return "christian_derived"
    if any(term in name for term in new_age_terms):
        return "new_age"

    return "nové náboženské hnutí"


def _seed_known_persons(session, person_aliases: Dict[str, List[str]]) -> Dict[str, Person]:
    """Seed known persons into DB with their aliases."""
    person_by_name: Dict[str, Person] = {
        person.name: person for person in session.query(Person).all()
    }

    for canonical_name, aliases in person_aliases.items():
        name = (canonical_name or "").strip()
        if not name:
            continue
        
        if name not in person_by_name:
            # Create person with canonical name and aliases
            alias_str = ", ".join(aliases) if aliases else None
            
            person = Person(
                name=name,
                alias=alias_str
            )
            session.add(person)
            session.flush()
            person_by_name[name] = person
            
            if aliases:
                print(f"  ➕ {name} (aliasy: {len(aliases)})")
        else:
            # Update existing person with aliases if they don't have any
            person = person_by_name[name]
            current_alias = cast(Optional[str], getattr(person, "alias", None))
            if not current_alias:
                if aliases:
                    setattr(person, "alias", ", ".join(aliases))
                    print(f"  🔄 Aktualizováno aliasy pro: {name} ({len(aliases)} aliasů)")

    session.commit()
    print(f"\n✅ Celkem known persons v DB: {len(person_aliases)}")
    return person_by_name


def _resolve_person_name(
    person_text: str,
    person_aliases: Dict[str, List[str]]
) -> Optional[str]:
    """Resolve person name from text using canonical names and aliases."""
    entity = _normalize_text(person_text)
    if not entity or len(entity) < 3:
        return None

    # Build normalized maps
    canonical_map = {_normalize_text(name): name for name in person_aliases.keys() if name}

    alias_map: Dict[str, str] = {}
    for canonical, aliases in person_aliases.items():
        if canonical:
            alias_map[_normalize_text(canonical)] = canonical
        for alias in aliases or []:
            alias_map[_normalize_text(alias)] = canonical

    # Try exact match first
    if entity in canonical_map:
        return canonical_map[entity]
    if entity in alias_map:
        return alias_map[entity]

    # Try fuzzy matching on canonical names and aliases
    for canonical, aliases in person_aliases.items():
        all_variants = [canonical] + (aliases or [])
        for variant in all_variants:
            variant_norm = _normalize_text(variant)
            if not variant_norm:
                continue
            # Use token_set_ratio for better matching
            score = fuzz.token_set_ratio(entity, variant_norm)
            if score >= 90:  # High threshold for person matching
                return canonical

    return None


def _resolve_movement_name(
    movement_text: str,
    known_movements: List[str],
    movement_aliases: Dict[str, List[str]]
) -> Optional[str]:
    entity = _normalize_text(movement_text)
    if not entity or len(entity) < 3:
        return None

    known_map = {_normalize_text(name): name for name in known_movements if name}

    alias_map: Dict[str, str] = {}
    for canonical, aliases in movement_aliases.items():
        if canonical:
            alias_map[_normalize_text(canonical)] = canonical
        for alias in aliases or []:
            alias_map[_normalize_text(alias)] = canonical

    if entity in known_map:
        return known_map[entity]
    if entity in alias_map:
        return alias_map[entity]

    candidates: List[Tuple[str, str]] = []
    for name in known_movements:
        normalized = _normalize_text(name)
        if normalized:
            candidates.append((normalized, name))
    for alias_norm, canonical in alias_map.items():
        if alias_norm and canonical:
            candidates.append((alias_norm, canonical))

    best_score = 0
    best_canonical: Optional[str] = None
    for candidate_norm, canonical in candidates:
        score = fuzz.token_set_ratio(entity, candidate_norm)
        if score > best_score:
            best_score = score
            best_canonical = canonical

    if best_score >= 84:
        return best_canonical

    return None


def _find_matching_person(person_name: str, cached_persons: List[Person], analyzer=None) -> Optional[Person]:
    for person in cached_persons:
        if _is_same_person_name(str(person.name), person_name, analyzer):
            return person
    return None


def _prune_invalid_persons(
    session,
    known_movements: List[str],
    movement_aliases: Dict[str, List[str]]
) -> int:
    persons = session.query(Person).all()
    removed = 0

    for person in persons:
        person_name = _clean_person_name(str(person.name))
        is_valid = _is_valid_person_name(person_name)
        movement_match = _resolve_movement_name(person_name, known_movements, movement_aliases)

        if is_valid and not movement_match:
            continue

        for article in list(person.articles):
            if person in article.persons:
                article.persons.remove(person)

        session.delete(person)
        removed += 1

    return removed


def _deduplicate_persons(session, analyzer=None) -> int:
    """
    Deduplicate persons by name similarity, including Czech declension variants.
    Also remove badly extracted entities.
    """
    # First pass: remove bad entities
    bad_removed = 0
    persons = session.query(Person).all()
    for person in persons:
        if _is_bad_person_entity(person.name):
            for article in list(person.articles):
                if person in article.persons:
                    article.persons.remove(person)
            session.delete(person)
            bad_removed += 1
    
    print(f"  🗑️  Odstraněno {bad_removed} špatně extrahovaných entit")
    session.commit()
    
    # Second pass: merge duplicates with lemmatization support
    persons = session.query(Person).order_by(Person.id.asc()).all()
    removed = 0
    deleted_ids = set()

    for index, base_person in enumerate(persons):
        if base_person.id in deleted_ids:
            continue

        for candidate in persons[index + 1:]:
            if candidate.id in deleted_ids:
                continue

            if not _is_same_person_name(base_person.name, candidate.name, analyzer):
                continue

            for article in list(candidate.articles):
                if base_person not in article.persons:
                    article.persons.append(base_person)

            session.delete(candidate)
            deleted_ids.add(candidate.id)
            removed += 1
    
    session.commit()
    return bad_removed + removed


def extract_entities(db):
    """Extract and link entities to articles using known movements and deduplicated persons."""
    try:
        print("\n🔍 Extracting entities...")
        analyzer = CzechTextAnalyzer()

        known_movements, movement_aliases, movement_categories, person_aliases, movement_founded_years = _load_entity_linking_config()
        print(f"📋 Loaded {len(known_movements)} known movements from config")
        print(f"📋 Loaded {len(movement_aliases)} movement alias groups")
        print(f"📋 Loaded {len(movement_categories)} movement category mappings")
        print(f"📋 Loaded {len(movement_founded_years)} movement founding-year mappings")
        print(f"📋 Loaded {len(person_aliases)} known persons from config")

        session = db.get_session()
        movement_by_name = _seed_known_movements(
            session,
            known_movements,
            movement_aliases,
            movement_categories,
            movement_founded_years,
        )
        person_by_canonical = _seed_known_persons(session, person_aliases)

        articles = session.query(Article).all()
        cached_persons = session.query(Person).all()

        print(f"📄 Processing {len(articles)} articles...")

        movements_linked = 0
        persons_linked = 0
        locations_linked = 0
        movements_skipped = 0
        persons_skipped = 0

        for article in articles:
            try:
                entities = analyzer.extract_named_entities(article.content)

                for movement_text in entities.get('movements', []):
                    try:
                        canonical_name = _resolve_movement_name(
                            movement_text,
                            known_movements,
                            movement_aliases
                        )
                        if not canonical_name:
                            movements_skipped += 1
                            continue

                        movement = movement_by_name.get(canonical_name)
                        if not movement:
                            continue

                        if movement not in article.movements:
                            article.movements.append(movement)
                            movements_linked += 1
                    except Exception:
                        continue

                for person_text in entities.get('persons', []):
                    try:
                        person_name = _clean_person_name(person_text)
                        
                        # Try to resolve to canonical known person first
                        canonical_person = _resolve_person_name(person_name, person_aliases)
                        if canonical_person:
                            # Use canonical person from config
                            person = person_by_canonical.get(canonical_person)
                            if person and person not in article.persons:
                                article.persons.append(person)
                                persons_linked += 1
                            continue
                        
                        # Regular person processing
                        if not _is_valid_person_name(person_name):
                            persons_skipped += 1
                            continue
                        if _is_bad_person_entity(person_name):
                            persons_skipped += 1
                            continue
                        if _resolve_movement_name(person_name, known_movements, movement_aliases):
                            persons_skipped += 1
                            continue

                        person = _find_matching_person(person_name, cached_persons, analyzer)
                        if not person:
                            person = Person(name=person_name)
                            session.add(person)
                            session.flush()
                            cached_persons.append(person)

                        if person not in article.persons:
                            article.persons.append(person)
                            persons_linked += 1
                    except Exception:
                        continue

                for location_text in entities.get('locations', []):
                    try:
                        location_text = location_text.strip()
                        if not location_text or len(location_text) < 3:
                            continue

                        location = session.query(Location).filter(
                            Location.name.ilike(f"%{location_text}%")
                        ).first()

                        if not location:
                            location = Location(name=location_text)
                            session.add(location)
                            session.flush()

                        if location not in article.locations:
                            article.locations.append(location)
                            locations_linked += 1
                    except Exception:
                        continue

            except Exception as e:
                print(f"   ⚠️  Error extracting entities from article {article.id}: {e}")
                continue

        persons_pruned = _prune_invalid_persons(session, known_movements, movement_aliases)
        persons_merged = _deduplicate_persons(session, analyzer)

        session.commit()
        session.close()

        print(f"✅ Entity extraction completed:")
        print(f"   • Known movements in DB: {len(known_movements)}")
        print(f"   • Movements linked: {movements_linked}")
        print(f"   • Movements skipped: {movements_skipped}")
        print(f"   • Persons linked: {persons_linked}")
        print(f"   • Persons skipped: {persons_skipped}")
        print(f"   • Persons pruned: {persons_pruned}")
        print(f"   • Persons merged: {persons_merged}")
        print(f"   • Locations linked: {locations_linked}")

    except Exception as e:
        print(f"❌ Error extracting entities: {e}")
        raise


def print_statistics(db, initial_counts: Optional[Dict[str, int]] = None):
    """Print database statistics and optional deltas compared to `initial_counts`."""
    try:
        current = {
            'articles': db.get_article_count(),
            'movements': db.get_movement_count(),
            'persons': db.get_person_count(),
            'locations': db.get_location_count(),
        }

        print("\n📊 Database Statistics:")
        print(f"   • Articles: {current['articles']}")
        print(f"   • Movements: {current['movements']}")
        print(f"   • Persons: {current['persons']}")
        print(f"   • Locations: {current['locations']}")

        if initial_counts:
            print("\n📈 Changes during this run:")
            for key in ['articles', 'movements', 'persons', 'locations']:
                before = int(initial_counts.get(key, 0))
                after = int(current.get(key, 0))
                delta = after - before
                sign = '+' if delta >= 0 else ''
                print(f"   • {key.capitalize()}: {after} ({sign}{delta})")

    except Exception as e:
        print(f"⚠️  Error getting statistics: {e}")


def main():
    """Main ETL pipeline"""
    try:
        print("=" * 60)
        print("🎬 Project Infinit - ETL Pipeline")
        print("=" * 60)
        
        # Step 1: Create database
        db = create_db()
        # Capture initial counts to report deltas at the end of this run
        try:
            initial_counts = {
                'articles': db.get_article_count(),
                'movements': db.get_movement_count(),
                'persons': db.get_person_count(),
                'locations': db.get_location_count(),
            }
        except Exception:
            initial_counts = None
        
        # Step 2: Run config-driven acquisition sources and spiders
        run_configured_acquisition_sources()
        run_spiders()
        
        # Step 3: Import CSV data
        import_csv_data(db)

        # Step 3.5: Remove off-topic articles without movement linkage
        prune_irrelevant_articles(db)
        
        # Step 4: NLP analysis (sentiment & risk)
        analyze_sentiment_and_risk(db)
        
        # Step 5: Entity extraction
        extract_entities(db)

        # Step 5.5: Manual QA report for suspicious relevance
        print_suspicious_articles_report(db, limit=20)
        exported_rows = export_suspicious_articles_csv(
            db,
            output_csv="export/csv/suspicious_articles_report.csv",
            limit=200,
        )
        print(
            "🗂️ Suspicious relevance CSV exported: "
            f"{exported_rows} rows -> export/csv/suspicious_articles_report.csv"
        )
        
        # Step 6: Print statistics (including deltas)
        print_statistics(db, initial_counts=initial_counts)

        # Step 7: Optional Google Trends collection
        run_google_trends(save_to_db=True)
        
        print("\n" + "=" * 60)
        print("✅ ETL Pipeline completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
