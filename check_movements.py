#!/usr/bin/env python3
"""Check movements count in database vs YAML"""

import yaml
from database.db_loader import DBConnector, Movement

# Check YAML
with open('extracting/sources_config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)
    yaml_movements = config.get('keywords', {}).get('known_movements', {}).get('new_religious_movements', [])

print(f"📊 Movements in YAML config: {len(yaml_movements)}")

# Check database
db = DBConnector()
session = db.get_session()
db_movements = session.query(Movement).all()

print(f"📊 Movements in database: {len(db_movements)}")
print()

if len(db_movements) < len(yaml_movements):
    print(f"⚠️  PROBLEM: Missing {len(yaml_movements) - len(db_movements)} movements in database!")
    print()
    print("Database movements:")
    for m in db_movements:
        print(f"  [{m.id}] {m.canonical_name} → {m.display_name}")
    
    print()
    print("🔧 Solution: The seeding logic will add missing movements on next run.")
else:
    print("✅ All movements from YAML are in database")

session.close()
