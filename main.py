# 📁 main.py
# ETL Pipeline for Project Infinit
# New simplified schema: Articles → Movements, Persons, Locations

import subprocess
import os
import yaml
from pathlib import Path
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


def extract_entities(db):
    """Extract and link entities to articles - FILTERED by known_movements"""
    try:
        print("\n🔍 Extracting entities...")
        analyzer = CzechTextAnalyzer()
        
        # Load known_movements from sources_config.yaml
        config_path = Path("extracting/sources_config.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # known_movements is under keywords.known_movements.new_religious_movements
        known_movements = config.get('keywords', {}).get('known_movements', {}).get('new_religious_movements', [])
        movement_aliases = config.get('keywords', {}).get('known_movements', {}).get('movement_aliases', {})
        
        print(f"📋 Loaded {len(known_movements)} known movements from config")
        
        # Build normalized movements list for fuzzy matching
        all_movement_variants = known_movements.copy()
        for aliases in movement_aliases.values():
            all_movement_variants.extend(aliases)
        
        session = db.get_session()
        articles = session.query(Article).all()
        
        print(f"📄 Processing {len(articles)} articles...")
        
        movements_linked = 0
        persons_linked = 0
        locations_linked = 0
        movements_skipped = 0
        
        for article in articles:
            try:
                # Extract named entities
                entities = analyzer.extract_named_entities(article.content)
                
                # Process movements - ONLY if they match known_movements
                for movement_text in entities.get('movements', []):
                    try:
                        movement_text = movement_text.strip()
                        if not movement_text or len(movement_text) < 3:
                            continue
                        
                        # Fuzzy match against known movements
                        best_match = None
                        best_score = 0
                        
                        for known_movement in all_movement_variants:
                            score = fuzz.token_set_ratio(movement_text.lower(), known_movement.lower())
                            if score > best_score:
                                best_score = score
                                best_match = known_movement
                        
                        # Only link if fuzzy match score is high enough
                        fuzzy_threshold = 80
                        if best_score < fuzzy_threshold:
                            movements_skipped += 1
                            continue
                        
                        # Map to canonical movement name (from known_movements list)
                        canonical_name = None
                        if best_match in known_movements:
                            canonical_name = best_match
                        else:
                            # Find which known_movement this alias belongs to
                            for main_movement, aliases in movement_aliases.items():
                                if best_match in aliases:
                                    canonical_name = main_movement
                                    break
                        
                        if not canonical_name:
                            canonical_name = best_match
                        
                        # Try to find or create movement with CANONICAL name
                        movement = session.query(Movement).filter(
                            Movement.name.ilike(f"%{canonical_name}%")
                        ).first()
                        
                        if not movement:
                            movement = Movement(name=canonical_name)
                            session.add(movement)
                            session.flush()
                        
                        # Link to article
                        if movement not in article.movements:
                            article.movements.append(movement)
                            movements_linked += 1
                    
                    except Exception as e:
                        continue
                
                # Process persons (no filtering - keep as-is)
                for person_text in entities.get('persons', []):
                    try:
                        person_text = person_text.strip()
                        if not person_text or len(person_text) < 3:
                            continue
                        
                        person = session.query(Person).filter(
                            Person.name.ilike(f"%{person_text}%")
                        ).first()
                        
                        if not person:
                            person = Person(name=person_text)
                            session.add(person)
                            session.flush()
                        
                        if person not in article.persons:
                            article.persons.append(person)
                            persons_linked += 1
                    except Exception as e:
                        continue
                
                # Process locations (no filtering - keep as-is)
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
                    except Exception as e:
                        continue
            
            except Exception as e:
                print(f"   ⚠️  Error extracting entities from article {article.id}: {e}")
                continue
        
        session.commit()
        session.close()
        
        print(f"✅ Entity extraction completed:")
        print(f"   • Movements linked: {movements_linked} (fuzzy matched to known movements)")
        print(f"   • Movements skipped: {movements_skipped} (no match with known movements)")
        print(f"   • Persons linked: {persons_linked}")
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
