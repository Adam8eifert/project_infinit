import subprocess
import os
from pathlib import Path
from database.db_loader import DBConnector
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader
from processing.import_pdf_to_db import DocumentsToDatabase, PDFtoDatabaseLoader
from extracting.keywords import ALL_KNOWN_MOVEMENTS

def run_spiders():
    """Run all defined Scrapy spiders (RSS, API, web and social media)"""
    spiders = [
        # New RSS spiders
        "extracting/rss_spider.py",           # Universal RSS spider
        # New API spiders
        "extracting/api_spider.py",            # Universal API spider
        # Social media spiders
        "extracting/social_media_spider.py",   # Reddit + X/Twitter API
        # Older web spiders (still supported)
        "extracting/medium_seznam_spider.py",
        "extracting/google_spider.py"
    ]
    for spider in spiders:
        try:
            print(f"🚀 Running spider: {spider}")
            # Set PYTHONPATH to include project root for proper imports
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path(__file__).parent)
            subprocess.run(["scrapy", "runspider", spider], check=True, env=env)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error running {spider}: {e}")
            # Continue even if one spider fails
            continue

def create_db():
    """Initialize database"""
    try:
        db = DBConnector()
        db.create_tables()
        
        # Create default "Unidentified" movement for documents without matches
        session = db.get_session()
        from database.db_loader import Movement
        default_movement = session.query(Movement).filter_by(
            canonical_name="Neidentifikované hnutí"
        ).first()
        if not default_movement:
            default_movement = Movement(
                canonical_name="Neidentifikované hnutí",
                category="other",
                description="Dokumenty bez odpovídajícího hnutí",
                active_status="inactive"
            )
            session.add(default_movement)
            session.commit()
            print(f"✅ Default movement created (ID: {default_movement.id})")
        else:
            print(f"✅ Default movement exists (ID: {default_movement.id})")
        session.close()
        
        print("✅ Database tables ready")

        # Seed known movements from configuration (idempotent)
        try:
            from extracting.config_loader import get_config_loader
            from sqlalchemy import text
            
            loader = get_config_loader()
            known = loader.config.get('keywords', {}).get('known_movements', {}).get('new_religious_movements', [])
            
            print(f"🌱 Loading movements from config: {len(known)} movements found")
            
            if known:
                session = db.get_session()
                
                # Fix PostgreSQL sequence before seeding
                if 'postgresql' in db.db_uri.lower():
                    try:
                        max_id_result = session.execute(text("SELECT MAX(id) FROM movements")).fetchone()
                        max_id = max_id_result[0] if max_id_result and max_id_result[0] else 0
                        new_seq_val = max_id + 1
                        session.execute(text(f"SELECT setval('movements_id_seq', {new_seq_val}, false)"))
                        session.commit()
                        print(f"   🔧 Fixed sequence: Starting from ID {new_seq_val}")
                    except Exception as seq_error:
                        print(f"   ⚠️  Could not fix sequence: {seq_error}")
                        session.rollback()
                
                seeded = 0
                
                for movement_name in known:
                    if not movement_name or not isinstance(movement_name, str):
                        continue
                    
                    movement_name = movement_name.strip()
                    if not movement_name:
                        continue
                    
                    # Check by canonical_name (unique key with diacritics)
                    existing = session.query(Movement).filter(Movement.canonical_name == movement_name).first()
                    if not existing:
                        movement = Movement(
                            canonical_name=movement_name,  # Name with diacritics (single source of truth)
                            category="religious",
                            description="Seeded from extracting/sources_config.yaml",
                            active_status="unknown"
                        )
                        session.add(movement)
                        # Flush after each insert to avoid sequence conflicts
                        session.flush()
                        seeded += 1
                
                # Commit all changes at once
                session.commit()
                
                if seeded > 0:
                    print(f"✅ Seeded {seeded} new movements from configuration")
                if seeded == 0:
                    print(f"ℹ️  All {len(known)} movements already in database")
                    
                session.close()
        except Exception as e:
            print(f"⚠️ Failed to seed known movements: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Error creating database: {e}")
        raise

def process_csv():
    """Import CSV files to database"""
    try:
        importer = CSVtoDatabaseLoader()
        # Dynamically load all *_raw.csv files from export/csv/
        csv_dir = Path("export/csv")
        csv_files = list(csv_dir.glob("*_raw.csv"))
        
        if not csv_files:
            print("⚠️  No CSV files found for import")
            return
            
        print(f"📁 Found {len(csv_files)} CSV files to import")
        for csv_file in csv_files:
            csv_path = str(csv_file)
            print(f"📄 Importing: {csv_path}")
            importer.load_csv_to_sources(csv_path)
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        raise

def process_academic_documents():
    """Import academic documents (PDF, DOC, DOCX) to database"""
    try:
        from processing.import_pdf_to_db import DocumentsToDatabase
        
        loader = DocumentsToDatabase()
        docs_dir = "academic_data"

        print(f"📚 Processing academic documents (PDF, DOC, DOCX) from: {docs_dir}")
        stats = loader.load_documents_to_sources(docs_dir)

        print("📊 Document Import Summary:")
        print(f"   • Processed: {stats['processed']}")
        print(f"   • Successful: {stats['successful']}")
        print(f"   • Skipped: {stats['skipped']}")
        print(f"   • Failed: {stats['failed']}")

    except Exception as e:
        print(f"❌ Error processing documents: {e}")
        raise


def process_academic_pdfs():
    """Backward compatibility wrapper for process_academic_documents"""
    return process_academic_documents()

def run_nlp(text="Hnutí Grálu bylo registrováno v Praze."):
    """Sample NLP analysis"""
    try:
        analyzer = CzechTextAnalyzer()
        entities = analyzer.extract_named_entities(text)
        sentiment = analyzer.analyze_sentiment(text)
        print("\n🧠 NLP results:")
        print(f"Entities: {entities}")
        print(f"Sentiment: {sentiment}")
    except Exception as e:
        print(f"❌ Error in NLP analysis: {e}")
        raise

def process_entities():
    """Extract entities from sources and populate movements, locations, etc."""
    try:
        from database.db_loader import DBConnector, Movement, Alias, Location, Source
        from processing.nlp_analysis import CzechTextAnalyzer
        import re
        from fuzzywuzzy import fuzz
        from fuzzywuzzy.process import extractOne
        
        db = DBConnector()
        session = db.get_session()
        analyzer = CzechTextAnalyzer()
        
        # Get all sources with content
        sources = session.query(Source).filter(Source.content_full.isnot(None)).all()
        print(f"📊 Processing {len(sources)} sources for entity extraction")
        
        movements_created = 0
        locations_created = 0
        
        # Czech NSM keywords
        nsm_keywords = [
            'hnutí', 'sekta', 'kult', 'církev', 'společenství', 'grál', 'svědkové', 'jehova',
            'satanist', 'okult', 'ezoter', 'myst', 'duchovn', 'nábožensk', 'fundamental',
            'mormon', 'buddh', 'hindu', 'islam', 'křesťan', 'žid', 'pagan', 'new age'
        ]
        
        # Known Czech NSM names
        known_nsm = ALL_KNOWN_MOVEMENTS
        
        for source in sources:
            text = (source.content_full or "") + " " + (source.content_excerpt or "")
            if not text or len(text.strip()) < 50:
                continue
                
            # Extract named entities (fallback if available)
            entities = analyzer.extract_named_entities(text)
            
            # Extract potential movement names
            potential_movements = []
            
            # First, check for known NSM names
            text_lower = text.lower()
            for nsm_name in known_nsm:
                if nsm_name.lower() in text_lower:
                    potential_movements.append(nsm_name)
            
            # From NER entities (if available) - only if they match known patterns
            for entity in entities:
                if entity['label'] in ['ORG', 'MISC']:
                    entity_text = entity['text'].strip()
                    # Only accept if it looks like a real movement name
                    if (len(entity_text) > 3 and len(entity_text) < 50 and 
                        not any(char.isdigit() for char in entity_text) and
                        any(keyword in entity_text.lower() for keyword in ['hnutí', 'sekta', 'církev', 'kult'])):
                        potential_movements.append(entity_text)
            
            # From regex patterns - look for "sekta X", "hnutí Y" (Czech religious keywords), etc. but only for known movements
            for keyword in ['sekta', 'hnutí', 'církev', 'kult']:
                # Pattern: keyword + known movement name
                for known_movement in known_nsm:
                    if f"{keyword} {known_movement}".lower() in text_lower:
                        potential_movements.append(f"{keyword.capitalize()} {known_movement}")
            
            # Remove duplicates and filter
            potential_movements = list(set(potential_movements))
            
            # Blacklist - generic/nonsense terms
            blacklist_exact = [
                'církev', 'cirkev', 'sekta', 'hnutí', 'hnuti', 'kult',
                'ministerstvo', 'ministerstva', 'vláda', 'vláda',
                'náboženství', 'nabozenstvi', 'společnost', 'spolecnost',
                'organizace', 'skupina', 'komunita',
                'náboženské hnutí (obecně)'
            ]
            
            blacklist_contains = [
                'ministerstvo kultury', 'ministerstva kultury',
                'obecně', 'obecný', 'obecné', '(obecně)', '(obecný)',
                '##', 'hodnutími', 'je ', 'jsou ', 'byla ', 'bylo ',
                'vnímají', 'používány', 'kritizovány', 'získává',
                'stává', 'mohou', 'mají', 'spočívá'
            ]
            
            # Filter out obviously wrong names
            filtered_movements = []
            for m in potential_movements:
                m_lower = m.lower()
                words = m.split()
                
                # Skip if exact match with blacklist
                if m_lower in blacklist_exact:
                    continue
                
                # Skip if contains blacklisted phrase
                if any(phrase in m_lower for phrase in blacklist_contains):
                    continue
                
                # Skip if too short, too long, or too many words
                if not (5 < len(m) < 80 and len(words) <= 6):
                    continue
                
                filtered_movements.append(m)
            
            potential_movements = filtered_movements[:3]  # Limit to 3 per source
            
            # Create movements and aliases
            for movement_name in potential_movements[:3]:  # Limit to 3 per source
                # Flush session to ensure previous additions are visible
                session.flush()
                
                # Check if this is a known movement name (direct match with diacritics)
                if movement_name in known_nsm:
                    # Direct match - create or update movement
                    existing = session.query(Movement).filter(
                        Movement.canonical_name == movement_name
                    ).first()
                    
                    if not existing:
                        movement = Movement(
                            canonical_name=movement_name,  # Name with diacritics (single source of truth)
                            category="religious",
                            description=f"Extracted from source: {source.url}",
                            active_status="unknown"
                        )
                        session.add(movement)
                        movements_created += 1
                        print(f"  ➕ Created movement: {movement_name}")
                    else:
                        print(f"  ⏭️  Movement already exists: {movement_name}")
                else:
                    # This is not a direct match - find best match and create alias
                    best_match, score = extractOne(movement_name, known_nsm, scorer=fuzz.ratio)
                    if score >= 80:  # High confidence match
                        # Find the movement
                        canonical_movement = session.query(Movement).filter(
                            Movement.canonical_name == best_match
                        ).first()
                        
                        if not canonical_movement:
                            # Create the canonical movement first
                            canonical_movement = Movement(
                                canonical_name=best_match,  # Name with diacritics (single source of truth)
                                category="religious",
                                description=f"Created for alias: {movement_name}",
                                active_status="unknown"
                            )
                            session.add(canonical_movement)
                            session.flush()  # Flush to get auto-generated ID before creating alias
                            movements_created += 1
                            print(f"  ➕ Created canonical movement: {best_match}")
                        
                        # Check if alias already exists
                        existing_alias = session.query(Alias).filter(
                            Alias.movement_id == canonical_movement.id,
                            Alias.alias == movement_name
                        ).first()
                        
                        if not existing_alias:
                            alias = Alias(
                                movement_id=canonical_movement.id,
                                alias=movement_name,
                                alias_type="extracted",
                                confidence_score=score / 100.0
                            )
                            session.add(alias)
                            print(f"  ➕ Created alias: {movement_name} -> {best_match} (score: {score})")
                        else:
                            print(f"  ⏭️  Alias already exists: {movement_name}")
                    else:
                        # Low confidence - create as new canonical movement
                        existing = session.query(Movement).filter(
                            Movement.canonical_name == movement_name
                        ).first()
                        
                        if not existing:
                            movement = Movement(
                                canonical_name=movement_name,  # Name with diacritics (single source of truth)
                                category="religious",
                                description=f"Extracted from source: {source.url} (low confidence match)",
                                active_status="unknown"
                            )
                            session.add(movement)
                            movements_created += 1
                            print(f"  ➕ Created movement (low confidence): {movement_name}")
                        else:
                            print(f"  ⏭️  Movement already exists: {movement_name}")
            locations = []
            czech_cities = ['praha', 'brno', 'ostrava', 'plzeň', 'liberec', 'olomouc', 'české budějovice', 'hradec králové', 'pardubice', 'zlín']
            
            for entity in entities:
                if entity['label'] in ['LOC', 'GPE']:
                    locations.append(entity['text'].strip())
            
            # Also check for Czech cities in text
            text_lower = text.lower()
            for city in czech_cities:
                if city in text_lower:
                    locations.append(city.capitalize())
            
            # Get default movement ID for location fallback
            default_movement = session.query(Movement).filter_by(
                canonical_name="Neidentifikované hnutí"
            ).first()
            default_movement_id = default_movement.id if default_movement else None
            
            for location_name in set(locations):
                # Check if location exists
                if default_movement_id:
                    existing = session.query(Location).filter(Location.municipality.ilike(f"%{location_name}%")).first()
                    if not existing:
                        location = Location(
                            movement_id=default_movement_id,  # Use actual default movement ID
                            municipality=location_name,
                            region="Czech Republic" if any(city in location_name.lower() for city in czech_cities + ['česk', 'praha']) else None
                        )
                        session.add(location)
                        locations_created += 1
            
            # Update source with sentiment if not set
            if source.sentiment_score is None:
                sentiment = analyzer.analyze_sentiment(text[:512])  # First 512 chars
                # Backwards-compatible handling: analyzer may return a string label (tests/legacy)
                if isinstance(sentiment, str):
                    # Map common star labels to a normalized score, otherwise default to 0.5
                    import re
                    m = re.search(r"(\d)\s*star", sentiment)
                    if m:
                        stars = int(m.group(1))
                        score = (stars - 1) / 4.0
                    else:
                        score = 0.5
                    label = sentiment
                else:
                    score = sentiment.get('score', 0.5)
                    label = sentiment.get('label', 'neutral')

                source.sentiment_score = score
                source.classification_label = label
        
        session.commit()
        session.close()
        
        print(f"✅ Entity extraction completed:")
        print(f"   • Movements created: {movements_created}")
        print(f"   • Locations created: {locations_created}")
        
    except Exception as e:
        print(f"❌ Error in entity processing: {e}")
        raise

if __name__ == "__main__":
    try:
        print("🎬 Starting ETL pipeline...")
        create_db()
        run_spiders()
        process_csv()
        process_academic_pdfs()
        process_entities()
        run_nlp()
        print("✅ ETL process completed")
    except Exception as e:
        print(f"❌ ETL pipeline failed: {e}")
        raise
