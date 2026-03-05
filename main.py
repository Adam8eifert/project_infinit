# 📁 main.py
# ETL Pipeline for Project Infinit
# New simplified schema: Articles → Movements, Persons, Locations

import subprocess
import os
import re
import unicodedata
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast
from database.db_loader import DBConnector, Article, Movement, Person, Location
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader
from fuzzywuzzy import fuzz


def run_spiders():
    """Run all defined Scrapy spiders for data collection"""
    spiders = [
        "extracting/rss_spider.py",              # Universal RSS spider
        "extracting/api_spider.py",              # Universal API spider
        "extracting/sekty_tv_spider.py",         # Sekty.TV web scraper
        "extracting/social_media_spider.py",     # Reddit + X/Twitter
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
        articles = session.query(Article).filter(Article.sentiment_label.is_(None)).all()
        
        print(f"📝 Analyzing {len(articles)} articles...")
        
        analyzed = 0
        for article in articles:
            try:
                # Sentiment analysis
                sentiment_result = analyzer.analyze_sentiment(article.content)
                if sentiment_result:
                    article.sentiment_score = sentiment_result.get('score')
                    article.sentiment_label = sentiment_result.get('label')
                
                # Risk analysis (basic - can be expanded)
                risk_score = analyzer.calculate_risk_score(article.content)
                article.risk_score = risk_score
                article.risk_level = analyzer.get_risk_level(risk_score)
                
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


def _load_entity_linking_config() -> Tuple[List[str], Dict[str, List[str]]]:
    config_path = Path("extracting/sources_config.yaml")
    with open(config_path, "r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file)

    config = loaded if isinstance(loaded, dict) else {}
    keywords = config.get("keywords", {}) if isinstance(config.get("keywords", {}), dict) else {}
    known_container = keywords.get("known_movements", {}) if isinstance(keywords.get("known_movements", {}), dict) else {}

    known_movements = known_container.get("new_religious_movements", [])

    movement_aliases = keywords.get("movement_aliases", {})
    if not movement_aliases:
        movement_aliases = known_container.get("movement_aliases", {})

    if not isinstance(known_movements, list):
        known_movements = []
    if not isinstance(movement_aliases, dict):
        movement_aliases = {}

    print(f"✅ Načteno {len(known_movements)} known_movements ze config")
    print(f"✅ Načteno {len(movement_aliases)} movement_aliases ze config")

    return known_movements, movement_aliases


def _seed_known_movements(session, known_movements: List[str], movement_aliases: Dict[str, List[str]]) -> Dict[str, Movement]:
    """Seed known movements into DB with aliases and category"""
    movement_by_name: Dict[str, Movement] = {
        movement.name: movement for movement in session.query(Movement).all()
    }

    for movement_name in known_movements:
        name = (movement_name or "").strip()
        if not name:
            continue
        
        if name not in movement_by_name:
            # Get aliases for this movement from config
            aliases = movement_aliases.get(name, [])
            alias_str = ", ".join(aliases) if aliases else None
            
            # Create movement with alias and default category
            movement = Movement(
                name=name,
                alias=alias_str,
                category="nové náboženské hnutí"
            )
            session.add(movement)
            session.flush()
            movement_by_name[name] = movement
            
            if aliases:
                print(f"  ➕ {name} (aliasy: {len(aliases)})")
        else:
            # Update existing movement with aliases if they don't have any
            movement = movement_by_name[name]
            current_alias = cast(Optional[str], getattr(movement, "alias", None))
            if not current_alias:
                aliases = movement_aliases.get(name, [])
                if aliases:
                    setattr(movement, "alias", ", ".join(aliases))
                    print(f"  🔄 Aktualizováno aliasy pro: {name} ({len(aliases)} aliasů)")
            current_category = cast(Optional[str], getattr(movement, "category", None))
            if not current_category:
                setattr(movement, "category", "nové náboženské hnutí")

    session.commit()
    print(f"\n✅ Celkem movements v DB: {len(movement_by_name)}")
    return movement_by_name


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

        known_movements, movement_aliases = _load_entity_linking_config()
        print(f"📋 Loaded {len(known_movements)} known movements from config")
        print(f"📋 Loaded {len(movement_aliases)} movement alias groups")

        session = db.get_session()
        movement_by_name = _seed_known_movements(session, known_movements, movement_aliases)

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


def print_statistics(db):
    """Print database statistics"""
    try:
        print("\n📊 Database Statistics:")
        print(f"   • Articles: {db.get_article_count()}")
        print(f"   • Movements: {db.get_movement_count()}")
        print(f"   • Persons: {db.get_person_count()}")
        print(f"   • Locations: {db.get_location_count()}")
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
        
        # Step 2: Run spiders
        run_spiders()
        
        # Step 3: Import CSV data
        import_csv_data(db)
        
        # Step 4: NLP analysis (sentiment & risk)
        analyze_sentiment_and_risk(db)
        
        # Step 5: Entity extraction
        extract_entities(db)
        
        # Step 6: Print statistics
        print_statistics(db)
        
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
