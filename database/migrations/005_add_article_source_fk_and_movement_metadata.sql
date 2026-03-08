-- Migration 005: Articles↔Sources normalization + movement metadata
-- Date: 2026-03-08
-- Adds:
--   - movements.founded_year, movements.concepts
--   - articles.source_id, articles.language
--   - sources.source_key, sources.domain, sources.language
--   - explicit indexes for M:N join tables

-- ============================================================
-- 1) New movement metadata columns
-- ============================================================
ALTER TABLE movements ADD COLUMN IF NOT EXISTS founded_year INTEGER;
ALTER TABLE movements ADD COLUMN IF NOT EXISTS concepts TEXT;

-- ============================================================
-- 2) Article source/language columns
-- ============================================================
ALTER TABLE articles ADD COLUMN IF NOT EXISTS source_id INTEGER;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS language VARCHAR(10);

-- ============================================================
-- 3) Source registry columns
-- ============================================================
ALTER TABLE sources ADD COLUMN IF NOT EXISTS source_key VARCHAR(255);
ALTER TABLE sources ADD COLUMN IF NOT EXISTS domain VARCHAR(255);
ALTER TABLE sources ADD COLUMN IF NOT EXISTS language VARCHAR(16);

-- ============================================================
-- 4) Foreign key: articles.source_id -> sources.id
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints tc
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = 'articles'
          AND tc.constraint_name = 'fk_articles_source'
    ) THEN
        ALTER TABLE articles
            ADD CONSTRAINT fk_articles_source
            FOREIGN KEY (source_id)
            REFERENCES sources(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================
-- 5) Indexes for join tables (requested for faster JOINs)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_article_movements_article
    ON public.article_movements(article_id);

CREATE INDEX IF NOT EXISTS idx_article_movements_movement
    ON public.article_movements(movement_id);

CREATE INDEX IF NOT EXISTS idx_article_persons_article
    ON public.article_persons(article_id);

CREATE INDEX IF NOT EXISTS idx_article_persons_person
    ON public.article_persons(person_id);

CREATE INDEX IF NOT EXISTS idx_article_locations_article
    ON public.article_locations(article_id);

CREATE INDEX IF NOT EXISTS idx_article_locations_location
    ON public.article_locations(location_id);

-- ============================================================
-- 6) Supporting indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_articles_source_id
    ON public.articles(source_id);

CREATE INDEX IF NOT EXISTS idx_articles_language
    ON public.articles(language);

CREATE INDEX IF NOT EXISTS idx_movements_founded_year
    ON public.movements(founded_year);

CREATE UNIQUE INDEX IF NOT EXISTS ux_sources_source_key
    ON public.sources(source_key)
    WHERE source_key IS NOT NULL;