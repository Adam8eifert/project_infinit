# 📁 processing/import_csv_to_db.py

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Source
from datetime import datetime
import logging
from typing import Union
import json
import re

# Import movement matching function
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from extracting.keywords import match_movement_from_text

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
        """Validate individual data rows

        New checks:
        - `scraped_at` must be parseable as a datetime (ISO or common formats)
        - `categories` if present must be valid JSON that resolves to a list
        """
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
            
        # Date validation - use pandas to parse and check for NaT
        dt = pd.to_datetime(row.get("scraped_at"), errors="coerce")
        if pd.isna(dt):
            errors.append("Invalid date")

        # Categories validation - accept empty, or JSON list or plain string; coerce where possible
        cats = row.get("categories", "")
        # Handle pandas NaN/null values gracefully by treating them as empty
        try:
            if pd.isna(cats):
                row['categories'] = []
                cats = []
        except Exception:
            # If pd.isna fails for any reason, continue with original value
            pass

        if cats and not isinstance(cats, (list, tuple)):
            try:
                parsed = json.loads(cats)
                if not isinstance(parsed, list):
                    # If JSON parsed to a scalar, wrap as a single-item list
                    parsed = [parsed]
            except Exception:
                # Not valid JSON; reject if it's clearly JSON-like (e.g., starts with '{' or '[')
                if isinstance(cats, str) and cats.strip():
                    s = cats.strip()
                    if s[0] in ('{', '['):
                        errors.append("categories must be a JSON list or non-empty string")
                        parsed = None
                    else:
                        # Try splitting on common separators
                        if any(sep in s for sep in [',',';','|']):
                            parts = [p.strip() for p in re.split('[,;|]', s) if p.strip()]
                            parsed = parts if parts else [s]
                        else:
                            parsed = [s]
                else:
                    # Treat empty/non-string categories as empty list (no categories)
                    parsed = []

            # If parsed is a list, normalize it back into the row for downstream processing
            if isinstance(parsed, list):
                row['categories'] = parsed
            else:
                # Keep the original value (and allow validation to fail above)
                pass

        if errors:
            self.logger.warning(f"Validation errors in {csv_path}: {', '.join(errors)}")
            return False
        return True

    def clean_row(self, row):
        """Clean and normalize data

        - Convert categories JSON string into a JSON string stored in `keywords_found` (preserve as JSON)
        - Convert scraped_at into a proper datetime for `publication_date`
        - Match movement from text content using fuzzy matching
        """
        # Normalize categories
        categories = row.get("categories", "")
        keywords_json = "[]"
        if categories:
            if isinstance(categories, (list, tuple)):
                keywords_json = json.dumps(categories, ensure_ascii=False)
            else:
                try:
                    parsed = json.loads(categories)
                    if isinstance(parsed, list):
                        keywords_json = json.dumps(parsed, ensure_ascii=False)
                except Exception:
                    # leave as empty list if parsing fails; validation should have caught it
                    keywords_json = "[]"

        # Try to match movement from text content
        text_content = str(row.get("text", "")).strip()
        title_content = str(row.get("title", "")).strip()
        combined_text = f"{title_content} {text_content}"
        
        movement_id = match_movement_from_text(combined_text)
        if movement_id is None:
            # Fallback to first movement if no match found
            movement_id = 1
            self.logger.debug(f"No movement match found for: {title_content[:50]}...")

        return {
            "movement_id": movement_id,
            "source_name": str(row.get("source_name", "")).strip(),
            "source_type": str(row.get("source_type", "")).strip(),
            "url": str(row.get("url", "")).strip(),
            "content_excerpt": str(row.get("title", "")).strip(),  # map title to content_excerpt
            "content_full": str(row.get("text", "")).strip(),      # map text to content_full
            "sentiment_score": None,  # will be filled during NLP
            "publication_date": pd.to_datetime(row.get("scraped_at"), errors="coerce"),
            "keywords_found": keywords_json
        }

    def load_csv_to_sources(self, csv_path: Union[str, Path]):
        """Import CSV to database with validation and error handling"""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            self.logger.error(f"File does not exist: {csv_path}")
            return

        try:
            try:
                df = pd.read_csv(csv_path)
            except pd.errors.EmptyDataError:
                self.logger.info(f"Skipping empty CSV (no columns): {csv_path}")
                return
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
