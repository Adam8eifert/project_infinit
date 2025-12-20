import subprocess
import os
from pathlib import Path
from database.db_loader import DBConnector
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader

def run_spiders():
    """Run all defined Scrapy spiders (RSS, API, web and social media)"""
    spiders = [
        # New RSS spiders
        "scraping/rss_spider.py",           # Universal RSS spider
        # New API spiders
        "scraping/api_spider.py",            # Universal API spider
        # Social media spiders
        "scraping/social_media_spider.py",   # Reddit + X/Twitter API
        # Older web spiders (still supported)
        "scraping/medium_seznam_spider.py",
        "scraping/google_spider.py"
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
        print("✅ Database tables ready")
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

if __name__ == "__main__":
    try:
        print("🎬 Starting ETL pipeline...")
        create_db()
        run_spiders()
        process_csv()
        run_nlp()
        print("✅ ETL process completed")
    except Exception as e:
        print(f"❌ ETL pipeline failed: {e}")
        raise
