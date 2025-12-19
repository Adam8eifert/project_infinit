# database/models/location.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movement_id = Column(Integer, ForeignKey("movements.id", ondelete="CASCADE"), nullable=False)

    municipality = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    region = Column(String(64), nullable=True)
    year_founded = Column(Integer, nullable=True)

    # NEW: Geographic coordinates for spatial analysis
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # NEW: Demographic data
    population = Column(Integer, nullable=True)
    location_type = Column(String(32), nullable=True)     # headquarters, branch, event, meeting_place

    # NEW: Activity metrics
    activity_level = Column(String(32), nullable=True)    # high, medium, low, inactive
    last_activity_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    movement = relationship("Movement", back_populates="locations")
    geographic_analyses = relationship("GeographicAnalysis", back_populates="location", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Location(id={self.id}, municipality={self.municipality})>"