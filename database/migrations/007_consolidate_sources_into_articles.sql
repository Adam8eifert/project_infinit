-- 007_consolidate_sources_into_articles.sql
-- Consolidate legacy `sources` table into `articles` metadata columns.
-- This migration:
--   1) Adds source metadata columns directly on `articles`
--   2) Backfills data from `sources` and existing article fields
--   3) Drops `articles.source_id` and legacy `sources` table

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_type_enum') THEN
        CREATE TYPE source_type_enum AS ENUM ('rss', 'website', 'api', 'manual', 'archive');
    END IF;
END
$$;

ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS source_name VARCHAR(255);
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS source_type source_type_enum;
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS author VARCHAR(255);
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS domain VARCHAR(255);

UPDATE public.articles AS a
SET
    source_name = COALESCE(a.source_name, s.source_name, a.source),
    domain = COALESCE(a.domain, s.domain),
    published_at = COALESCE(a.published_at, s.publication_date),
    source_type = COALESCE(
        a.source_type,
        CASE
            WHEN lower(COALESCE(s.source_type, '')) LIKE '%rss%' THEN 'rss'::source_type_enum
            WHEN lower(COALESCE(s.source_type, '')) IN ('api', 'search_api', 'social_api') THEN 'api'::source_type_enum
            WHEN lower(COALESCE(s.source_type, '')) = 'manual' THEN 'manual'::source_type_enum
            WHEN lower(COALESCE(s.source_type, '')) IN ('archive', 'academic_pdf', 'academic_doc') THEN 'archive'::source_type_enum
            ELSE NULL
        END
    )
FROM public.sources AS s
WHERE a.source_id IS NOT NULL
  AND a.source_id = s.id;

UPDATE public.articles
SET source_name = COALESCE(source_name, source)
WHERE source_name IS NULL;

UPDATE public.articles
SET source_type = COALESCE(
    source_type,
    CASE
        WHEN lower(COALESCE(source_name, '')) LIKE '%rss%' THEN 'rss'::source_type_enum
        WHEN lower(COALESCE(source_name, '')) LIKE '%api%' THEN 'api'::source_type_enum
        WHEN url LIKE 'file://%' THEN 'archive'::source_type_enum
        ELSE 'website'::source_type_enum
    END
)
WHERE source_type IS NULL;

UPDATE public.articles
SET domain = NULLIF(regexp_replace(split_part(COALESCE(url, ''), '/', 3), '^www\.', ''), '')
WHERE domain IS NULL;

CREATE INDEX IF NOT EXISTS idx_articles_source_name ON public.articles(source_name);
CREATE INDEX IF NOT EXISTS idx_articles_source_type ON public.articles(source_type);
CREATE INDEX IF NOT EXISTS idx_articles_domain ON public.articles(domain);

DO $$
DECLARE
    fk RECORD;
BEGIN
    IF to_regclass('public.articles') IS NOT NULL AND to_regclass('public.sources') IS NOT NULL THEN
        FOR fk IN
            SELECT c.conname
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_class rt ON rt.oid = c.confrelid
            WHERE t.relname = 'articles'
              AND rt.relname = 'sources'
              AND c.contype = 'f'
        LOOP
            EXECUTE format('ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS %I', fk.conname);
        END LOOP;
    END IF;
END
$$;

ALTER TABLE public.articles DROP COLUMN IF EXISTS source_id;
ALTER TABLE public.articles DROP COLUMN IF EXISTS source;

DROP INDEX IF EXISTS public.idx_articles_source_id;
DROP INDEX IF EXISTS public.ix_articles_source_id;

DROP TABLE IF EXISTS public.source_quality CASCADE;
DROP TABLE IF EXISTS public.sources CASCADE;

COMMIT;
