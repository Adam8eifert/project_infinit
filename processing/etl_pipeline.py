"""
ETL Pipeline orchestrator class that manages the entire data flow.
Designed to be extensible for future enhancements while keeping current implementation simple.
"""

import logging
from typing import List
import subprocess
import os
from database.db_loader import DBConnector
from processing.nlp_analysis import CzechTextAnalyzer
from processing.import_csv_to_db import CSVtoDatabaseLoader

class SpiderManager:
    """Manages the execution of Scrapy spiders with future extensibility in mind"""
    
    def __init__(self, spider_dir: str = "scraping"):
        self.spider_dir = spider_dir
        self.spiders = [
            "sekty_tv_spider.py",
            "sekty_cz_spider.py",
            "info_dingir_spider.py",
            "pastorace_spider.py",
            "wikipedia_spider.py",
            "soccas_spider.py",
            "google_spider.py"
        ]
    
    def run_spiders(self) -> None:
        """Execute all registered spiders"""
        for spider in self.spiders:
            path = os.path.join(self.spider_dir, spider)
            logging.info(f"Starting spider: {spider}")
            try:
                subprocess.run(["scrapy", "runspider", path], check=True)
                logging.info(f"Successfully completed spider: {spider}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Spider {spider} failed with exit code {e.returncode}")
                raise

class DataProcessor:
    """Handles all data processing operations including NLP and CSV operations"""
    
    def __init__(self):
        self.nlp = CzechTextAnalyzer()
        self.csv_loader = CSVtoDatabaseLoader()
    
    def process_csv_files(self) -> None:
        """Process all CSV files from spiders"""
        try:
            self.csv_loader.import_all()
            logging.info("Successfully processed all CSV files")
        except Exception as e:
            logging.error(f"Error processing CSV files: {e}")
            raise
    
    def run_nlp_analysis(self, text: str) -> dict:
        """Run NLP analysis on given text"""
        try:
            return {
                'lemmas': self.nlp.analyze(text),
                'entities': self.nlp.extract_named_entities(text),
                'sentiment': self.nlp.analyze_sentiment(text)
            }
        except Exception as e:
            logging.error(f"Error in NLP analysis: {e}")
            raise

class ETLPipeline:
    """Main ETL orchestrator that manages the entire pipeline flow"""
    
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.spider_manager = SpiderManager()
        self.data_processor = DataProcessor()
        self.db = DBConnector()
    
    def initialize_database(self) -> None:
        """Initialize database tables"""
        try:
            self.db.create_tables()
            logging.info("Database tables created successfully")
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
    
    def run_pipeline(self) -> None:
        """Execute the complete ETL pipeline"""
        try:
            logging.info("Starting ETL pipeline")
            
            # Initialize database
            self.initialize_database()
            
            # Run spiders to collect data
            self.spider_manager.run_spiders()
            
            # Process collected data
            self.data_processor.process_csv_files()
            
            # Optional: Run sample NLP analysis
            sample_text = "Hnutí Grálu bylo registrováno v Praze. Text článku je neutrální."
            nlp_results = self.data_processor.run_nlp_analysis(sample_text)
            logging.info(f"NLP Analysis complete: {nlp_results}")
            
            logging.info("ETL pipeline completed successfully")
            
        except Exception as e:
            logging.error(f"ETL pipeline failed: {e}")
            raise