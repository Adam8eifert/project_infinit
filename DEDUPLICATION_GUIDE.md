# Movement Deduplication Guide

## Problem Summary

Your `movements` table contains **169 movements**, with **24 near-duplicate groups** representing ~40+ redundant entries that should be consolidated. These are not technical database duplicates (the `canonical_name` UNIQUE constraint prevents exact matches), but **semantic duplicates** - different names for the same movement.

**Total impact**: Deduplication will reduce movements from 169 to ~129 unique entries.

## Root Causes of Duplicates

### 1. **Diacritics Lost in NLP Extraction** (Most Common)
PDF text processing strips diacritical marks from Czech characters:
- `Šinčchondží` (with diacritics, from YAML config) 
- `sincchondzi` (without diacritics, from NLP extraction)
- `Plaváček` vs `plavacek`
- `Imanuelité` vs `imanuelite`

### 2. **Prefix Variations from Different Sources**
Documents refer to the same movement with and without Czech word "Hnutí" (Movement):
- `Wicca` (direct name from some sources)
- `Hnutí Wicca` (formal name from other sources)
- Similar pattern: `Fa-lun-kung` vs `Hnutí Fa-lun-kung`

### 3. **Case Inconsistencies**
- `kristadelfiani` (lowercase, from NLP)
- `Kristadelfiáni` (proper case, from config)

### 4. **Punctuation Variations**
- `Církev Boží (celosvětová)` - with parentheses
- `Církev Boží celosveltová` - without

### 5. **Multiple Pipeline Runs**
Repeated execution of the ETL pipeline without checking for near-duplicates before insertion creates variants without proper merging logic.

## Data Organization

The database has an `aliases` table specifically for this:
- **movements** table: Canonical entries with unique `canonical_name`
- **aliases** table: Variant names linked to canonical movement
- **sources** table: All articles/content linked to movement via foreign key

Current state: Aliases table is **underutilized** - variants are being created as separate movements instead of being added to the aliases table.

## Solution: The Deduplication Script

The `database/deduplicate_movements.py` script automates the merge process:

### How it Works:
1. **Detects** movement names with >70% string similarity
2. **Chooses** the best canonical name using this preference order:
   - Longest name (usually most complete)
   - Name with diacritics (more authoritative)
   - Oldest ID (historical priority)
3. **Merges** by:
   - Creating aliases for all other variant names
   - Reassigning all sources to the canonical movement
   - Deleting the duplicate movement record

### Safety Features:
- **Dry-run mode** (default) shows what would be done without making changes
- **Merge mode** (optional `--merge` flag) performs the actual deduplication
- Preserves all source data (no content loss)
- Creates audit trail via aliases table

## Quick Start

### 1. Review the Deduplication Plan (Dry Run)
```bash
python database/deduplicate_movements.py
```
Shows 24 groups and their proposed merges. **No changes made.**

### 2. Execute the Deduplication
```bash
python database/deduplicate_movements.py --merge
```
- Merges 24 groups
- Deletes ~40 redundant movement records
- Creates ~40 alias entries
- Reassigns ~hundreds of sources

### 3. Verify Results
```bash
psql nsm_db -c "SELECT COUNT(*) FROM movements;"      # Should be ~129
psql nsm_db -c "SELECT COUNT(*) FROM aliases;"       # Should increase by ~40
psql nsm_db -c "SELECT * FROM aliases LIMIT 10;"     # Check alias samples
```

## Specific Merge Groups (Key Decisions)

| # | Will Keep | Will Alias | Reason |
|----|-----------|-----------|--------|
| 5 | Šinčchondží (ID 167) | sincchondzi (ID 48) | Keep diacritics version |
| 20 | Hnutí Wicca (ID 245) | Wicca (ID 223) | Keep formal name |
| 22 | Církev Boží (celosvětová) (ID 241) | Církev Boží celosveltová (ID 246) | Keep punctuated version |
| 3 | AllatRa (ID 142) | ALatRa (ID 23) | Keep proper capitalization |

## Preventing Future Duplicates

### 1. **Normalize Names in NLP Pipeline**
Before creating movements from extracted text:
```python
# In processing/nlp_analysis.py
normalized_name = unicodedata.normalize('NFKD', extracted_name)
# Preserve diacritics instead of stripping them
```

### 2. **Check for Existing Movement Before Insert**
```python
# In database/db_loader.py or processing modules
existing = session.query(Movement).filter(
    Movement.canonical_name.ilike(new_name)
).first()

if existing:
    # Add as alias instead of creating new movement
    add_alias(existing.id, new_name)
else:
    # Create new movement  
    create_movement(new_name)
```

### 3. **Handle Prefix Variations**
Strip common Czech prefixes before checking for duplicates:
```python
def normalize_for_comparison(name: str) -> str:
    """Remove common prefixes for deduplication."""
    prefixes = ['Hnutí ', 'Skupiny ', 'Движение ', 'Církev ']
    normalized = name
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return normalized.lower().strip()
```

### 4. **Run Deduplication Periodically**
After major ETL runs, check for new duplicates:
```bash
# Add to CI/CD pipeline or post-ETL checks
python database/deduplicate_movements.py --dry-run

# Or create a scheduled task
0 3 * * 0 cd /path/to/project && python database/deduplicate_movements.py --merge
```

## Impact Analysis

### Before Deduplication
- **Movements**: 169
- **Aliases**: ~10 (underused)
- **Redundancy**: 24 groups with ~40 duplicate entries
- **Data quality**: Some sources duplicated across alias movements

### After Deduplication
- **Movements**: ~129 (reduced by ~40)
- **Aliases**: ~50 (properly utilized)
- **Redundancy**: 0 semantic duplicates
- **Data quality**: All sources consolidat under canonical movements

### Query Impact
Reports will now show consolidated data:
```sql
-- Before: Multiple IDs for what should be one movement
SELECT COUNT(*) FROM movements WHERE canonical_name IN ('Wicca', 'Hnutí Wicca');
-- Result: 2

-- After: Single movement with variants tracked via aliases
SELECT COUNT(*) FROM movements WHERE canonical_name = 'Hnutí Wicca';
-- Result: 1

SELECT alias FROM aliases WHERE movement_id = (
    SELECT id FROM movements WHERE canonical_name = 'Hnutí Wicca'
);
-- Result: 'Wicca'
```

## Related Files
- `database/deduplicate_movements.py` - The deduplication script
- `database/models/alias.py` - Alias table definition
- `database/models/movement.py` - Movement table with UNIQUE constraint
- `processing/nlp_analysis.py` - Where NLP extraction occurs
- `processing/import_csv_to_db.py` - Where CSV imports happen
