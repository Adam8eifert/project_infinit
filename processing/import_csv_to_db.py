# 📁 processing/import_csv_to_db.py
# CSV to Articles Database Loader with New Schema

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Article, Movement, SourceType
from datetime import datetime
import logging
from typing import Union, Optional, Any, Dict
import json
import re
from urllib.parse import urlparse
from fuzzywuzzy import fuzz
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from extracting.config_loader import SourcesConfigLoader
except ImportError:
    SourcesConfigLoader = None

class CSVtoDatabaseLoader:
    """Load CSV articles to database with new schema (Article → M:N Movements)"""

    def __init__(self, db: Optional[DBConnector] = None):
        self.db = db or DBConnector()
        self.session = self.db.get_session()
        self.setup_logging()
        self.movement_cache = {}  # Cache for movement fuzzy matching
        
        # Load sources config for require_movement_id checks
        try:
            self.sources_config = SourcesConfigLoader() if SourcesConfigLoader else None
        except Exception as e:
            self.logger.warning(f"Could not load sources config: {e}")
            self.sources_config = None

    def setup_logging(self):
        """Setup logging for import tracking"""
        self.logger = logging.getLogger(__name__)
        if self.logger.handlers:
            return

        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler('import_log.txt')
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)
        self.logger.propagate = False

    def match_movement_fuzzy(self, text: str, threshold: float = 70) -> Optional[Movement]:
        """Fuzzy match article text to find related Movement
        
        Args:
            text: Article title + content
            threshold: Minimum similarity score (0-100)
            
        Returns:
            Movement object if found, else None
        """
        if not text.strip():
            return None
        
        # Get all movements from database
        all_movements = self.session.query(Movement).all()
        
        best_match = None
        best_score = 0
        
        for movement in all_movements:
            # Try matching against movement name and alias
            scores = [
                fuzz.token_set_ratio(text.lower(), movement.name.lower()) if movement.name else 0,
                fuzz.token_set_ratio(text.lower(), movement.alias.lower()) if movement.alias else 0,
            ]
            
            max_score = max(scores)
            if max_score > best_score:
                best_score = max_score
                best_match = movement
        
        if best_score >= threshold:
            return best_match
        
        return None

    def validate_row(self, row, csv_path):
        """Validate individual data rows"""
        errors = []
        
        # Check for empty values
        if not row.get("url"):
            errors.append("Missing URL")
        if not row.get("title"):
            errors.append("Missing title")
        # Text can be very short for web-scraped content
        if not row.get("text"):
            errors.append("Missing text")
            
        # URL validation
        if row.get("url") and not row["url"].startswith(("http://", "https://")):
            errors.append("Invalid URL")
            
        # Date validation
        dt = pd.to_datetime(row.get("scraped_at"), errors="coerce")
        if pd.isna(dt):
            errors.append("Invalid date")

        categories_raw = row.get("categories")
        if categories_raw not in (None, "", []):
            if isinstance(categories_raw, str):
                categories_text = categories_raw.strip()
                if categories_text:
                    try:
                        json.loads(categories_text)
                    except (json.JSONDecodeError, TypeError):
                        errors.append("Invalid categories JSON")
            elif not isinstance(categories_raw, (list, tuple, dict)):
                errors.append("Invalid categories type")
        
        if errors:
            self.logger.warning(f"Validation errors in {csv_path}: {', '.join(errors)}")
            return False
        return True

    def clean_row(self, row) -> Optional[dict]:
        """Clean and normalize article data
        
        Returns dict with Article fields or None if validation fails
        """
        try:
            title = str(row.get("title", "")).strip()
            text = str(row.get("text", "")).strip()
            url = str(row.get("url", "")).strip()
            source_name = str(row.get("source_name", "")).strip()
            source_type_raw = str(row.get("source_type", "")).strip().lower()
            author = str(row.get("author", "")).strip() or None
            language_raw = str(row.get("language", "")).strip().lower()
            language = language_raw[:10] if language_raw else "cs"
            
            scraped_at = pd.to_datetime(row.get("scraped_at"), errors="coerce")
            published_at = pd.to_datetime(row.get("published_at"), errors="coerce")

            # Map source_type to SourceType enum
            source_type = None
            source_type_mapping = {
                'rss': SourceType.rss,
                'web': SourceType.website,
                'website': SourceType.website,
                'api': SourceType.api,
                'manual': SourceType.manual,
                'archive': SourceType.archive,
            }
            if source_type_raw in source_type_mapping:
                source_type = source_type_mapping[source_type_raw]
            elif source_type_raw:
                # Default to website if unknown
                source_type = SourceType.website

            categories_raw = row.get("categories", [])
            if isinstance(categories_raw, str):
                categories_text = categories_raw.strip()
                if categories_text:
                    try:
                        categories = json.loads(categories_text)
                    except (json.JSONDecodeError, TypeError):
                        categories = []
                else:
                    categories = []
            elif isinstance(categories_raw, (list, tuple, dict)):
                categories = categories_raw
            else:
                categories = []

            keywords_found = json.dumps(categories, ensure_ascii=False)

            movement_text = f"{title} {text}".strip()
            movement_id = None
            try:
                from extracting.keywords import match_movement_from_text
                movement_id = match_movement_from_text(movement_text, min_score=90)
            except Exception:
                movement_id = None
            
            parsed_domain = ""
            try:
                parsed_domain = urlparse(url).netloc.lower()
            except Exception:
                parsed_domain = ""

            return {
                "title": title[:500],  # Limit title length
                "content": text[:10000],  # Limit content length
                "source_name": source_name,
                "source_type": source_type,
                "author": author,
                "domain": parsed_domain,
                "language": language,
                "url": url,
                "published_at": published_at if not pd.isna(published_at) else (scraped_at if not pd.isna(scraped_at) else None),
                "keywords_found": keywords_found,
                "movement_id": movement_id,
            }
        except Exception as e:
            self.logger.error(f"Error cleaning row: {e}")
            return None

    def _source_requires_movement_id(self, csv_path: Path) -> bool:
        """Check if source requires movement_id based on sources_config.yaml
        
        Args:
            csv_path: Path to the CSV file being imported
            
        Returns:
            True if source requires movement_id, False otherwise
        """
        if not self.sources_config:
            return False
        
        # Extract source key from CSV filename (e.g., "blesk_rss_raw.csv" -> "blesk")
        filename = csv_path.stem  # e.g., "blesk_rss_raw"
        # Remove common suffixes
        source_key = filename.replace("_rss_raw", "").replace("_raw", "").replace("_web_raw", "")
        
        try:
            sources = self.sources_config.get_all_sources()
            source_config = sources.get(source_key, {})
            return source_config.get("require_movement_id", False)
        except Exception as e:
            self.logger.debug(f"Could not check require_movement_id for {source_key}: {e}")
            return False

    def _is_article_relevant(self, cleaned: Dict[str, Any], csv_path: Optional[Path] = None) -> bool:
        """Decide whether article should be imported into articles table."""
        movement_id = cleaned.get("movement_id")
        source_type_raw = cleaned.get("source_type")
        source_type = getattr(source_type_raw, "value", source_type_raw)
        source_type = str(source_type or "").strip().lower()
        combined_text = f"{cleaned.get('title', '')} {cleaned.get('content', '')}".strip()
        
        # Check source-level require_movement_id setting
        if csv_path and self._source_requires_movement_id(csv_path):
            if movement_id is None:
                self.logger.debug(f"Skipping article from strict source without movement: {cleaned.get('title', '')[:80]}")
                return False

        # For broad aggregators (Google News), require explicit movement match.
        if source_type == "news_aggregator":
            return movement_id is not None

        try:
            from extracting.keywords import contains_relevant_keywords, is_excluded_content
            if is_excluded_content(combined_text):
                return False
            return movement_id is not None or contains_relevant_keywords(combined_text, min_hits=2)
        except Exception:
            # Safe fallback when keyword module is unavailable.
            return movement_id is not None

    def load_csv_to_articles(self, csv_path: Union[str, Path]) -> int:
        """Import CSV to Articles table
        
        Returns number of articles imported
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
            required_columns = {"source_name", "title", "url", "text", "scraped_at"}
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

                        if not self._is_article_relevant(cleaned, csv_path):
                            self.logger.debug(f"Skipping non-relevant article: {cleaned.get('title', '')[:80]}")
                            skipped += 1
                            continue
                        
                        # Check for duplicate URL
                        existing = self.session.query(Article).filter(
                            Article.url == cleaned["url"]
                        ).first()
                        
                        if existing:
                            self.logger.debug(f"Skipping duplicate URL: {cleaned['url']}")
                            skipped += 1
                            continue
                        
                        # Create article with all metadata fields
                        article_payload = {
                            "title": cleaned["title"],
                            "content": cleaned["content"],
                            "url": cleaned["url"],
                            "source_name": cleaned["source_name"],
                            "source_type": cleaned["source_type"],
                            "author": cleaned.get("author"),
                            "domain": cleaned.get("domain"),
                            "language": cleaned.get("language", "cs"),
                            "published_at": cleaned.get("published_at"),
                        }
                        article = Article(**article_payload)
                        self.session.add(article)
                        self.session.flush()
                        
                        # Link movement only from strict movement matcher result.
                        matched_movement = None
                        movement_id = cleaned.get("movement_id")
                        if movement_id is not None:
                            matched_movement = self.session.query(Movement).filter(
                                Movement.id == movement_id
                            ).first()
                        
                        if matched_movement:
                            article.movements.append(matched_movement)
                            self.logger.debug(f"Linked article to movement: {matched_movement.name}")
                        
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
