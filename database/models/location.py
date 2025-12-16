# database/models/location.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
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

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    movement = relationship("Movement", back_populates="locations")

    def __repr__(self):
        return f"<Location(id={self.id}, municipality={self.municipality})>"