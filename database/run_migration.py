#!/usr/bin/env python3
"""
Apply database migrations

Supports both PostgreSQL and SQLite through SQLAlchemy.

Usage:
    python database/run_migration.py 002_add_display_name.sql
    python database/run_migration.py 002_add_display_name.sql --auto  # skip confirmation
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from config import DB_URI

def run_migration(migration_file: str, auto_confirm: bool = False):
    """Apply a migration SQL file to the database"""
    
    migration_path = Path("database/migrations") / migration_file
    if not migration_path.exists():
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    print(f"🔗 Database: {DB_URI}")
    print(f"📄 Migration: {migration_path}")
    print()
    
    # Read migration SQL
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Parse SQL statements (split by semicolon, filter comments)
    statements = []
    for statement in sql_content.split(';'):
        statement = statement.strip()
        # Remove comments and empty lines
        lines = [line for line in statement.split('\n') 
                 if line.strip() and not line.strip().startswith('--')]
        if lines:
            statements.append('\n'.join(lines))
    
    if not statements:
        print("❌ No SQL statements found in migration file")
        return False
    
    print("SQL to execute:")
    print("-" * 70)
    for i, stmt in enumerate(statements, 1):
        print(f"-- Statement {i}:")
        print(stmt)
        print()
    print("-" * 70)
    print()
    
    # Confirm
    if not auto_confirm:
        response = input("Apply this migration? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Migration cancelled")
            return False
    
    # Apply migration using SQLAlchemy
    try:
        engine = create_engine(DB_URI)
        
        with engine.connect() as conn:
            # Execute each statement
            for i, statement in enumerate(statements, 1):
                try:
                    print(f"Executing statement {i}...", end=' ')
                    conn.execute(text(statement))
                    conn.commit()
                    print("✓")
                except Exception as e:
                    # Some statements might fail if already applied (e.g., column exists)
                    error_str = str(e).lower()
                    if 'already exists' in error_str or 'duplicate column' in error_str:
                        print(f"⚠️  Already applied (skipped)")
                    else:
                        print(f"❌ Failed: {e}")
                        conn.rollback()
                        raise
        
        print()
        print("✅ Migration applied successfully!")
        return True
        
    except Exception as e:
        print()
        print(f"❌ Migration failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python database/run_migration.py <migration_file> [--auto]")
        print("Example: python database/run_migration.py 002_add_display_name.sql")
        print("         python database/run_migration.py 002_add_display_name.sql --auto")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    auto_confirm = '--auto' in sys.argv
    
    success = run_migration(migration_file, auto_confirm=auto_confirm)
    sys.exit(0 if success else 1)
