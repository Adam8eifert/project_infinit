#!/usr/bin/env python3
"""
Merge near-duplicate movements and create aliases.

This script identifies movements that are likely the same (based on string similarity)
and merges them by:
1. Keeping the "best" version as the canonical movement
2. Moving other names to the aliases table
3. Consolidating sources across all variants

Usage:
    python database/deduplicate_movements.py [--dry-run] [--merge]
"""

import sys
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Tuple
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DB_URI
from database.db_loader import DBConnector, Movement, Alias, Source
from sqlalchemy import text
import psycopg2
from urllib.parse import urlparse

def get_movements() -> List[Tuple[int, str]]:
    """Get all movements from database."""
    parsed = urlparse(DB_URI.replace('postgresql+psycopg2://', 'postgresql://'))
    conn_params = {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username or 'username',
        'password': parsed.password or '20665166'
    }
    
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    cursor.execute("SELECT id, canonical_name FROM movements ORDER BY id")
    movements = cursor.fetchall()
    cursor.close()
    conn.close()
    return movements

def find_duplicate_groups(movements: List[Tuple[int, str]], 
                         similarity_threshold: float = 0.70) -> List[List[Tuple[int, str]]]:
    """Find groups of near-duplicate movements."""
    groups = []
    processed = set()
    
    for i, (id1, name1) in enumerate(movements):
        if id1 in processed:
            continue
        
        group = [(id1, name1)]
        
        for id2, name2 in movements[i+1:]:
            if id2 in processed:
                continue
            
            # Calculate similarity
            ratio = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
            is_substring = name1.lower() in name2.lower() or name2.lower() in name1.lower()
            
            if ratio > similarity_threshold or (is_substring and len(name1) > 3):
                group.append((id2, name2))
                processed.add(id2)
        
        if len(group) > 1:
            groups.append(sorted(group, key=lambda x: x[1]))  # Sort for consistent output
            processed.add(id1)
    
    return groups

def choose_canonical(group: List[Tuple[int, str]]) -> Tuple[int, str]:
    """
    Choose the best name to use as canonical.
    Preference order:
    1. Longest name (usually most complete)
    2. Name with diacritics (more authoritative)
    3. First ID (oldest)
    """
    # Sort by: length (desc), then check for diacritics, then by ID
    def score(item):
        id, name = item
        has_diacritics = any(ord(c) > 127 for c in name)  # Non-ASCII = diacritics
        return (-len(name), -has_diacritics, id)  # Negative for descending sort
    
    return min(group, key=score)

def print_report(groups: List[List[Tuple[int, str]]]):
    """Print a detailed report of duplicates."""
    print("\n" + "="*70)
    print(f"Near-Duplicate Movements Report ({len(groups)} groups)")
    print("="*70 + "\n")
    
    for idx, group in enumerate(groups, 1):
        canonical_id, canonical_name = choose_canonical(group)
        aliases = [name for id, name in group if id != canonical_id]
        
        print(f"{idx}. CANONICAL: ID {canonical_id} '{canonical_name}'")
        for id, name in group:
            if id != canonical_id:
                similarity = SequenceMatcher(None, canonical_name.lower(), name.lower()).ratio()
                print(f"   → ALIAS: ID {id} '{name}' ({similarity:.0%} similar)")
        print()

def merge_movements(groups: List[List[Tuple[int, str]]], dry_run: bool = True):
    """
    Merge near-duplicate movements.
    
    - Keeps one as canonical
    - Moves other names to aliases table
    - Consolidates sources
    """
    connector = DBConnector(DB_URI)
    session = connector.get_session()
    
    stats = {
        'groups_processed': 0,
        'movements_deleted': 0,
        'aliases_created': 0,
        'sources_reassigned': 0,
    }
    
    try:
        for group in groups:
            canonical_id, canonical_name = choose_canonical(group)
            canonical_movement = session.query(Movement).filter_by(id=canonical_id).first()
            
            if not canonical_movement:
                print(f"⚠ Canonical movement ID {canonical_id} not found, skipping group")
                continue
            
            print(f"\nProcessing group: keeping '{canonical_name}' (ID {canonical_id})")
            
            for id, name in group:
                if id == canonical_id:
                    continue
                
                # Get the movement to be merged
                duplicate = session.query(Movement).filter_by(id=id).first()
                if not duplicate:
                    continue
                
                print(f"  Merging ID {id} '{name}' into ID {canonical_id}")
                
                # 1. Create alias for the duplicate name
                if not dry_run:
                    existing_alias = session.query(Alias).filter(
                        Alias.movement_id == canonical_id,
                        Alias.alias == name
                    ).first()
                    
                    if not existing_alias:
                        alias = Alias(
                            movement_id=canonical_id,
                            alias=name,
                            alias_type='variant',
                            confidence_score=0.95
                        )
                        session.add(alias)
                        stats['aliases_created'] += 1
                
                # 2. Reassign all sources from duplicate to canonical
                sources = session.query(Source).filter_by(movement_id=id).all()
                for source in sources:
                    if not dry_run:
                        source.movement_id = canonical_id
                        stats['sources_reassigned'] += 1
                
                # 3. Delete the duplicate movement
                if not dry_run:
                    session.delete(duplicate)
                    stats['movements_deleted'] += 1
            
            stats['groups_processed'] += 1
    
    finally:
        if not dry_run:
            session.commit()
        session.close()
    
    return stats

def main():
    parser = argparse.ArgumentParser(
        description='Deduplicate movements by merging near-duplicates'
    )
    parser.add_argument('--merge', action='store_true', 
                       help='Actually perform the merge (required to make changes)')
    args = parser.parse_args()
    
    print("\n🔍 Detecting near-duplicate movements...")
    movements = get_movements()
    print(f"✓ Loaded {len(movements)} movements")
    
    print("\n📊 Finding duplicate groups...")
    groups = find_duplicate_groups(movements)
    print(f"✓ Found {len(groups)} groups of near-duplicates")
    
    print_report(groups)
    
    if args.merge:
        print("\n" + "="*70)
        print("MERGING DUPLICATES...")
        print("="*70)
        stats = merge_movements(groups, dry_run=False)
        print(f"\n✓ Merge complete!")
        print(f"  - Groups processed: {stats['groups_processed']}")
        print(f"  - Movements deleted: {stats['movements_deleted']}")
        print(f"  - Aliases created: {stats['aliases_created']}")
        print(f"  - Sources reassigned: {stats['sources_reassigned']}")
    else:
        print("\n" + "="*70)
        print("DRY RUN - No changes made.")
        print("Run with --merge to actually perform the deduplication.")
        print("="*70)

if __name__ == '__main__':
    main()
