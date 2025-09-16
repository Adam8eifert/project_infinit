# 📁 main.py – orchestrace celého ETL procesu

import subprocess
from database.db_loader import DBConnector
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader
import os

def run_spiders():
    """Spustí všechny definované Scrapy spidery a uloží výstupy do export/csv/"""
    spiders = [
        "sekty_tv_spider.py",
        "sekty_cz_spider.py",
        "info_dingir_spider.py",
        "pastorace_spider.py",
        "wikipedia_spider.py",
        "soccas_spider.py",
        "google_spider.py"
    ]
    for spider in spiders:
        path = os.path.join("scraping", spider)
        print(f"🚀 Spouštím spider: {spider}")
        subprocess.run(["scrapy", "runspider", path])

def create_db():
    """Inicializuje databázi a vytvoří tabulky, pokud ještě neexistují"""
    db = DBConnector()
    db.create_tables()
    print("✅ Databázové tabulky připraveny.")

def process_csv():
    """Importuje CSV soubory do databáze podle schématu"""
    importer = CSVtoDatabaseLoader()
    importer.import_all()

def run_nlp():
    """Volitelná ukázková NLP analýza (lze později přepsat na dávkovou)"""
    analyzer = CzechTextAnalyzer()
    sample_text = "Hnutí Grálu bylo registrováno v Praze. Text článku je neutrální."
    lemmas = analyzer.analyze(sample_text)
    entities = analyzer.extract_named_entities(sample_text)
    sentiment = analyzer.analyze_sentiment(sample_text)

    print("\n🧠 NLP DEMO:")
    for token in lemmas:
        print(f"{token['text']} → {token['lemma']} ({token['pos']})")
    print("\n🔎 Entity:")
    for ent in entities:
        print(f"{ent['text']} → {ent['type']}")
    print(f"\n💬 Sentiment: {sentiment}")

def load_scraped_csvs():
    csv_loader = CSVtoDatabaseLoader()
    csv_loader.load_csv_to_sources("export/csv/info_dingir_raw.csv")  # Můžeš přidat další


if __name__ == "__main__":
    print("🎬 Zahájení ETL pipeline...")
    create_db()
    run_spiders()
    process_csv()
    run_nlp()
    print("✅ Celý ETL proces dokončen.")
    load_scraped_csvs()
