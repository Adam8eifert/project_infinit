# database/models/alias.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base

class Alias(Base):
    __tablename__ = "aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    movement_id = Column(Integer, ForeignKey("movements.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String(255), nullable=False, index=True)

    # Extra fields
    alias_type = Column(String(64), nullable=True)     # e.g. short, colloquial, historical
    confidence_score = Column(Float, nullable=True)     # fuzzy matching confidence

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    movement = relationship("Movement", back_populates="aliases")

    def __repr__(self):
        return f"<Alias(id={self.id}, alias={self.alias})>"

# Index("ix_aliases_alias", Alias.alias)  # Commented out to avoid conflicts