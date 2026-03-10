# 📁 processing/import_csv_to_db.py
# CSV to Articles Database Loader with New Schema

import pandas as pd
from pathlib import Path
from sqlalchemy.exc import IntegrityError
from database.db_loader import DBConnector, Article, Movement, SourceType
from datetime import datetime, timezone
import logging
from typing import Union, Optional, Any, Dict
import json
import re
from urllib.parse import urlparse
from fuzzywuzzy import fuzz
from time import perf_counter
import sys
from logging_utils import configure_project_logger

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
        self.logger = configure_project_logger(__name__, "imports/csv_import.log")

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

    def _normalize_datetime(self, value: Any) -> Optional[datetime]:
        """Normalize datetime-like values for safe comparisons and storage."""
        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except Exception:
            pass

        if isinstance(value, pd.Timestamp):
            value = value.to_pydatetime()
        elif isinstance(value, str):
            parsed = pd.to_datetime(value, errors="coerce")
            if pd.isna(parsed):
                return None
            value = parsed.to_pydatetime() if isinstance(parsed, pd.Timestamp) else parsed

        if not isinstance(value, datetime):
            return None

        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)

        return value.replace(microsecond=0)

    def _apply_article_updates(self, article: Article, cleaned: Dict[str, Any]) -> bool:
        """Update mutable article fields and return True if anything changed."""
        changed = False
        field_map = {
            "title": "title",
            "content": "content",
            "source_name": "source_name",
            "source_type": "source_type",
            "author": "author",
            "domain": "domain",
            "language": "language",
        }

        for article_field, cleaned_key in field_map.items():
            current_value = getattr(article, article_field)
            new_value = cleaned.get(cleaned_key)
            if current_value != new_value:
                setattr(article, article_field, new_value)
                changed = True

        current_published_at = self._normalize_datetime(article.published_at)
        new_published_at = self._normalize_datetime(cleaned.get("published_at"))
        if current_published_at != new_published_at:
            article.published_at = new_published_at
            changed = True

        return changed

    def _sync_article_movement(self, article: Article, matched_movement: Optional[Movement]) -> bool:
        """Ensure article has exactly one matched movement (or none)."""
        target_ids = [matched_movement.id] if matched_movement else []
        current_ids = sorted(movement.id for movement in article.movements)

        if current_ids == target_ids:
            return False

        article.movements = [matched_movement] if matched_movement else []
        return True

    def load_csv_to_articles(self, csv_path: Union[str, Path]) -> int:
        """Import CSV to Articles table
        
        Returns number of changed articles (inserted + updated)
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

            total_start = perf_counter()
            total_rows = len(df)
            inserted = 0
            updated = 0
            unchanged = 0
            skipped = 0
            batch_size = 100
            total_batches = max(1, (total_rows + batch_size - 1) // batch_size)

            for batch_start in range(0, len(df), batch_size):
                batch_number = (batch_start // batch_size) + 1
                batch_timer_start = perf_counter()
                batch = df.iloc[batch_start:batch_start + batch_size]
                batch_row_count = len(batch)
                prepared_rows = []
                movement_ids = set()
                batch_skipped_before = skipped
                batch_unchanged_before = unchanged
                
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
                        prepared_rows.append(cleaned)
                        movement_id = cleaned.get("movement_id")
                        if movement_id is not None:
                            movement_ids.add(movement_id)
                        
                    except IntegrityError as e:
                        self.session.rollback()
                        self.logger.warning(f"Integrity error: {e}")
                        skipped += 1
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing row: {e}")
                        skipped += 1
                        continue

                if not prepared_rows:
                    batch_elapsed = perf_counter() - batch_timer_start
                    batch_rate = (batch_row_count / batch_elapsed) if batch_elapsed > 0 else float(batch_row_count)
                    batch_skipped = skipped - batch_skipped_before
                    self.logger.info(
                        f"Batch {batch_number}/{total_batches} for {csv_path.name}: "
                        f"{batch_row_count} rows in {batch_elapsed:.2f}s ({batch_rate:.1f} rows/s), "
                        f"0 changed, 0 unchanged, {batch_skipped} skipped"
                    )
                    continue

                urls = {row["url"] for row in prepared_rows if row.get("url")}
                existing_by_url = {}
                if urls:
                    existing_articles = self.session.query(Article).filter(Article.url.in_(urls)).all()
                    existing_by_url = {article.url: article for article in existing_articles if article.url}

                movement_map = {}
                if movement_ids:
                    matched_movements = self.session.query(Movement).filter(Movement.id.in_(movement_ids)).all()
                    movement_map = {movement.id: movement for movement in matched_movements}

                batch_inserted = 0
                batch_updated = 0
                pending_changes = 0

                for cleaned in prepared_rows:
                    try:
                        existing = existing_by_url.get(cleaned["url"])
                        movement_id = cleaned.get("movement_id")
                        matched_movement = movement_map.get(movement_id) if movement_id is not None else None

                        if existing:
                            fields_changed = self._apply_article_updates(existing, cleaned)
                            movement_changed = self._sync_article_movement(existing, matched_movement)

                            if fields_changed or movement_changed:
                                batch_updated += 1
                                pending_changes += 1
                            else:
                                unchanged += 1
                            continue

                        article_payload = {
                            "title": cleaned["title"],
                            "content": cleaned["content"],
                            "url": cleaned["url"],
                            "source_name": cleaned["source_name"],
                            "source_type": cleaned["source_type"],
                            "author": cleaned.get("author"),
                            "domain": cleaned.get("domain"),
                            "language": cleaned.get("language", "cs"),
                            "published_at": self._normalize_datetime(cleaned.get("published_at")),
                        }
                        article = Article(**article_payload)

                        if matched_movement:
                            article.movements = [matched_movement]

                        self.session.add(article)
                        if cleaned.get("url"):
                            existing_by_url[cleaned["url"]] = article
                        batch_inserted += 1
                        pending_changes += 1

                    except Exception as e:
                        self.logger.error(f"Error processing row: {e}")
                        skipped += 1
                        continue
                
                # Commit batch
                try:
                    self.session.commit()
                    inserted += batch_inserted
                    updated += batch_updated
                except Exception as e:
                    self.session.rollback()
                    self.logger.error(f"Error saving batch: {e}")
                    skipped += pending_changes

                batch_elapsed = perf_counter() - batch_timer_start
                batch_rate = (batch_row_count / batch_elapsed) if batch_elapsed > 0 else float(batch_row_count)
                batch_skipped = skipped - batch_skipped_before
                batch_unchanged = unchanged - batch_unchanged_before
                batch_changed = batch_inserted + batch_updated
                self.logger.info(
                    f"Batch {batch_number}/{total_batches} for {csv_path.name}: "
                    f"{batch_row_count} rows in {batch_elapsed:.2f}s ({batch_rate:.1f} rows/s), "
                    f"{batch_changed} changed ({batch_inserted} inserted, {batch_updated} updated), "
                    f"{batch_unchanged} unchanged, {batch_skipped} skipped"
                )

            changed = inserted + updated
            total_elapsed = perf_counter() - total_start
            total_rate = (total_rows / total_elapsed) if total_elapsed > 0 else float(total_rows)
            self.logger.info(
                f"Import completed in {total_elapsed:.2f}s ({total_rate:.1f} rows/s): "
                f"{changed} changed ({inserted} inserted, {updated} updated), "
                f"{unchanged} unchanged, {skipped} skipped from {csv_path}"
            )
            return changed
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Error loading CSV: {e}")
            return 0
        finally:
            self.session.close()

    def load_csv_to_sources(self, csv_path: Union[str, Path]) -> int:
        """Backward-compatible alias for manual CSV pipeline."""
        return self.load_csv_to_articles(csv_path)
