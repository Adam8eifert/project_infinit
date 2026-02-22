# Quick Answer: Why Duplicates Exist in `movements` Table

## TL;DR
You have **24 near-duplicate groups** (~40 redundant movements) because:
1. **NLP extraction** loses diacritical marks (sincchondzi ≠ Šinčchondží)
2. **Prefix variations** from different naming conventions (Wicca vs Hnutí Wicca)
3. **Case inconsistencies** (kristadelfiani vs Kristadelfiáni)
4. **No deduplication step** in the ETL pipeline before inserting movements

## Current Situation
| Metric | Value |
|--------|-------|
| Total single "movement" records | 169 |
| Near-duplicate groups | 24 |
| Redundant movements | ~40 |
| Aliases defined | 52 |
| Aliases needed after merge | ~90 |
| **Effective unique movements** | **~129** |

## Root Cause Analysis
Your data comes from multiple sources with different normalization:
- **PDFs** → NLP extraction → Lowercase, no diacritics
- **YAML config** → Direct seeding → Proper case, full diacritics
- **News feeds** → HTML scraping → Various conventions per source

The system creates a new `Movement` record for each unique `canonical_name`, but no pre-processing step normalizes variants before checking if they already exist.

## Examples of Duplicates

### 1. Diacritics Lost (Most Common)
```
ID 48:  sincchondzi          ← PDF text extracted (diacritics lost)
ID 167: Šinčchondží          ← YAML config (proper diacritics)
```

### 2. Prefix Variations
```
ID 223: Wicca                ← Direct from source
ID 245: Hnutí Wicca          ← Formal name with "Hnutí" prefix
```

### 3. Case Differences
```
ID 42:  kristadelfiani       ← NLP extract (lowercase)
ID 161: Kristadelfiáni       ← Config (proper case + diacritics)
```

### 4. Semantic Variations  
```
ID 141:  Rodina              ← Simple name
ID 261:  Hnutí Sjednocená rodina  ← Formal descriptive name
```

## Fix It Now

### Step 1: Review the Merge Plan (No Changes)
```bash
python database/deduplicate_movements.py
# Shows 24 groups and what will be merged
```

### Step 2: Execute the Merge
```bash
python database/deduplicate_movements.py --merge
# Merges 24 groups into ~129 unique movements
# Creates ~40 aliases for variant names
```

### Step 3: Verify
```bash
psql nsm_db -c "SELECT COUNT(*) FROM movements;"  # 129
psql nsm_db -c "SELECT COUNT(*) FROM aliases;"    # ~90
```

## Prevention Going Forward

To avoid this in future ETL runs, modify the insertion logic:

```python
# Before inserting a movement, check if variant exists
def get_or_create_movement(name: str, session) -> Movement:
    """Create movement, but merge variants to existing."""
    
    # 1. Check exact match first
    movement = session.query(Movement).filter_by(
        canonical_name=name
    ).first()
    if movement:
        return movement
    
    # 2. Check for similar movement (case-insensitive on normalized name)
    normalized = normalize_name(name)  # lowercase + unaccent
    similar = session.query(Movement).filter(
        func.lower(func.unaccent(Movement.canonical_name)).contains(normalized)
    ).first()
    
    if similar:
        # Add as alias instead of new movement
        alias = Alias(
            movement_id=similar.id,
            alias=name,
            alias_type='variant'
        )
        session.add(alias)
        return similar
    
    # 3. Create new movement
    return Movement(canonical_name=name)
```

## Files
- **database/deduplicate_movements.py** — The deduplication script
- **DEDUPLICATION_GUIDE.md** — Full technical documentation
- **database/DEDUPLICATION_README.md** — Info on source deduplication (separate issue)
