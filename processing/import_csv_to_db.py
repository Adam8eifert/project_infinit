# 📁 processing/import_csv_to_db.py
# CSV to Articles Database Loader with New Schema

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Article, Movement, Source
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
        self.source_cache: Dict[str, int] = {}  # Cache for source lookup
        
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
            source_type = str(row.get("source_type", "")).strip().lower()
            language_raw = str(row.get("language", "")).strip().lower()
            language = language_raw[:10] if language_raw else "cs"
            scraped_at = pd.to_datetime(row.get("scraped_at"), errors="coerce")

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
                movement_id = match_movement_from_text(movement_text)
            except Exception:
                movement_id = None

            if movement_id is None:
                try:
                    matched_movement = self.match_movement_fuzzy(movement_text, threshold=70)
                    if matched_movement is not None:
                        movement_id = int(matched_movement.id)  # type: ignore[arg-type]
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
                "source": source_name,
                "url": url,
                "published_at": scraped_at if not pd.isna(scraped_at) else datetime.utcnow(),
                "keywords_found": keywords_found,
                "movement_id": movement_id,
                "source_type": source_type,
                "language": language,
                "domain": parsed_domain,
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

    @staticmethod
    def _slugify_source_value(value: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower())
        normalized = re.sub(r"-+", "-", normalized).strip("-")
        return normalized or "unknown"

    def _build_source_key(self, source_name: str, source_type: str) -> str:
        name_part = self._slugify_source_value(source_name)
        type_part = self._slugify_source_value(source_type)
        return f"{type_part}__{name_part}"

    def _get_or_create_source_id(self, cleaned: Dict[str, Any]) -> Optional[int]:
        try:
            source_name = str(cleaned.get("source", "")).strip()
            source_type = str(cleaned.get("source_type", "")).strip().lower() or "unknown"
            language = str(cleaned.get("language", "")).strip().lower() or None
            domain = str(cleaned.get("domain", "")).strip().lower() or None

            if not source_name:
                return None

            source_key = self._build_source_key(source_name, source_type)
            cached_id = self.source_cache.get(source_key)
            if cached_id is not None:
                return cached_id

            source_record = self.session.query(Source).filter(Source.source_key == source_key).first()
            if source_record is None:
                source_url = f"source://{source_key}"
                source_record = self.session.query(Source).filter(Source.url == source_url).first()

            if source_record is None:
                source_record = Source(
                    source_key=source_key,
                    source_name=source_name,
                    source_type=source_type,
                    domain=domain,
                    language=language,
                    url=f"source://{source_key}",
                    content_full=None,
                )
                self.session.add(source_record)
                self.session.flush()
            else:
                # Backfill key/metadata for legacy rows when missing.
                if not getattr(source_record, "source_key", None):
                    source_record.source_key = source_key
                if not getattr(source_record, "domain", None) and domain:
                    source_record.domain = domain
                if not getattr(source_record, "language", None) and language:
                    source_record.language = language

            source_id = int(source_record.id) if source_record.id is not None else None
            if source_id is not None:
                self.source_cache[source_key] = source_id
            return source_id
        except Exception as error:
            self.logger.debug(f"Source normalization fallback to NULL source_id: {error}")
            self.session.rollback()
            return None

    def _is_article_relevant(self, cleaned: Dict[str, Any], csv_path: Optional[Path] = None) -> bool:
        """Decide whether article should be imported into articles table."""
        movement_id = cleaned.get("movement_id")
        source_type = str(cleaned.get("source_type", "")).strip().lower()
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
                        
                        # Resolve normalized source record for FK link.
                        source_id = self._get_or_create_source_id(cleaned)

                        # Create article (Article fields + source FK)
                        article_payload = {
                            "title": cleaned["title"],
                            "content": cleaned["content"],
                            "source": cleaned["source"],
                            "source_id": source_id,
                            "language": cleaned.get("language"),
                            "url": cleaned["url"],
                            "published_at": cleaned["published_at"],
                        }
                        article = Article(**article_payload)
                        self.session.add(article)
                        self.session.flush()
                        
                        # Try to link movement from clean_row or fallback fuzzy match
                        matched_movement = None
                        movement_id = cleaned.get("movement_id")
                        if movement_id is not None:
                            matched_movement = self.session.query(Movement).filter(
                                Movement.id == movement_id
                            ).first()

                        if matched_movement is None:
                            movement_text = f"{cleaned['title']} {cleaned['content']}"
                            matched_movement = self.match_movement_fuzzy(movement_text, threshold=70)
                        
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
