# database/models/source.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # movement_id can be null for unassigned sources (e.g., scraped items not matched to movement)
    movement_id = Column(Integer, ForeignKey("movements.id", ondelete="CASCADE"), nullable=True)

    # Basic metadata
    source_name = Column(String(255), nullable=True)
    source_type = Column(String(64), nullable=True)        # e.g. article, blog, book, report
    author = Column(String(255), nullable=True)
    domain = Column(String(255), nullable=True, index=True)
    language = Column(String(16), nullable=True)

    publication_date = Column(DateTime, nullable=True)
    url = Column(String(1024), unique=True, nullable=False)

    # Content
    content_excerpt = Column(Text, nullable=True)         # short preview
    content_full = Column(Text, nullable=True)            # full text

    # NEW: Content analytics
    word_count = Column(Integer, nullable=True)
    reading_time_minutes = Column(Integer, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # for duplicate detection
    scraped_by = Column(String(64), nullable=True)        # which spider collected it

    # NEW: Social metrics
    social_shares = Column(Integer, default=0, nullable=True)
    backlinks_count = Column(Integer, default=0, nullable=True)

    # NLP / analysis fields
    lemma_text = Column(Text, nullable=True)              # lemmatized text
    keywords_found = Column(Text, nullable=True)          # comma separated or JSON-like
    sentiment_score = Column(Float, nullable=True)
    toxicity_score = Column(Float, nullable=True)
    classification_label = Column(String(128), nullable=True)  # e.g. 'critique', 'neutral', 'support'

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    movement = relationship("Movement", back_populates="sources")
    quality_metrics = relationship("SourceQuality", back_populates="source", cascade="all, delete-orphan", uselist=False)

    def __repr__(self):
        return f"<Source(id={self.id}, domain={self.domain}, url={self.url})>"

# Index("ix_sources_domain", Source.domain)
# Index("ix_sources_publication_date", Source.publication_date)