# database/db_connector.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
import sqlite3
import datetime
import hashlib
from typing import Optional, List

from .models import Base, Movement, Alias, Location, Source, TemporalAnalysis, GeographicAnalysis, SourceQuality
import config  # expects config.DB_URI

class DBConnector:
    """
    Portable DB connector using SQLAlchemy. Works with both SQLite and PostgreSQL.
    Exposes:
      - create_tables()
      - get_session()
      - helper methods for common inserts
    """
    def __init__(self, uri: Optional[str] = None):
        if uri is not None:
            self.db_uri = uri
        else:
            self.db_uri = getattr(config, "DB_URI", "sqlite:///data.db")
        connect_args = {}
        if self.db_uri.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        self.engine = create_engine(self.db_uri, connect_args=connect_args, future=True)
        self.SessionFactory = scoped_session(sessionmaker(bind=self.engine, autoflush=False, expire_on_commit=False))

    def create_tables(self):
        Base.metadata.create_all(self.engine, checkfirst=True)

    def drop_tables(self):
        Base.metadata.drop_all(self.engine)

    def get_session(self):
        return self.SessionFactory()

    # ========================================
    # DUPLICATE DETECTION & CLEANUP METHODS
    # ========================================

    def calculate_content_hash(self, text: str) -> str:
        """
        Calculate SHA-256 hash of content for duplicate detection.
        Normalizes text by removing extra whitespace and converting to lowercase.
        """
        if not text:
            return ""

        # Normalize text: lowercase, strip whitespace, normalize spaces
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def find_duplicates(self, content_hash: Optional[str] = None, url: Optional[str] = None, title: Optional[str] = None) -> List[Source]:
        """
        Find duplicate sources based on content hash, URL, or title similarity.
        Returns list of duplicate sources (excluding the most recent one).
        """
        session = self.get_session()
        try:
            query = session.query(Source)

            if content_hash:
                # Find by content hash
                duplicates = query.filter(Source.content_hash == content_hash).all()
            elif url:
                # Find by URL
                duplicates = query.filter(Source.url == url).all()
            elif title:
                # Find by similar title (basic implementation)
                title_lower = title.lower()
                duplicates = query.filter(Source.source_name.ilike(f"%{title_lower}%")).all()
            else:
                return []

            # Sort by creation date, keep the most recent, return others as duplicates
            if len(duplicates) > 1:
                duplicates.sort(key=lambda x: x.created_at, reverse=True)
                return duplicates[1:]  # Return all except the most recent

            return []

        finally:
            session.close()

    def remove_duplicates(self, dry_run: bool = True) -> dict:
        """
        Remove duplicate sources from database.
        Returns statistics about what was found and removed.
        """
        session = self.get_session()
        stats = {
            'scanned': 0,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'errors': 0
        }

        try:
            # Get all sources with content_hash
            sources = session.query(Source).filter(Source.content_hash.isnot(None)).all()
            stats['scanned'] = len(sources)

            # Group by content_hash
            hash_groups = {}
            for source in sources:
                if source.content_hash not in hash_groups:
                    hash_groups[source.content_hash] = []
                hash_groups[source.content_hash].append(source)

            # Process each group with duplicates
            for content_hash, group_sources in hash_groups.items():
                if len(group_sources) > 1:
                    stats['duplicates_found'] += len(group_sources) - 1

                    # Sort by creation date (newest first), keep the first one
                    group_sources.sort(key=lambda x: x.created_at, reverse=True)
                    duplicates_to_remove = group_sources[1:]

                    if not dry_run:
                        # Remove duplicates
                        for duplicate in duplicates_to_remove:
                            try:
                                session.delete(duplicate)
                                stats['duplicates_removed'] += 1
                            except Exception as e:
                                print(f"Error removing duplicate {duplicate.id}: {e}")
                                stats['errors'] += 1
                    else:
                        stats['duplicates_removed'] += len(duplicates_to_remove)

            if not dry_run:
                session.commit()

            return stats

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_content_hashes(self, batch_size: int = 1000) -> dict:
        """
        Update content_hash for sources that don't have it yet.
        Processes in batches to avoid memory issues.
        """
        session = self.get_session()
        stats = {
            'processed': 0,
            'updated': 0,
            'errors': 0
        }

        try:
            # Get sources without content_hash
            while True:
                sources = session.query(Source).filter(
                    Source.content_hash.is_(None),
                    Source.content_full.isnot(None)
                ).limit(batch_size).all()

                if not sources:
                    break

                for source in sources:
                    try:
                        content_hash = self.calculate_content_hash(source.content_full)  # type: ignore
                        if content_hash:
                            source.content_hash = content_hash  # type: ignore
                            stats['updated'] += 1
                    except Exception as e:
                        print(f"Error calculating hash for source {source.id}: {e}")
                        stats['errors'] += 1

                    stats['processed'] += 1

                session.commit()
                print(f"Processed {stats['processed']} sources, updated {stats['updated']}...")

            return stats

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    # ========================================
    # EXISTING METHODS
    # ========================================

    # Example helper: upsert movement by canonical_name
    def upsert_movement(self, canonical_name: str, **kwargs):
        session = self.get_session()
        try:
            m = session.query(Movement).filter(Movement.canonical_name == canonical_name).one_or_none()
            if m is None:
                m = Movement(canonical_name=canonical_name, **kwargs)
                session.add(m)
            else:
                for k, v in kwargs.items():
                    if hasattr(m, k) and v is not None:
                        setattr(m, k, v)
                # updated_at will be set automatically by SQLAlchemy onupdate
            session.commit()
            return m
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def add_source(self, source_dict: dict):
        """
        source_dict should contain keys: movement_id (or canonical_name), url, source_name, domain, content_full, etc.
        If movement_id not provided, we can try to resolve by canonical_name.
        """
        session = self.get_session()
        try:
            movement_id = source_dict.get("movement_id")
            canonical_name = source_dict.get("canonical_name")
            if not movement_id and canonical_name:
                m = session.query(Movement).filter(Movement.canonical_name == canonical_name).one_or_none()
                if m:
                    movement_id = m.id
                else:
                    m = Movement(canonical_name=canonical_name)
                    session.add(m)
                    session.flush()  # assign id
                    movement_id = m.id

            src = Source(
                movement_id=movement_id,
                source_name=source_dict.get("source_name"),
                source_type=source_dict.get("source_type"),
                author=source_dict.get("author"),
                domain=source_dict.get("domain"),
                language=source_dict.get("language"),
                publication_date=source_dict.get("publication_date"),
                url=source_dict.get("url"),
                content_excerpt=source_dict.get("content_excerpt"),
                content_full=source_dict.get("content_full"),
                lemma_text=source_dict.get("lemma_text"),
                keywords_found=source_dict.get("keywords_found"),
                sentiment_score=source_dict.get("sentiment_score"),
                toxicity_score=source_dict.get("toxicity_score"),
                classification_label=source_dict.get("classification_label"),
            )
            session.add(src)
            session.commit()
            return src
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def insert_source_safe(self, movement_id: int, url: str, content_full: Optional[str] = None,
                          check_duplicates: bool = True, **kwargs) -> Source:
        """
        Insert a new source with automatic duplicate detection.
        Returns existing source if duplicate found, otherwise creates new one.
        """
        session = self.get_session()
        try:
            # Check for URL duplicate first (fast check)
            existing = session.query(Source).filter(Source.url == url).first()
            if existing:
                print(f"⚠️  Source with URL already exists: {url}")
                return existing

            # Calculate content hash if content provided
            content_hash = None
            if content_full and check_duplicates:
                content_hash = self.calculate_content_hash(content_full)

                # Check for content duplicate
                if content_hash:
                    duplicate = session.query(Source).filter(Source.content_hash == content_hash).first()
                    if duplicate:
                        print(f"⚠️  Duplicate content found (hash: {content_hash[:8]}...), returning existing source")
                        return duplicate

            # Create new source
            source_data = {
                'movement_id': movement_id,
                'url': url,
                'content_full': content_full,
                'content_hash': content_hash,
                **kwargs
            }

            new_source = Source(**source_data)
            session.add(new_source)
            session.commit()

            print(f"✅ New source inserted: {url}")
            return new_source

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def bulk_insert_sources_safe(self, sources_data: List[dict], check_duplicates: bool = True) -> dict:
        """
        Bulk insert sources with duplicate detection.
        sources_data: List of dicts with source data including 'movement_id', 'url', etc.
        Returns statistics about insertions.
        """
        session = self.get_session()
        stats = {
            'total': len(sources_data),
            'inserted': 0,
            'duplicates_skipped': 0,
            'errors': 0
        }

        try:
            for i, source_data in enumerate(sources_data):
                try:
                    # Extract required fields
                    movement_id = source_data.pop('movement_id')
                    url = source_data.pop('url')
                    content_full = source_data.pop('content_full', None)

                    # Check for duplicates
                    skip = False

                    # URL check
                    existing = session.query(Source).filter(Source.url == url).first()
                    if existing:
                        stats['duplicates_skipped'] += 1
                        skip = True

                    # Content hash check
                    if not skip and content_full and check_duplicates:
                        content_hash = self.calculate_content_hash(content_full)
                        if content_hash:
                            duplicate = session.query(Source).filter(Source.content_hash == content_hash).first()
                            if duplicate:
                                stats['duplicates_skipped'] += 1
                                skip = True
                            else:
                                source_data['content_hash'] = content_hash

                    if not skip:
                        new_source = Source(
                            movement_id=movement_id,
                            url=url,
                            content_full=content_full,
                            **source_data
                        )
                        session.add(new_source)
                        stats['inserted'] += 1

                    # Progress reporting
                    if (i + 1) % 100 == 0:
                        print(f"Processed {i + 1}/{stats['total']} sources...")

                except Exception as e:
                    print(f"Error processing source {i}: {e}")
                    stats['errors'] += 1

            session.commit()

            print("✅ Bulk insert completed:")
            print(f"   • Total: {stats['total']}")
            print(f"   • Inserted: {stats['inserted']}")
            print(f"   • Duplicates skipped: {stats['duplicates_skipped']}")
            print(f"   • Errors: {stats['errors']}")

            return stats

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

# Ensure SQLite enforces foreign key constraints when a sqlite3 connection is used
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()