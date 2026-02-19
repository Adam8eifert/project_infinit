-- Migration: Single Source of Truth - Remove display_name column
-- Date: 2026-02-19
-- Description: Consolidate to canonical_name with diacritics only

-- Step 1: Copy display_name to canonical_name where canonical_name is a slug
UPDATE movements 
SET canonical_name = display_name 
WHERE display_name IS NOT NULL 
  AND canonical_name != display_name
  AND canonical_name NOT LIKE '%ě%'
  AND canonical_name NOT LIKE '%š%'
  AND canonical_name NOT LIKE '%č%'
  AND canonical_name NOT LIKE '%ř%'
  AND canonical_name NOT LIKE '%ž%'
  AND canonical_name NOT LIKE '%ý%'
  AND canonical_name NOT LIKE '%á%'
  AND canonical_name NOT LIKE '%í%'
  AND canonical_name NOT LIKE '%é%'
  AND canonical_name NOT LIKE '%ú%'
  AND canonical_name NOT LIKE '%ů%'
  AND canonical_name NOT LIKE '%ť%'
  AND canonical_name NOT LIKE '%ď%'
  AND canonical_name NOT LIKE '%ň%';

-- Step 2: Handle any remaining NULL display_name (use canonical_name as-is)
-- No action needed - canonical_name is already populated

-- Step 3: Drop display_name column
ALTER TABLE movements DROP COLUMN IF EXISTS display_name;

-- Step 4: Update comment on canonical_name
COMMENT ON COLUMN movements.canonical_name IS 'Official movement name with diacritics (single source of truth)';

-- Verification query (run manually after migration):
-- SELECT id, canonical_name FROM movements ORDER BY id LIMIT 20;
