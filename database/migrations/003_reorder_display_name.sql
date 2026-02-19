-- Migration 003: Reorder display_name column to be next to canonical_name
-- PostgreSQL doesn't support MODIFY COLUMN position, so we need to recreate the column

-- Step 1: Create temporary column in correct position  
ALTER TABLE movements ADD COLUMN display_name_new VARCHAR(255);

-- Step 2: Copy data from old column
UPDATE movements SET display_name_new = display_name;

-- Step 3: Drop old column
ALTER TABLE movements DROP COLUMN display_name;

-- Step 4: Rename new column
ALTER TABLE movements RENAME COLUMN display_name_new TO display_name;

-- Step 5: Add comment for clarity
COMMENT ON COLUMN movements.display_name IS 'Oficiální název hnutí s diakritikou (vedle canonical_name)';
COMMENT ON COLUMN movements.canonical_name IS 'Jedinečný slug identifikátor bez diakritiky';
