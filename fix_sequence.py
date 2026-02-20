#!/usr/bin/env python3
"""
Fix PostgreSQL sequence for movements table
"""

from sqlalchemy import text
from database.db_loader import DBConnector, Movement

db = DBConnector()
session = db.get_session()

# Get current max ID
max_id_result = session.execute(text("SELECT MAX(id) FROM movements")).fetchone()
max_id = max_id_result[0] if max_id_result and max_id_result[0] else 0

print(f"Current max ID in movements table: {max_id}")

# Reset sequence to max_id + 1
new_seq_val = max_id + 1
try:
    session.execute(text(f"ALTER SEQUENCE movements_id_seq RESTART WITH {new_seq_val}"))
    session.commit()
    print(f"✅ Sequence reset to {new_seq_val}")
except Exception as e:
    print(f"❌ Failed to reset sequence: {e}")
    session.rollback()

session.close()
