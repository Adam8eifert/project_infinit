# database/models/source_quality.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class SourceQuality(Base):
    """
    Quality metrics and credibility assessment for sources.
    Helps filter and weight sources in analysis.
    """
    __tablename__ = "source_quality"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)

    # Credibility metrics
    credibility_score = Column(Float, nullable=True)       # 0-1 scale
    bias_score = Column(Float, nullable=True)             # -1 (left) to 1 (right) scale
    reliability_score = Column(Float, nullable=True)      # 0-1 scale

    # Fact-checking status
    fact_check_status = Column(String(32), nullable=True)  # verified, disputed, unverified, unknown
    fact_check_source = Column(String(255), nullable=True) # who did the fact check
    last_checked = Column(DateTime, nullable=True)

    # Content quality
    content_accuracy = Column(Float, nullable=True)       # 0-1 scale
    source_diversity = Column(Float, nullable=True)       # 0-1 scale (how many different sources confirm)

    # Domain reputation
    domain_trust_score = Column(Float, nullable=True)     # 0-1 scale from external services
    domain_category = Column(String(64), nullable=True)   # news, blog, forum, social, academic, etc.

    # Automated flags
    is_satirical = Column(Float, nullable=True)           # probability 0-1
    is_opinion = Column(Float, nullable=True)             # probability 0-1
    contains_misinformation = Column(Float, nullable=True) # probability 0-1

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    source = relationship("Source", back_populates="quality_metrics")

    def __repr__(self):
        return f"<SourceQuality(source_id={self.source_id}, credibility={self.credibility_score})>"

# Indexes
# Index("ix_source_quality_source", SourceQuality.source_id, unique=True)
# Index("ix_source_quality_credibility", SourceQuality.credibility_score)
# Index("ix_source_quality_status", SourceQuality.fact_check_status)