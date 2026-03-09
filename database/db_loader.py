# 📁 database/db_loader.py
# SQLAlchemy models and database connector for new schema
# Project Infinit - Religious Movements Analysis

import os
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, Numeric, ForeignKey, Enum, DateTime, Table, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
import enum

DEFAULT_DB_URI = 'postgresql+psycopg2://username:20665166@localhost:5432/nsm_db'


def _resolve_db_uri() -> str:
    try:
        import config as app_config
        config_db_uri = getattr(app_config, 'DB_URI', None)
    except Exception:
        config_db_uri = None

    return os.getenv('DB_URI', config_db_uri or DEFAULT_DB_URI)


Base = declarative_base()


# ============================================================
# ENUM TYPES
# ============================================================

class SentimentLabel(str, enum.Enum):
    """Sentiment classification"""
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class RiskLevel(str, enum.Enum):
    """Risk level classification"""
    low = "low"
    medium = "medium"
    high = "high"


class SourceType(str, enum.Enum):
    """Source type classification"""
    rss = "rss"
    website = "website"
    api = "api"
    manual = "manual"
    archive = "archive"


# ============================================================
# ASSOCIATION TABLES (M:N Relationships)
# ============================================================

article_movements = Table(
    'article_movements',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True),
    Column('movement_id', Integer, ForeignKey('movements.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_article_movements_article', 'article_id'),
    Index('idx_article_movements_movement', 'movement_id')
)

article_persons = Table(
    'article_persons',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True),
    Column('person_id', Integer, ForeignKey('persons.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_article_persons_article', 'article_id'),
    Index('idx_article_persons_person', 'person_id')
)

article_locations = Table(
    'article_locations',
    Base.metadata,
    Column('article_id', Integer, ForeignKey('articles.id', ondelete='CASCADE'), primary_key=True),
    Column('location_id', Integer, ForeignKey('locations.id', ondelete='CASCADE'), primary_key=True),
    Index('idx_article_locations_article', 'article_id'),
    Index('idx_article_locations_location', 'location_id')
)


# ============================================================
# MODELS (ORM)
# ============================================================

class Article(Base):
    """
    Main articles table - stores scraped content with sentiment & risk analysis
    Consolidates both scraped web content and academic documents
    """
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(500), nullable=True, index=True, unique=True)
    
    # Source metadata (previously in separate Source table)
    source_name = Column(String(255), nullable=True)
    source_type = Column(Enum(SourceType), nullable=True, index=True)
    author = Column(String(255), nullable=True)
    domain = Column(String(255), nullable=True, index=True)
    language = Column(String(10), nullable=True, default='cs')
    published_at = Column(TIMESTAMP, nullable=True)
    
    # NLP Analysis
    sentiment_score = Column(Numeric(4, 3), nullable=True)  # -1 to 1
    sentiment_label = Column(Enum(SentimentLabel), nullable=True)
    risk_score = Column(Numeric(4, 3), nullable=True)  # 0 to 1
    risk_level = Column(Enum(RiskLevel), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    movements = relationship(
        "Movement",
        secondary="article_movements",
        back_populates="articles"
    )
    persons = relationship(
        "Person",
        secondary="article_persons",
        back_populates="articles"
    )
    locations = relationship(
        "Location",
        secondary="article_locations",
        back_populates="articles"
    )


class Movement(Base):
    """
    Religious movements/cults database
    """
    __tablename__ = "movements"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    alias = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    founded_year = Column(Integer, nullable=True)
    concepts = Column(Text, nullable=True)
    
    # Relationships
    articles = relationship(
        "Article",
        secondary="article_movements",
        back_populates="movements"
    )


class Person(Base):
    """
    Notable persons - leaders, members, researchers mentioned in articles
    """
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    alias = Column(String(255), nullable=True)
    
    # Relationships
    articles = relationship(
        "Article",
        secondary="article_persons",
        back_populates="persons"
    )


class Location(Base):
    """
    Geographic locations - countries, cities, regions
    """
    __tablename__ = "locations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    country = Column(String(100), nullable=True)
    
    # Relationships
    articles = relationship(
        "Article",
        secondary="article_locations",
        back_populates="locations"
    )


class SocialMediaPost(Base):
    """
    Social media posts from Reddit, YouTube, Telegram, Mastodon
    Both discussion ABOUT NRM and content FROM NRM
    """
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, index=True)  # reddit, youtube, telegram, mastodon
    author = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    url = Column(String(1000), nullable=False, unique=True, index=True)
    created_at = Column(TIMESTAMP, nullable=True)
    
    # Engagement metrics
    likes = Column(Integer, nullable=True, default=0)
    comments = Column(Integer, nullable=True, default=0)
    shares = Column(Integer, nullable=True, default=0)
    
    # Collection metadata
    query = Column(String(500), nullable=True)  # Search query used
    raw_json = Column(Text, nullable=True)  # Full API response for future analysis
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Movement linkage (detected by NLP or manual tagging)
    movement_id = Column(Integer, ForeignKey('movements.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # NLP Analysis
    sentiment_score = Column(Numeric(4, 3), nullable=True)
    sentiment_label = Column(Enum(SentimentLabel), nullable=True)
    risk_score = Column(Numeric(4, 3), nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    
    # Relationships
    movement = relationship("Movement")


class GoogleTrend(Base):
    """
    Google Trends data for tracking search interest in religious movements
    """
    __tablename__ = "google_trends"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    date = Column(TIMESTAMP, nullable=False, index=True)
    interest_value = Column(Integer, nullable=False)  # 0-100 scale
    region = Column(String(10), nullable=True)  # CZ, SK, etc.
    
    # Movement linkage
    movement_id = Column(Integer, ForeignKey('movements.id', ondelete='SET NULL'), nullable=True, index=True)
    
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    movement = relationship("Movement")
    
    # Composite index for efficient time-series queries
    __table_args__ = (
        Index('idx_trends_keyword_date', 'keyword', 'date'),
        Index('idx_trends_movement_date', 'movement_id', 'date'),
    )


# ============================================================
# DATABASE CONNECTOR CLASS
# ============================================================

class DBConnector:
    """
    Database management and helper methods
    """
    
    def __init__(self, db_uri: Optional[str] = None):
        self.db_uri = db_uri or _resolve_db_uri()
        self.engine = create_engine(self.db_uri, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def create_tables(self):
        """Create all tables from models"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            raise
    
    def drop_all_tables(self):
        """Drop all tables (dangerous - for testing only)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            print("⚠️  All tables dropped")
        except Exception as e:
            print(f"❌ Error dropping tables: {e}")
            raise
    
    def get_session(self):
        """Get new database session"""
        return self.SessionLocal()
    
    def add_article(self, title, content, url=None, source_name=None, source_type=None,
                    author=None, domain=None, language='cs', published_at=None):
        """Add new article"""
        session = self.get_session()
        try:
            # Check if URL already exists
            if url:
                existing = session.query(Article).filter(Article.url == url).first()
                if existing:
                    print(f"⚠️  Article with URL already exists: {url}")
                    session.close()
                    return existing
            
            article = Article(
                title=title,
                content=content,
                url=url,
                source_name=source_name,
                source_type=source_type,
                author=author,
                domain=domain,
                language=language,
                published_at=published_at
            )
            session.add(article)
            session.commit()
            session.close()
            return article
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding article: {e}")
            raise
    
    def add_movement(self, name, alias=None, category=None, founded_year=None, concepts=None):
        """Add or get movement"""
        session = self.get_session()
        try:
            # Check if exists
            movement = session.query(Movement).filter(Movement.name == name).first()
            if movement:
                session.close()
                return movement
            
            # Create new
            movement = Movement(
                name=name,
                alias=alias,
                category=category,
                founded_year=founded_year,
                concepts=concepts,
            )
            session.add(movement)
            session.commit()
            session.close()
            return movement
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding movement: {e}")
            raise
    
    def add_person(self, name, alias=None):
        """Add or get person"""
        session = self.get_session()
        try:
            # Check if exists
            person = session.query(Person).filter(Person.name == name).first()
            if person:
                session.close()
                return person
            
            # Create new
            person = Person(name=name, alias=alias)
            session.add(person)
            session.commit()
            session.close()
            return person
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding person: {e}")
            raise
    
    def add_location(self, name, country=None):
        """Add or get location"""
        session = self.get_session()
        try:
            # Check if exists (not unique to allow duplicates with different countries)
            location = session.query(Location).filter(
                Location.name == name,
                Location.country == country
            ).first()
            if location:
                session.close()
                return location
            
            # Create new
            location = Location(name=name, country=country)
            session.add(location)
            session.commit()
            session.close()
            return location
        except Exception as e:
            session.rollback()
            print(f"❌ Error adding location: {e}")
            raise
    
    def link_article_movement(self, article_id, movement_id):
        """Link article to movement"""
        session = self.get_session()
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            movement = session.query(Movement).filter(Movement.id == movement_id).first()
            
            if not article or not movement:
                raise ValueError("Article or Movement not found")
            
            if movement not in article.movements:
                article.movements.append(movement)
            
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            print(f"❌ Error linking article to movement: {e}")
            raise
    
    def link_article_person(self, article_id, person_id):
        """Link article to person"""
        session = self.get_session()
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            person = session.query(Person).filter(Person.id == person_id).first()
            
            if not article or not person:
                raise ValueError("Article or Person not found")
            
            if person not in article.persons:
                article.persons.append(person)
            
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            print(f"❌ Error linking article to person: {e}")
            raise
    
    def link_article_location(self, article_id, location_id):
        """Link article to location"""
        session = self.get_session()
        try:
            article = session.query(Article).filter(Article.id == article_id).first()
            location = session.query(Location).filter(Location.id == location_id).first()
            
            if not article or not location:
                raise ValueError("Article or Location not found")
            
            if location not in article.locations:
                article.locations.append(location)
            
            session.commit()
            session.close()
        except Exception as e:
            session.rollback()
            print(f"❌ Error linking article to location: {e}")
            raise
    
    def get_article_count(self):
        """Get total article count"""
        session = self.get_session()
        try:
            count = session.query(Article).count()
            return count
        finally:
            session.close()
    
    def get_movement_count(self):
        """Get total movement count"""
        session = self.get_session()
        try:
            count = session.query(Movement).count()
            return count
        finally:
            session.close()
    
    def get_person_count(self):
        """Get total person count"""
        session = self.get_session()
        try:
            count = session.query(Person).count()
            return count
        finally:
            session.close()
    
    def get_location_count(self):
        """Get total location count"""
        session = self.get_session()
        try:
            count = session.query(Location).count()
            return count
        finally:
            session.close()
    
    def bulk_insert_articles(self, articles_data):
        """Bulk insert articles"""
        session = self.get_session()
        try:
            count = 0
            for article_data in articles_data:
                # Check for duplicate URL
                if article_data.get('url'):
                    existing = session.query(Article).filter(
                        Article.url == article_data['url']
                    ).first()
                    if existing:
                        continue
                
                article = Article(**article_data)
                session.add(article)
                count += 1
            
            session.commit()
            print(f"✅ Inserted {count} articles")
            return count
        except Exception as e:
            session.rollback()
            print(f"❌ Error bulk inserting articles: {e}")
            raise
        finally:
            session.close()


# ============================================================
# INITIALIZATION
# ============================================================

if __name__ == "__main__":
    # Test connection
    db = DBConnector()
    db.create_tables()
    print(f"✅ Database initialized: {db.db_uri}")

