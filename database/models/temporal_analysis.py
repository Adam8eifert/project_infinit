# database/models/temporal_analysis.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class TemporalAnalysis(Base):
    """
    Time-series analysis data for movements.
    Tracks trends over time for analytics and reporting.
    """
    __tablename__ = "temporal_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movement_id = Column(Integer, ForeignKey("movements.id", ondelete="CASCADE"), nullable=False)

    # Time dimension
    analysis_date = Column(Date, nullable=False, index=True)

    # Metrics
    mention_count = Column(Integer, default=0, nullable=False)
    source_count = Column(Integer, default=0, nullable=False)
    sentiment_avg = Column(Float, nullable=True)
    toxicity_avg = Column(Float, nullable=True)

    # Content analysis
    positive_mentions = Column(Integer, default=0, nullable=False)
    negative_mentions = Column(Integer, default=0, nullable=False)
    neutral_mentions = Column(Integer, default=0, nullable=False)

    # Source diversity
    unique_domains = Column(Integer, default=0, nullable=False)
    unique_authors = Column(Integer, default=0, nullable=False)

    # Trend indicators
    sentiment_trend = Column(String(16), nullable=True)   # improving, worsening, stable
    activity_trend = Column(String(16), nullable=True)    # increasing, decreasing, stable

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    movement = relationship("Movement", back_populates="temporal_analyses")

    def __repr__(self):
        return f"<TemporalAnalysis(movement_id={self.movement_id}, date={self.analysis_date}, mentions={self.mention_count})>"

# Indexes for efficient time-series queries
Index("ix_temporal_movement_date", TemporalAnalysis.movement_id, TemporalAnalysis.analysis_date, unique=True)
Index("ix_temporal_date", TemporalAnalysis.analysis_date)