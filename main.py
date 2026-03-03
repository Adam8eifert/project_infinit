# 📁 main.py
# ETL Pipeline for Project Infinit
# New simplified schema: Articles → Movements, Persons, Locations

import subprocess
import os
import re
import unicodedata
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
    suffixes = [
        "ove", "ova", "ovi", "ove", "ech", "ich", "emu", "eho", "ami", "emi",
        "ou", "em", "om", "mi", "mu", "ho", "ch", "y", "i", "a", "e", "u"
    ]
    stem = token
    for suffix in suffixes:
        if len(stem) > 4 and stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    return stem


def _tokenize_person(name: str) -> List[str]:
    normalized = _normalize_text(name)
    return [token for token in normalized.split() if token]


def _is_same_person_name(name_a: str, name_b: str) -> bool:
    norm_a = _normalize_text(name_a)
    norm_b = _normalize_text(name_b)

    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True

    tokens_a = _tokenize_person(name_a)
    tokens_b = _tokenize_person(name_b)
    if len(tokens_a) < 2 or len(tokens_b) < 2:
        return False

    first_a, last_a = _stem_name_token(tokens_a[0]), _stem_name_token(tokens_a[-1])
    first_b, last_b = _stem_name_token(tokens_b[0]), _stem_name_token(tokens_b[-1])

    full_score = fuzz.token_set_ratio(norm_a, norm_b)
    first_score = fuzz.ratio(first_a, first_b)
    last_score = fuzz.ratio(last_a, last_b)

    if full_score >= 95:
        return True
    if first_score >= 88 and last_score >= 88 and full_score >= 78:
        return True
    if first_score >= 95 and last_score >= 85 and full_score >= 82:
        return True

    same_first = tokens_a[0] == tokens_b[0]
    initial_match = (
        len(tokens_a[-1]) == 1 and tokens_b[-1].startswith(tokens_a[-1])
    ) or (
        len(tokens_b[-1]) == 1 and tokens_a[-1].startswith(tokens_b[-1])
    )
    if same_first and initial_match:
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

    return known_movements, movement_aliases


def _seed_known_movements(session, known_movements: List[str]) -> Dict[str, Movement]:
    movement_by_name: Dict[str, Movement] = {
        movement.name: movement for movement in session.query(Movement).all()
    }

    for movement_name in known_movements:
        name = (movement_name or "").strip()
        if not name:
            continue
        if name not in movement_by_name:
            movement = Movement(name=name)
            session.add(movement)
            session.flush()
            movement_by_name[name] = movement

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


def _find_matching_person(person_name: str, cached_persons: List[Person]) -> Optional[Person]:
    for person in cached_persons:
        if _is_same_person_name(str(person.name), person_name):
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


def _deduplicate_persons(session) -> int:
    persons = session.query(Person).order_by(Person.id.asc()).all()
    removed = 0
    deleted_ids = set()

    for index, base_person in enumerate(persons):
        if base_person.id in deleted_ids:
            continue

        for candidate in persons[index + 1:]:
            if candidate.id in deleted_ids:
                continue

            if not _is_same_person_name(base_person.name, candidate.name):
                continue

            for article in list(candidate.articles):
                if base_person not in article.persons:
                    article.persons.append(base_person)

            session.delete(candidate)
            deleted_ids.add(candidate.id)
            removed += 1

    return removed


def extract_entities(db):
    """Extract and link entities to articles using known movements and deduplicated persons."""
    try:
        print("\n🔍 Extracting entities...")
        analyzer = CzechTextAnalyzer()

        known_movements, movement_aliases = _load_entity_linking_config()
        print(f"📋 Loaded {len(known_movements)} known movements from config")
        print(f"📋 Loaded {len(movement_aliases)} movement alias groups")

        session = db.get_session()
        movement_by_name = _seed_known_movements(session, known_movements)

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
                        if _resolve_movement_name(person_name, known_movements, movement_aliases):
                            persons_skipped += 1
                            continue

                        person = _find_matching_person(person_name, cached_persons)
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
        persons_merged = _deduplicate_persons(session)

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
