# database/models/movement.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_name = Column(String(255), nullable=False, index=True)
    registration = Column(Integer, nullable=True)
    rating = Column(String(64), nullable=True)

    # Extended fields
    category = Column(String(128), nullable=True)         # e.g. religious, esoteric, sect...
    description = Column(Text, nullable=True)
    origin_country = Column(String(64), nullable=True)
    established_year = Column(Integer, nullable=True)
    active_status = Column(String(32), nullable=True)     # active/inactive/banned/etc.
    website = Column(String(512), nullable=True)
    keywords_matched = Column(Text, nullable=True)        # CSV or JSON-like string of keywords
    sentiment_overall = Column(Float, nullable=True)      # aggregated sentiment across sources
    risk_level = Column(Integer, nullable=True)           # internal score 1-5

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    aliases = relationship("Alias", back_populates="movement", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="movement", cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="movement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Movement(id={self.id}, canonical_name={self.canonical_name})>"

# Additional indexes if desired
Index("ix_movements_canonical_name", Movement.canonical_name)