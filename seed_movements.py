#!/usr/bin/env python3
"""
Standalone utility to seed movements and aliases from sources_config.yaml to database

This script seeds both movements and their aliases without running the full ETL pipeline.
"""

import yaml
from sqlalchemy import text
from database.db_loader import DBConnector, Movement
from database.models.alias import Alias

def seed_movements():
    """Seed movements and aliases from YAML to database"""
    
    # Load configuration
    with open('extracting/sources_config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Safely extract movements config with type checking
    if not isinstance(config, dict):
        print("❌ Config is not a dictionary")
        return
    
    keywords = config.get('keywords', {})
    if not isinstance(keywords, dict):
        print("❌ 'keywords' section not found or invalid")
        return
    
    known_movements = keywords.get('known_movements', {})
    if not isinstance(known_movements, dict):
        print("❌ 'known_movements' section not found or invalid")
        return
    
    movements_config = known_movements.get('new_religious_movements', [])
    if not isinstance(movements_config, list):
        print("❌ 'new_religious_movements' not found or invalid")
        return
    
    print(f"📊 Found {len(movements_config)} movements in YAML configuration")
    
    # Connect to database
    db = DBConnector()
    session = db.get_session()
    
    # Fix PostgreSQL sequence
    if 'postgresql' in db.db_uri.lower():
        try:
            max_id_result = session.execute(text("SELECT COALESCE(MAX(id), 0) FROM movements")).fetchone()
            max_id = max_id_result[0] if max_id_result else 0
            new_seq_val = max_id + 1
            session.execute(text(f"SELECT setval('movements_id_seq', {new_seq_val}, false)"))
            session.commit()
            print(f"🔧 Fixed PostgreSQL sequence: Starting from ID {new_seq_val}")
        except Exception as e:
            print(f"⚠️  Could not fix sequence: {e}")
            session.rollback()
    
    # Seed movements
    seeded = 0
    skipped = 0
    
    for movement_name in movements_config:
        if not isinstance(movement_name, str):
            continue
        
        movement_name = movement_name.strip()
        if not movement_name:
            continue
        
        # Check if already exists (canonical_name with diacritics)
        existing = session.query(Movement).filter(Movement.canonical_name == movement_name).first()
        
        if existing:
            skipped += 1
            continue
        
        # Create new movement
        movement = Movement(
            canonical_name=movement_name,  # Name with diacritics (single source of truth)
            category="religious",
            description="Seeded from extracting/sources_config.yaml",
            active_status="unknown"
        )
        
        try:
            session.add(movement)
            session.flush()  # Flush immediately to get ID assigned
            seeded += 1
            print(f"  ✅ Seeded: {movement_name}")
        except Exception as e:
            print(f"  ❌ Failed to seed {movement_name}: {e}")
            session.rollback()
            # Re-establish session
            session = db.get_session()
    
    # Final commit for movements
    try:
        session.commit()
        print()
        print("=" * 70)
        print(f"✅ MOVEMENTS SEEDED")
        print(f"   • Seeded: {seeded} new movements")
        print(f"   • Skipped: {skipped} existing movements")
        print(f"   • Total movements: {seeded + skipped}")
        print("=" * 70)
        print()
    except Exception as e:
        print(f"❌ Failed to commit movements: {e}")
        session.rollback()
        session.close()
        return
    
    # Now seed aliases
    print("🔗 Seeding aliases from movement_aliases configuration...")
    print()
    
    # Safely extract aliases config with type checking
    movement_aliases = keywords.get('movement_aliases', {})
    if not isinstance(movement_aliases, dict):
        print("⚠️  No movement_aliases found in config or invalid format")
        session.close()
        return
    
    aliases_config = movement_aliases
    
    if not aliases_config:
        print("⚠️  No movement_aliases found in config")
        session.close()
        return
    
    print(f"📊 Found {len(aliases_config)} movement alias groups")
    
    aliases_seeded = 0
    aliases_skipped = 0
    aliases_failed = 0
    
    for movement_name, alias_list in aliases_config.items():
        if not isinstance(alias_list, list):
            continue
        
        # Find the movement by canonical name (with diacritics)
        movement = session.query(Movement).filter(Movement.canonical_name == movement_name).first()
        
        if not movement:
            print(f"  ⚠️  Movement not found: {movement_name}")
            aliases_failed += len(alias_list)
            continue
        
        # Seed each alias
        for alias_name in alias_list:
            if not alias_name or not alias_name.strip():
                continue
            
            alias_name = alias_name.strip()
            
            # Check if alias already exists
            existing_alias = session.query(Alias).filter(
                Alias.movement_id == movement.id,
                Alias.alias == alias_name
            ).first()
            
            if existing_alias:
                aliases_skipped += 1
                continue
            
            # Create new alias
            alias = Alias(
                movement_id=movement.id,
                alias=alias_name,
                alias_type="predefined"
            )
            
            try:
                session.add(alias)
                session.flush()  # Flush immediately
                aliases_seeded += 1
                print(f"  ✅ {movement_name} → {alias_name}")
            except Exception as e:
                print(f"  ❌ Failed to seed alias '{alias_name}' for {movement_name}: {e}")
                session.rollback()
                # Re-establish session
                session = db.get_session()
                aliases_failed += 1
    
    # Final commit for aliases
    try:
        session.commit()
        print()
        print("=" * 70)
        print(f"✅ ALIASES SEEDED")
        print(f"   • Seeded: {aliases_seeded} new aliases")
        print(f"   • Skipped: {aliases_skipped} existing aliases")
        print(f"   • Failed: {aliases_failed}")
        print(f"   • Total aliases: {aliases_seeded + aliases_skipped}")
        print("=" * 70)
    except Exception as e:
        print(f"❌ Failed to commit aliases: {e}")
        session.rollback()
    
    session.close()


if __name__ == "__main__":
    seed_movements()
