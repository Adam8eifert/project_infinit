-- Migration: Add display_name column to movements table
-- Date: 2026-02-14
-- Description: Separate canonical slug from display name with diacritics
-- Compatible with: PostgreSQL, SQLite

-- Add display_name column (nullable for now)
-- Note: PostgreSQL will error if column exists, script handles this gracefully
ALTER TABLE movements ADD COLUMN display_name VARCHAR(255);

-- Create index for display_name lookups
CREATE INDEX idx_movements_display_name ON movements(display_name);

-- Populate display_name from canonical_name for existing records
-- (will be properly updated by migrate_canonical_names.py script)
UPDATE movements 
SET display_name = canonical_name 
WHERE display_name IS NULL;
