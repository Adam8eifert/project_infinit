# Database Migration Guide: Canonical Names

## Overview

This migration adds support for canonical slugs + display names architecture:

- **canonical_name**: normalized slug without diacritics (e.g., `"hnuti-hare-krsna"`)
- **display_name**: official name with diacritics (e.g., `"Hnutí Hare Kršna"`)

This prevents duplicates caused by diacritics variations and improves data consistency.

## Quick Start (Recommended)

Run the complete automated migration workflow:

```bash
./database/migrate_all.sh
```

This will:

1. Add `display_name` column to movements table
2. Show preview of data changes (dry run)
3. Ask for confirmation
4. Apply data migration

## Manual Step-by-Step

### Step 1: Schema Migration

Add `display_name` column to database:

```bash
# Interactive (asks for confirmation)
python database/run_migration.py 002_add_display_name.sql

# Automatic (no confirmation)
python database/run_migration.py 002_add_display_name.sql --auto
```

**Compatible with:**

- PostgreSQL ✓
- SQLite ✓

### Step 2: Data Migration

Migrate existing movements to canonical format:

```bash
# Preview changes (safe, no modifications)
python processing/migrate_canonical_names.py --dry-run

# Apply changes to database
python processing/migrate_canonical_names.py --live
```

## What Gets Changed

### Schema Changes

- New column: `movements.display_name` (VARCHAR(255), nullable)
- New index: `idx_movements_display_name`

### Data Changes

**Before:**

```text
canonical_name: "Hnutí Hare Kršna"
display_name:   NULL
```

**After:**

```text
canonical_name: "hnuti-hare-krsna"
display_name:   "Hnutí Hare Kršna"
```

## Rollback

If you need to rollback (not recommended):

```sql
-- Remove display_name column
ALTER TABLE movements DROP COLUMN display_name;

-- Restore canonical_name from display_name (if you kept backups)
UPDATE movements SET canonical_name = display_name;
```

## Verification

After migration, verify the results:

```python
from database.db_loader import DBConnector, Movement

db = DBConnector()
session = db.get_session()

# Check movements with slugs
movements = session.query(Movement).limit(10).all()
for m in movements:
    print(f"{m.canonical_name:30} → {m.display_name}")

session.close()
```

Expected output:

```text
hnuti-hare-krsna               → Hnutí Hare Kršna
cirkev-sjednoceni              → Církev sjednocení
scientologicka-cirkev          → Scientologická církev
...
```

## Troubleshooting

### Error: "column already exists"

The migration script handles this gracefully - it means `display_name` was already added. Skip to Step 2.

### Error: "no such column: movements.display_name"

You need to run Step 1 (schema migration) first.

### No movements matched in data migration

Check that `extracting/sources_config.yaml` uses the new format:

```yamlyaml
known_movements:
  new_religious_movements:
    - canonical: "hnuti-gralu"
      display: "Hnutí Grálu"
```

Not the old format:

```yamlyaml
known_movements:
  new_religious_movements: ["Hnutí Grálu", ...]
```

## Next Steps

After successful migration:

1. Run the ETL pipeline:

   ```bash
   python main.py
   ```

2. New CSV/PDF imports will automatically use canonical matching

3. All existing sources are now linked via canonical slugs

## Files Modified

- `database/migrations/002_add_display_name.sql` - Schema migration
- `processing/migrate_canonical_names.py` - Data migration script
- `database/run_migration.py` - Universal migration runner
- `database/migrate_all.sh` - Complete automated workflow
