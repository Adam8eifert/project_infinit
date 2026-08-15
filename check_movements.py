#!/usr/bin/env python3
"""Check movements count in database vs YAML"""

from database.db_loader import DBConnector, Movement
from extracting.config_loader import get_config_loader, KeywordsAccessor

# Check config via KeywordsAccessor
loader = get_config_loader()
ka = KeywordsAccessor(loader.config)
yaml_movements = list(ka.movements_map().keys())

print(f"📊 Movements in config: {len(yaml_movements)}")

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
        print(f"  [{m.id}] {m.canonical_name}")
    
    print()
    print("🔧 Solution: The seeding logic will add missing movements on next run.")
else:
    print("✅ All movements from YAML are in database")

session.close()
