-- Migration 006: Social Media & Google Trends Tables
-- Date: 2026-03-08
-- Purpose: Add tables for social media posts and Google Trends data
-- Research focus: Track both discussion ABOUT NRM and content FROM NRM

-- ============================================================
-- 1) Social Media Posts Table
-- ============================================================
CREATE TABLE IF NOT EXISTS social_media_posts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    author VARCHAR(255),
    text TEXT NOT NULL,
    url VARCHAR(1000) NOT NULL UNIQUE,
    created_at TIMESTAMP,
    
    -- Engagement metrics
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    
    -- Collection metadata
    query VARCHAR(500),
    raw_json TEXT,
    collected_at TIMESTAMP DEFAULT NOW() NOT NULL,
    
    -- Movement linkage (FK to movements table)
    movement_id INTEGER REFERENCES movements(id) ON DELETE SET NULL,
    
    -- NLP Analysis fields
    sentiment_score NUMERIC(4, 3),
    sentiment_label VARCHAR(20),
    risk_score NUMERIC(4, 3),
    risk_level VARCHAR(20)
);

-- Indexes for social_media_posts
CREATE INDEX IF NOT EXISTS idx_social_media_platform ON social_media_posts(platform);
CREATE INDEX IF NOT EXISTS idx_social_media_url ON social_media_posts(url);
CREATE INDEX IF NOT EXISTS idx_social_media_movement_id ON social_media_posts(movement_id);
CREATE INDEX IF NOT EXISTS idx_social_media_created_at ON social_media_posts(created_at);

-- ============================================================
-- 2) Google Trends Table
-- ============================================================
CREATE TABLE IF NOT EXISTS google_trends (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(255) NOT NULL,
    date TIMESTAMP NOT NULL,
    interest_value INTEGER NOT NULL,  -- 0-100 scale
    region VARCHAR(10),  -- CZ, SK, etc.
    
    -- Movement linkage
    movement_id INTEGER REFERENCES movements(id) ON DELETE SET NULL,
    
    collected_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for google_trends
CREATE INDEX IF NOT EXISTS idx_trends_keyword ON google_trends(keyword);
CREATE INDEX IF NOT EXISTS idx_trends_date ON google_trends(date);
CREATE INDEX IF NOT EXISTS idx_trends_movement_id ON google_trends(movement_id);
CREATE INDEX IF NOT EXISTS idx_trends_keyword_date ON google_trends(keyword, date);
CREATE INDEX IF NOT EXISTS idx_trends_movement_date ON google_trends(movement_id, date);

-- ============================================================
-- 3) Comments
-- ============================================================

COMMENT ON TABLE social_media_posts IS 'Social media content: discussions ABOUT NRM and content FROM NRM';
COMMENT ON COLUMN social_media_posts.movement_id IS 'Links post to specific movement via NLP detection or manual tagging';
COMMENT ON COLUMN social_media_posts.raw_json IS 'Full API response preserved for future analysis';

COMMENT ON TABLE google_trends IS 'Google search trends for religious movements over time';
COMMENT ON COLUMN google_trends.interest_value IS 'Google Trends score 0-100';
COMMENT ON COLUMN google_trends.movement_id IS 'Links trend data to specific movement';
