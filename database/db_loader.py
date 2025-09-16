# 📁 database/db_loader.py
# Připojení k PostgreSQL + definice tabulek podle uživatelského schématu

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import datetime
import config

Base = declarative_base()

class Movement(Base):
    __tablename__ = 'movements'

    id = Column(Integer, primary_key=True)
    canonical_name = Column(String, nullable=False)
    registration = Column(Integer)
    rating = Column(String)

    aliases = relationship("Alias", back_populates="movement")
    locations = relationship("Location", back_populates="movement")
    sources = relationship("Source", back_populates="movement")

class Alias(Base):
    __tablename__ = 'aliases'

    id = Column(Integer, primary_key=True)
    movement_id = Column(Integer, ForeignKey('movements.id'))
    alias = Column(String)

    movement = relationship("Movement", back_populates="aliases")

class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True)
    movement_id = Column(Integer, ForeignKey('movements.id'))
    municipality = Column(String)
    district = Column(String)
    region = Column(String)
    year_founded = Column(Integer)

    movement = relationship("Movement", back_populates="locations")

class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    movement_id = Column(Integer, ForeignKey('movements.id'))
    source_name = Column(String)
    source_type = Column(String)
    publication_date = Column(DateTime, default=datetime.datetime.utcnow)
    sentiment_rating = Column(String)
    url = Column(String, unique=True)

    movement = relationship("Movement", back_populates="sources")

class DBConnector:
    def __init__(self):
        self.engine = create_engine(config.DB_URI)
        self.Session = sessionmaker(bind=self.engine)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def insert_sources(self, sources: list):
        session = self.Session()
        for src in sources:
            s = Source(
                movement_id=src.get("movement_id"),
                source_name=src.get("source_name"),
                source_type=src.get("source_type"),
                publication_date=src.get("publication_date"),
                sentiment_rating=src.get("sentiment_rating"),
                url=src.get("url")
            )
            session.add(s)
        session.commit()
        session.close()