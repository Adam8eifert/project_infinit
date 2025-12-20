# database/models/geographic_analysis.py
from sqlalchemy import Column, Integer, String, Float, Text, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class GeographicAnalysis(Base):
    """
    Geographic analysis data for spatial patterns and regional insights.
    Aggregates data by location for mapping and regional analysis.
    """
    __tablename__ = "geographic_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)

    # Time dimension
    analysis_date = Column(Date, nullable=False, index=True)

    # Regional metrics
    movement_count = Column(Integer, default=0, nullable=False)
    total_mentions = Column(Integer, default=0, nullable=False)
    active_movements = Column(Integer, default=0, nullable=False)

    # Sentiment by region
    avg_sentiment = Column(Float, nullable=True)
    sentiment_distribution = Column(String(255), nullable=True)  # JSON-like: "positive:60,neutral:30,negative:10"

    # Category dominance
    dominant_category = Column(String(128), nullable=True)
    category_distribution = Column(Text, nullable=True)    # JSON of category counts

    # Risk assessment
    regional_risk_score = Column(Float, nullable=True)     # 0-1 scale
    high_risk_movements = Column(Integer, default=0, nullable=False)

    # Demographic correlations
    population_density = Column(Float, nullable=True)
    urban_rural_ratio = Column(Float, nullable=True)       # 0=rural, 1=urban

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    location = relationship("Location", back_populates="geographic_analyses")

    def __repr__(self):
        return f"<GeographicAnalysis(location_id={self.location_id}, date={self.analysis_date}, movements={self.movement_count})>"

# Indexes for efficient spatial queries
# Index("ix_geographic_location_date", GeographicAnalysis.location_id, GeographicAnalysis.analysis_date, unique=True)
# Index("ix_geographic_date", GeographicAnalysis.analysis_date)