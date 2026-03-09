# database/models/__init__.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Re-export commonly used names so other modules can import from database.models
from .movement import Movement
from .alias import Alias
from .location import Location
from .temporal_analysis import TemporalAnalysis
from .geographic_analysis import GeographicAnalysis

__all__ = ["Base", "Movement", "Alias", "Location", "TemporalAnalysis", "GeographicAnalysis"]