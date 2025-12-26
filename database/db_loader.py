# database/db_connector.py

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
import sqlite3
import datetime
import hashlib
from typing import Optional, List, Dict

from .models import (
    Base,
    Movement,
    Alias,
    Location,
    Source,
    TemporalAnalysis,
    GeographicAnalysis,
    SourceQuality,
)

import config  # expects config.DB_URI


class DBConnector:
    """
    Portable DB connector using SQLAlchemy.
    Works with both SQLite and PostgreSQL.

    Exposes:
      - create_tables()
      - get_session()
      - upsert helpers
      - safe insert methods (pipeline + manual)
    """

    def __init__(self, uri: Optional[str] = None):
        self.db_uri = uri or getattr(config, "DB_URI", "sqlite:///data.db")

        connect_args = {}
        if self.db_uri.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(
            self.db_uri,
            connect_args=connect_args,
            future=True,
        )

        self.SessionFactory = scoped_session(
            sessionmaker(
                bind=self.engine,
                autoflush=False,
                expire_on_commit=False,
            )
        )

    # ========================================
    # BASIC DB OPERATIONS
    # ========================================

    def create_tables(self):
        Base.metadata.create_all(self.engine, checkfirst=True)

    def drop_tables(self):
        Base.metadata.drop_all(self.engine)

    def get_session(self):
        return self.SessionFactory()

    # ========================================
    # CONTENT HASHING & DUPLICATES
    # ========================================

    def calculate_content_hash(self, text: Optional[str]) -> Optional[str]:
        """
        Calculate SHA-256 hash of normalized content.
        Used for duplicate detection across pipelines and manual inserts.
        """
        if not text:
            return None

        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def update_content_hashes(self, batch_size: int = 1000) -> dict:
        """
        Backfill content_hash for sources that do not have it yet.
        Safe to run repeatedly.
        """
        session = self.get_session()

        stats = {
            "processed": 0,
            "updated": 0,
            "errors": 0,
        }

        try:
            while True:
                sources = (
                    session.query(Source)
                    .filter(
                        Source.content_hash.is_(None),
                        Source.content_full.isnot(None),
                    )
                    .limit(batch_size)
                    .all()
                )

                if not sources:
                    break

                for src in sources:
                    try:
                        src.content_hash = self.calculate_content_hash(src.content_full)
                        stats["updated"] += 1
                    except Exception as e:
                        print(f"❌ Hash error (source_id={src.id}): {e}")
                        stats["errors"] += 1

                    stats["processed"] += 1

                session.commit()
                print(
                    f"🔄 Processed {stats['processed']} | "
                    f"Updated {stats['updated']}"
                )

            return stats

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========================================
    # MOVEMENTS
    # ========================================

    def upsert_movement(self, canonical_name: str, **fields) -> Movement:
        """
        Insert or update Movement by canonical_name.
        """
        session = self.get_session()

        try:
            movement = (
                session.query(Movement)
                .filter(Movement.canonical_name == canonical_name)
                .one_or_none()
            )

            if movement is None:
                movement = Movement(canonical_name=canonical_name, **fields)
                session.add(movement)
            else:
                for key, value in fields.items():
                    if value is not None and hasattr(movement, key):
                        setattr(movement, key, value)

            session.commit()
            return movement

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ========================================
    # SOURCES – SAFE INSERTS (PIPELINE + MANUAL)
    # ========================================

    def insert_source_safe(
        self,
        movement_id: int,
        url: str,
        content_full: Optional[str] = None,
        **extra_fields,
    ) -> Source:
        """
        Insert a source safely.

        Rules:
        - URL must be unique
        - content_hash must be unique if present
        - manual and pipeline inserts coexist
        """
        session = self.get_session()

        try:
            # Fast path – URL already exists
            existing = session.query(Source).filter(Source.url == url).first()
            if existing:
                print(f"⚠️  Source already exists (URL): {url}")
                return existing

            content_hash = self.calculate_content_hash(content_full)

            if content_hash:
                duplicate = (
                    session.query(Source)
                    .filter(Source.content_hash == content_hash)
                    .first()
                )
                if duplicate:
                    print(
                        f"⚠️  Duplicate content detected "
                        f"(hash={content_hash[:8]}…) – reusing existing source"
                    )
                    return duplicate

            source = Source(
                movement_id=movement_id,
                url=url,
