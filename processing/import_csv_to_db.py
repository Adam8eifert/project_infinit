# 📁 processing/import_csv_to_db.py

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Source
from datetime import datetime
import logging
from typing import Union

class CSVtoDatabaseLoader:
    """Safe import of CSV data to database with validation and logging"""

    def __init__(self):
        self.db = DBConnector()
        self.session = self.db.get_session()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for import tracking"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('import_log.txt'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def validate_row(self, row, csv_path):
        """Validate individual data rows"""
        errors = []
        
        # Check for empty values
        if not row.get("url"):
            errors.append("Missing URL")
        if not row.get("title"):
            errors.append("Missing title")
        if not row.get("text") or len(str(row.get("text", "")).strip()) < 10:
            errors.append("Missing or too short text")
            
        # URL validation
        if row.get("url") and not row["url"].startswith(("http://", "https://")):
            errors.append("Invalid URL")
            
        # Date validation
        try:
            pd.to_datetime(row.get("scraped_at"))
        except:
            errors.append("Invalid date")
            
        if errors:
            self.logger.warning(f"Validation errors in {csv_path}: {', '.join(errors)}")
            return False
        return True

    def clean_row(self, row):
        """Clean and normalize data"""
        return {
            "movement_id": 1,  # temporary: assign to first movement for testing
            "source_name": str(row.get("source_name", "")).strip(),
            "source_type": str(row.get("source_type", "")).strip(),
            "url": str(row.get("url", "")).strip(),
            "content_excerpt": str(row.get("title", "")).strip(),  # map title to content_excerpt
            "content_full": str(row.get("text", "")).strip(),      # map text to content_full
            "sentiment_score": None,  # will be filled during NLP
            "publication_date": pd.to_datetime(row.get("scraped_at"), errors="coerce")
        }

    def load_csv_to_sources(self, csv_path: Union[str, Path]):
        """Import CSV to database with validation and error handling"""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            self.logger.error(f"File does not exist: {csv_path}")
            return

        try:
            df = pd.read_csv(csv_path)
            self.logger.info(f"Loading {len(df)} rows from {csv_path}")

            # Check required columns
            required_columns = {"source_name", "source_type", "title", "url", "text", "scraped_at"}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(f"Missing columns: {missing}")

            # Import in batches for better performance and rollback capability
            batch_size = 100
            imported = 0
            skipped = 0

            for batch_start in range(0, len(df), batch_size):
                batch = df.iloc[batch_start:batch_start + batch_size]
                
                for _, row in batch.iterrows():
                    try:
                        # Validation and cleaning
                        if not self.validate_row(row, csv_path):
                            skipped += 1
                            continue
                            
                        cleaned_data = self.clean_row(row)
                        source = Source(**cleaned_data)
                        self.session.add(source)
                        imported += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error processing row: {e}")
                        skipped += 1
                        continue
                
                try:
                    self.session.commit()
                except IntegrityError:
                    self.session.rollback()
                    self.logger.warning("Duplicate URL - skipping batch")
                    skipped += len(batch)
                except Exception as e:
                    self.session.rollback()
                    self.logger.error(f"Error saving batch: {e}")
                    skipped += len(batch)

            self.logger.info(f"Import completed: {imported} imported, {skipped} skipped")
        except IntegrityError:
            self.session.rollback()
            print("⚠️ Duplicate URL – some records already exist.")
        except Exception as e:
            self.session.rollback()
            print(f"❌ Error loading CSV: {e}")
        finally:
            self.session.close()
