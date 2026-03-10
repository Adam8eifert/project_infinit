# 📁 processing/import_social_media_to_db.py
# Import social media posts from CSV to database
# Handles Reddit, YouTube, Telegram, Mastodon data
# Project: Religious Movements Research Database

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, SocialMediaPost
from datetime import datetime
from typing import Union, Optional
import logging
import json
import sys
from logging_utils import configure_project_logger

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from extracting.keywords import match_movement_from_text


class SocialMediaLoader:
    """Load social media posts from CSV to database"""

    def __init__(self, db: Optional[DBConnector] = None):
        self.db = db or DBConnector()
        self.session = self.db.get_session()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for import tracking"""
        self.logger = configure_project_logger(__name__, "imports/social_media_import.log")

    def validate_row(self, row, csv_path):
        """Validate individual data rows"""
        errors = []
        
        # Check for empty values
        if not row.get("url"):
            errors.append("Missing URL")
        if not row.get("text"):
            errors.append("Missing text")
        if not row.get("platform"):
            errors.append("Missing platform")
            
        # URL validation
        if row.get("url") and not row["url"].startswith(("http://", "https://")):
            errors.append("Invalid URL")
        
        if errors:
            self.logger.warning(f"Validation errors in {csv_path}: {', '.join(errors)}")
            return False
        return True

    def clean_row(self, row) -> Optional[dict]:
        """Clean and normalize social media post data"""
        try:
            platform = str(row.get("platform", "")).strip().lower()
            author = str(row.get("author", "")).strip()
            text = str(row.get("text", "")).strip()
            url = str(row.get("url", "")).strip()
            query = str(row.get("query", "")).strip()
            raw_json = row.get("raw_json", "")
            
            # Parse dates
            created_at = pd.to_datetime(row.get("created_at"), errors="coerce")
            if pd.isna(created_at):
                created_at = None
            
            # Parse metrics
            likes = int(row.get("likes", 0)) if pd.notna(row.get("likes")) else 0
            comments = int(row.get("comments", 0)) if pd.notna(row.get("comments")) else 0
            shares = int(row.get("shares", 0)) if pd.notna(row.get("shares")) else 0
            
            # Check for movement match (if not already assigned)
            movement_id = row.get("movement_id")
            if pd.isna(movement_id) or movement_id is None:
                movement_id = match_movement_from_text(text)
            else:
                movement_id = int(movement_id)

            return {
                "platform": platform,
                "author": author[:255],  # Limit length
                "text": text[:10000],  # Limit text length
                "url": url,
                "created_at": created_at,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "query": query,
                "raw_json": raw_json if isinstance(raw_json, str) else json.dumps(raw_json),
                "movement_id": movement_id,
            }
        except Exception as e:
            self.logger.error(f"Error cleaning row: {e}")
            return None

    def load_csv_to_database(self, csv_path: Union[str, Path]) -> int:
        """
        Import CSV to social_media_posts table
        
        Returns number of posts imported
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            self.logger.error(f"File does not exist: {csv_path}")
            return 0

        try:
            try:
                df = pd.read_csv(csv_path)
            except pd.errors.EmptyDataError:
                self.logger.info(f"Skipping empty CSV: {csv_path}")
                return 0
            
            self.logger.info(f"Loading {len(df)} rows from {csv_path}")

            # Check required columns
            required_columns = {"platform", "text", "url"}
            if not required_columns.issubset(df.columns):
                missing = required_columns - set(df.columns)
                raise ValueError(f"Missing columns: {missing}")

            imported = 0
            skipped = 0
            batch_size = 100

            for batch_start in range(0, len(df), batch_size):
                batch = df.iloc[batch_start:batch_start + batch_size]
                
                for _, row in batch.iterrows():
                    try:
                        # Validation
                        if not self.validate_row(row, csv_path):
                            skipped += 1
                            continue
                        
                        # Clean data
                        cleaned = self.clean_row(row)
                        if not cleaned:
                            skipped += 1
                            continue
                        
                        # Check for duplicate URL
                        existing = self.session.query(SocialMediaPost).filter(
                            SocialMediaPost.url == cleaned["url"]
                        ).first()
                        
                        if existing:
                            self.logger.debug(f"Duplicate URL skipped: {cleaned['url']}")
                            skipped += 1
                            continue
                        
                        # Create social media post
                        post = SocialMediaPost(**cleaned)
                        self.session.add(post)
                        self.session.flush()
                        
                        imported += 1
                        
                    except IntegrityError as e:
                        self.session.rollback()
                        self.logger.warning(f"Integrity error: {e}")
                        skipped += 1
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing row: {e}")
                        skipped += 1
                        continue
                
                # Commit batch
                try:
                    self.session.commit()
                except Exception as e:
                    self.session.rollback()
                    self.logger.error(f"Error saving batch: {e}")

            self.logger.info(f"Import completed: {imported} imported, {skipped} skipped from {csv_path}")
            return imported
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error loading CSV: {e}")
            return 0
        finally:
            self.session.close()

    def load_all_social_media_csvs(self, csv_dir="export/csv"):
        """Load all social media CSV files from directory"""
        csv_dir = Path(csv_dir)
        
        # Pattern match for social media CSVs
        patterns = [
            "reddit_raw.csv",
            "youtube_raw.csv",
            "telegram_raw.csv",
            "mastodon_raw.csv",
        ]
        
        total_imported = 0
        
        for pattern in patterns:
            csv_files = list(csv_dir.glob(pattern))
            for csv_file in csv_files:
                self.logger.info(f"Processing: {csv_file}")
                imported = self.load_csv_to_database(csv_file)
                total_imported += imported
        
        self.logger.info(f"Total social media posts imported: {total_imported}")
        return total_imported


def main():
    """Standalone execution"""
    loader = SocialMediaLoader()
    loader.load_all_social_media_csvs()


if __name__ == "__main__":
    main()
