-- 📁 database/schema.sql
-- New database schema for Project Infinit
-- Simplified structure: Articles with M:N relationships

-- ============================================================
-- 1️⃣ ENUM TYPES
-- ============================================================

CREATE TYPE sentiment_label_enum AS ENUM (
    'positive',
    'neutral',
    'negative'
);

CREATE TYPE risk_level_enum AS ENUM (
    'low',
    'medium',
    'high'
);


-- ============================================================
-- 2️⃣ ARTICLES TABLE (Main table with NLP analysis)
-- ============================================================

CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    
    -- Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255),
    source_id INT,
    language VARCHAR(10),
    url VARCHAR(500) UNIQUE,
    published_at TIMESTAMP,
    
    -- NLP Analysis
    sentiment_score NUMERIC(4,3) CHECK (sentiment_score BETWEEN -1 AND 1),
    sentiment_label sentiment_label_enum,
    
    risk_score NUMERIC(4,3) CHECK (risk_score BETWEEN 0 AND 1),
    risk_level risk_level_enum,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_articles_url (url),
    INDEX idx_articles_created_at (created_at),
    INDEX idx_articles_source_id (source_id),
    INDEX idx_articles_language (language)
);


-- ============================================================
-- 3️⃣ MOVEMENTS TABLE (Religious movements/cults)
-- ============================================================

CREATE TABLE movements (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    alias VARCHAR(255),
    category VARCHAR(100),
    founded_year INT,
    concepts TEXT,
    
    INDEX idx_movements_name (name),
    INDEX idx_movements_founded_year (founded_year)
);


-- ============================================================
-- 4️⃣ PERSONS TABLE (Notable people)
-- ============================================================

CREATE TABLE persons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    alias VARCHAR(255),
    
    INDEX idx_persons_name (name)
);


-- ============================================================
-- 5️⃣ LOCATIONS TABLE (Geographic data)
-- ============================================================

CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100),
    
    INDEX idx_locations_name (name),
    INDEX idx_locations_country (country)
);


-- ============================================================
-- 6️⃣ SOURCES TABLE (normalized media/source registry)
-- ============================================================

CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    movement_id INT REFERENCES movements(id) ON DELETE SET NULL,
    source_key VARCHAR(255) UNIQUE,
    source_name VARCHAR(255),
    source_type VARCHAR(100),
    domain VARCHAR(255),
    language VARCHAR(16),
    publication_date TIMESTAMP,
    sentiment_rating VARCHAR(50),
    url VARCHAR(500) UNIQUE,
    content_full TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_sources_source_key (source_key),
    INDEX idx_sources_source_name (source_name),
    INDEX idx_sources_source_type (source_type)
);

ALTER TABLE articles
ADD CONSTRAINT fk_articles_source
FOREIGN KEY (source_id)
REFERENCES sources(id);


-- ============================================================
-- 7️⃣ ASSOCIATION TABLES (M:N Relationships with CASCADE)
-- ============================================================

-- Article ↔ Movements
CREATE TABLE article_movements (
    article_id INT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    movement_id INT NOT NULL REFERENCES movements(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, movement_id),
    
    INDEX idx_article_movements_article (article_id),
    INDEX idx_article_movements_movement (movement_id)
);

-- Article ↔ Persons
CREATE TABLE article_persons (
    article_id INT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    person_id INT NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, person_id),
    
    INDEX idx_article_persons_article (article_id),
    INDEX idx_article_persons_person (person_id)
);

-- Article ↔ Locations
CREATE TABLE article_locations (
    article_id INT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    location_id INT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, location_id),
    
    INDEX idx_article_locations_article (article_id),
    INDEX idx_article_locations_location (location_id)
);


-- ============================================================
-- USEFUL QUERIES (For reference, not auto-run)
-- ============================================================

/*
-- Count articles per sentiment
SELECT sentiment_label, COUNT(*) as count
FROM articles
WHERE sentiment_label IS NOT NULL
GROUP BY sentiment_label;

-- Count articles per risk level
SELECT risk_level, COUNT(*) as count
FROM articles
WHERE risk_level IS NOT NULL
GROUP BY risk_level;

-- Most mentioned movements
SELECT m.name, COUNT(DISTINCT am.article_id) as article_count
FROM movements m
LEFT JOIN article_movements am ON m.id = am.movement_id
GROUP BY m.id, m.name
ORDER BY article_count DESC;

-- Articles mentioning multiple entities
SELECT a.id, a.title, COUNT(DISTINCT am.movement_id) as movements, 
       COUNT(DISTINCT ap.person_id) as persons, COUNT(DISTINCT al.location_id) as locations
FROM articles a
LEFT JOIN article_movements am ON a.id = am.article_id
LEFT JOIN article_persons ap ON a.id = ap.article_id
LEFT JOIN article_locations al ON a.id = al.article_id
GROUP BY a.id, a.title
ORDER BY (COUNT(DISTINCT am.movement_id) + COUNT(DISTINCT ap.person_id) + COUNT(DISTINCT al.location_id)) DESC;
*/
