#!/usr/bin/env python3
"""
Migration script: Update existing movements to use canonical slugs + display names

This script:
1. Loads new YAML format with canonical slugs and display names
2. Updates existing movements in database:
   - Sets canonical_name to slug (e.g., "hnuti-hare-krsna")
   - Sets display_name to official name with diacritics (e.g., "Hnutí Hare Kršna")
3. Prevents duplicates by checking canonical_name before inserting

Usage:
    python processing/migrate_canonical_names.py --dry-run  # Preview changes
    python processing/migrate_canonical_names.py --live      # Apply changes
"""

import sys
import os
import yaml
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_loader import DBConnector, Movement
from database.utils import slugify

def load_movements_from_yaml() -> Dict[str, str]:
    """
    Load canonical -> display mapping from sources_config.yaml
    
    Returns:
        Dict mapping canonical_slug -> display_name
    """
    config_path = Path("extracting/sources_config.yaml")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            known = config.get('keywords', {}).get('known_movements', {}).get('new_religious_movements', [])
            
            mapping = {}
            for entry in known:
                if isinstance(entry, dict):
                    canonical = entry.get('canonical', '').strip()
                    display = entry.get('display', '').strip()
                    if canonical and display:
                        mapping[canonical] = display
            
            return mapping
    except Exception as e:
        print(f"❌ Failed to load YAML: {e}")
        return {}


def migrate_movements(dry_run: bool = True):
    """
    Migrate existing movements to canonical slug format
    
    Args:
        dry_run: If True, only preview changes without modifying database
    """
    print("=" * 70)
    print("MOVEMENT CANONICAL NAME MIGRATION")
    print("=" * 70)
    print(f"Mode: {'DRY RUN (preview only)' if dry_run else 'LIVE (will modify database)'}")
    print()
    
    # Load canonical -> display mapping from YAML
    yaml_movements = load_movements_from_yaml()
    if not yaml_movements:
        print("❌ No movements found in YAML config")
        return
    
    print(f"✓ Loaded {len(yaml_movements)} movements from sources_config.yaml")
    print()
    
    # Connect to database
    db = DBConnector()
    session = db.get_session()
    
    # Get all existing movements
    movements = session.query(Movement).all()
    print(f"✓ Found {len(movements)} existing movements in database")
    print()
    
    # Statistics
    stats = {
        'matched': 0,
        'updated': 0,
        'skipped_already_canonical': 0,
        'skipped_no_match': 0,
        'errors': 0
    }
    
    print("Processing movements:")
    print("-" * 70)
    
    for movement in movements:
        canonical_current = movement.canonical_name
        display_current = movement.display_name
        
        if not canonical_current:
            continue
        
        # Check if canonical_name is already a slug (no spaces, no uppercase, no diacritics)
        is_already_slug = (
            '-' in canonical_current and 
            ' ' not in canonical_current and 
            canonical_current.islower()
        )
        
        if is_already_slug:
            # Already migrated, just update display_name if missing
            if not display_current:
                # Try to find display name in YAML
                expected_display = yaml_movements.get(canonical_current)
                if expected_display:
                    print(f"  [{movement.id}] {canonical_current}")
                    print(f"          Already slug, adding display_name: {expected_display}")
                    if not dry_run:
                        movement.display_name = expected_display
                    stats['updated'] += 1
                else:
                    stats['skipped_already_canonical'] += 1
            else:
                stats['skipped_already_canonical'] += 1
            continue
        
        # Try to find matching canonical slug by:
        # 1. Converting current canonical_name to slug and checking YAML
        # 2. Finding display name that matches current canonical_name
        
        candidate_slug = slugify(canonical_current)
        expected_display = None
        final_canonical = None
        
        # Strategy 1: Check if slugified version exists in YAML
        if candidate_slug in yaml_movements:
            final_canonical = candidate_slug
            expected_display = yaml_movements[candidate_slug]
            stats['matched'] += 1
        else:
            # Strategy 2: Check if current canonical_name matches any display name in YAML
            for canonical_slug, display_name in yaml_movements.items():
                if canonical_current.lower() == display_name.lower():
                    final_canonical = canonical_slug
                    expected_display = display_name
                    stats['matched'] += 1
                    break
        
        if final_canonical and expected_display:
            print(f"  [{movement.id}] {canonical_current}")
            print(f"          → canonical: {final_canonical}")
            print(f"          → display: {expected_display}")
            
            if not dry_run:
                try:
                    movement.canonical_name = final_canonical
                    movement.display_name = expected_display
                    stats['updated'] += 1
                except Exception as e:
                    print(f"          ❌ Error: {e}")
                    stats['errors'] += 1
            else:
                stats['updated'] += 1
        else:
            print(f"  [{movement.id}] {canonical_current} → ⚠️  No match in YAML")
            stats['skipped_no_match'] += 1
    
    # Commit changes if not dry run
    if not dry_run:
        try:
            session.commit()
            print()
            print("✓ Changes committed to database")
        except Exception as e:
            session.rollback()
            print()
            print(f"❌ Failed to commit changes: {e}")
            stats['errors'] += 1
    
    session.close()
    
    # Print summary
    print()
    print("=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Total movements:           {len(movements)}")
    print(f"Matched and updated:       {stats['updated']}")
    print(f"Already canonical:         {stats['skipped_already_canonical']}")
    print(f"No match in YAML:          {stats['skipped_no_match']}")
    print(f"Errors:                    {stats['errors']}")
    print("=" * 70)
    
    if dry_run:
        print()
        print("ℹ️  This was a DRY RUN - no changes were made to the database")
        print("   Run with --live to apply changes")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate movements to canonical slug format")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Apply changes to database (default is dry-run)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying database (default)"
    )
    
    args = parser.parse_args()
    
    # Default to dry-run if neither specified
    dry_run = not args.live or args.dry_run
    
    migrate_movements(dry_run=dry_run)
