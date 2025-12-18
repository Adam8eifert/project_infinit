# database/db_connector.py
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine import Engine
import sqlite3
import datetime
from typing import Optional

from .models import Base, Movement, Alias, Location, Source
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
        self.db_uri = uri or getattr(config, "DB_URI", "sqlite:///data.db")
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

# Ensure SQLite enforces foreign key constraints when a sqlite3 connection is used
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()