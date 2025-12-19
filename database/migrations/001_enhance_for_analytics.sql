-- database/migrations/001_enhance_for_analytics.sql
-- Migration script to add analytical enhancements to existing database

-- Add new columns to movements table
ALTER TABLE movements ADD COLUMN IF NOT EXISTS follower_estimate INTEGER;
ALTER TABLE movements ADD COLUMN IF NOT EXISTS social_media_presence TEXT;
ALTER TABLE movements ADD COLUMN IF NOT EXISTS legal_status VARCHAR(64);
ALTER TABLE movements ADD COLUMN IF NOT EXISTS controversy_level INTEGER;
ALTER TABLE movements ADD COLUMN IF NOT EXISTS influence_score FLOAT;
ALTER TABLE movements ADD COLUMN IF NOT EXISTS growth_trend VARCHAR(32);

-- Add new columns to sources table
ALTER TABLE sources ADD COLUMN IF NOT EXISTS word_count INTEGER;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS reading_time_minutes INTEGER;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);
ALTER TABLE sources ADD COLUMN IF NOT EXISTS scraped_by VARCHAR(64);
ALTER TABLE sources ADD COLUMN IF NOT EXISTS social_shares INTEGER DEFAULT 0;
ALTER TABLE sources ADD COLUMN IF NOT EXISTS backlinks_count INTEGER DEFAULT 0;

-- Add new columns to locations table
ALTER TABLE locations ADD COLUMN IF NOT EXISTS latitude FLOAT;
ALTER TABLE locations ADD COLUMN IF NOT EXISTS longitude FLOAT;
ALTER TABLE locations ADD COLUMN IF NOT EXISTS population INTEGER;
ALTER TABLE locations ADD COLUMN IF NOT EXISTS location_type VARCHAR(32);
ALTER TABLE locations ADD COLUMN IF NOT EXISTS activity_level VARCHAR(32);
ALTER TABLE locations ADD COLUMN IF NOT EXISTS last_activity_date TIMESTAMP;

-- Create new analytical tables
CREATE TABLE IF NOT EXISTS temporal_analysis (
    id SERIAL PRIMARY KEY,
    movement_id INTEGER REFERENCES movements(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    mention_count INTEGER DEFAULT 0 NOT NULL,
    source_count INTEGER DEFAULT 0 NOT NULL,
    sentiment_avg FLOAT,
    toxicity_avg FLOAT,
    positive_mentions INTEGER DEFAULT 0 NOT NULL,
    negative_mentions INTEGER DEFAULT 0 NOT NULL,
    neutral_mentions INTEGER DEFAULT 0 NOT NULL,
    unique_domains INTEGER DEFAULT 0 NOT NULL,
    unique_authors INTEGER DEFAULT 0 NOT NULL,
    sentiment_trend VARCHAR(16),
    activity_trend VARCHAR(16),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS geographic_analysis (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) ON DELETE CASCADE,
    analysis_date DATE NOT NULL,
    movement_count INTEGER DEFAULT 0 NOT NULL,
    total_mentions INTEGER DEFAULT 0 NOT NULL,
    active_movements INTEGER DEFAULT 0 NOT NULL,
    avg_sentiment FLOAT,
    sentiment_distribution VARCHAR(255),
    dominant_category VARCHAR(128),
    category_distribution TEXT,
    regional_risk_score FLOAT,
    high_risk_movements INTEGER DEFAULT 0 NOT NULL,
    population_density FLOAT,
    urban_rural_ratio FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS source_quality (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE CASCADE,
    credibility_score FLOAT,
    bias_score FLOAT,
    reliability_score FLOAT,
    fact_check_status VARCHAR(32),
    fact_check_source VARCHAR(255),
    last_checked TIMESTAMP,
    content_accuracy FLOAT,
    source_diversity FLOAT,
    domain_trust_score FLOAT,
    domain_category VARCHAR(64),
    is_satirical FLOAT,
    is_opinion FLOAT,
    contains_misinformation FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS ix_temporal_movement_date ON temporal_analysis(movement_id, analysis_date);
CREATE INDEX IF NOT EXISTS ix_temporal_date ON temporal_analysis(analysis_date);
CREATE INDEX IF NOT EXISTS ix_geographic_location_date ON geographic_analysis(location_id, analysis_date);
CREATE INDEX IF NOT EXISTS ix_geographic_date ON geographic_analysis(analysis_date);
CREATE INDEX IF NOT EXISTS ix_source_quality_source ON source_quality(source_id);
CREATE INDEX IF NOT EXISTS ix_source_quality_credibility ON source_quality(credibility_score);
CREATE INDEX IF NOT EXISTS ix_source_quality_status ON source_quality(fact_check_status);
CREATE INDEX IF NOT EXISTS ix_sources_content_hash ON sources(content_hash);

-- Create unique constraints
ALTER TABLE temporal_analysis ADD CONSTRAINT IF NOT EXISTS unique_temporal_movement_date
    UNIQUE (movement_id, analysis_date);
ALTER TABLE geographic_analysis ADD CONSTRAINT IF NOT EXISTS unique_geographic_location_date
    UNIQUE (location_id, analysis_date);
ALTER TABLE source_quality ADD CONSTRAINT IF NOT EXISTS unique_source_quality_source
    UNIQUE (source_id);

-- Update trigger for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers to new tables
DROP TRIGGER IF EXISTS update_temporal_analysis_updated_at ON temporal_analysis;
CREATE TRIGGER update_temporal_analysis_updated_at
    BEFORE UPDATE ON temporal_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_geographic_analysis_updated_at ON geographic_analysis;
CREATE TRIGGER update_geographic_analysis_updated_at
    BEFORE UPDATE ON geographic_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_source_quality_updated_at ON source_quality;
CREATE TRIGGER update_source_quality_updated_at
    BEFORE UPDATE ON source_quality
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();