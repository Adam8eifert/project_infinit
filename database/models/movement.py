# database/models/movement.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Movement(Base):
    __tablename__ = "movements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_name = Column(String(255), nullable=False, unique=True, index=True)  # slug bez diakritiky
    display_name = Column(String(255), nullable=True)  # oficiální název s diakritikou
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

    # NEW: Enhanced analytics fields
    follower_estimate = Column(Integer, nullable=True)    # estimated number of followers
    social_media_presence = Column(Text, nullable=True)   # JSON: {"twitter": "handle", "facebook": "url"}
    legal_status = Column(String(64), nullable=True)      # registered, unregistered, banned, monitored
    controversy_level = Column(Integer, nullable=True)    # 1-5 scale of public controversy
    influence_score = Column(Float, nullable=True)        # calculated influence metric 0-1
    growth_trend = Column(String(32), nullable=True)      # growing, stable, declining, unknown

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    aliases = relationship("Alias", back_populates="movement", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="movement", cascade="all, delete-orphan")
    sources = relationship("Source", back_populates="movement", cascade="all, delete-orphan")
    temporal_analyses = relationship("TemporalAnalysis", back_populates="movement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Movement(id={self.id}, canonical_name={self.canonical_name})>"

# Additional indexes if desired
# Index("ix_movements_canonical_name", Movement.canonical_name)  # Commented out to avoid conflicts