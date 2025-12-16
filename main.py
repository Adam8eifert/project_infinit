import subprocess
import os
from pathlib import Path
from database.db_loader import DBConnector
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader

def run_spiders():
    """Spustí všechny definované Scrapy spidery (RSS, API, web a sociální média)"""
    spiders = [
        # Nové RSS spidery
        "scraping/rss_spider.py",           # Univerzální RSS spider
        # Nové API spidery
        "scraping/api_spider.py",            # Univerzální API spider
        # Sociální média spidery
        "scraping/social_media_spider.py",   # Reddit + X/Twitter API
        # Starší web spidery (stále podporované)
        "scraping/medium_seznam_spider.py",
        "scraping/google_spider.py"
    ]
    for spider in spiders:
        try:
            print(f"🚀 Spouštím spider: {spider}")
            subprocess.run(["scrapy", "runspider", spider], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Chyba při spuštění {spider}: {e}")
            # Pokračuj dál i když jeden spider selže
            continue

def create_db():
    """Inicializuje databázi"""
    try:
        db = DBConnector()
        db.create_tables()
        print("✅ Databázové tabulky připraveny")
    except Exception as e:
        print(f"❌ Chyba při vytváření databáze: {e}")
        raise

def process_csv():
    """Importuje CSV soubory do databáze"""
    try:
        importer = CSVtoDatabaseLoader()
        # Import konkrétních CSV pokud existují
        csv_files = [
            "export/csv/info_dingir_raw.csv",
            "export/csv/sekty_tv_raw.csv",
            "export/csv/google_news_raw.csv"
        ]
        for csv_file in csv_files:
            if Path(csv_file).exists():
                importer.load_csv_to_sources(csv_file)
    except Exception as e:
        print(f"❌ Chyba při zpracování CSV: {e}")
        raise

def run_nlp(text="Hnutí Grálu bylo registrováno v Praze."):
    """Ukázková NLP analýza"""
    try:
        analyzer = CzechTextAnalyzer()
        entities = analyzer.extract_named_entities(text)
        sentiment = analyzer.analyze_sentiment(text)
        print("\n🧠 NLP výsledky:")
        print(f"Entity: {entities}")
        print(f"Sentiment: {sentiment}")
    except Exception as e:
        print(f"❌ Chyba při NLP analýze: {e}")
        raise

if __name__ == "__main__":
    try:
        print("🎬 Zahájení ETL pipeline...")
        create_db()
        run_spiders()
        process_csv()
        run_nlp()
        print("✅ ETL proces dokončen")
    except Exception as e:
        print(f"❌ ETL pipeline selhal: {e}")
        raise
