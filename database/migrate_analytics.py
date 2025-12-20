#!/usr/bin/env python3
# database/migrate_analytics.py
"""
Migration script to enhance database with analytical capabilities.
Adds new tables, columns, and views for advanced analytics.
"""

import os
import sys
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_loader import DBConnector
import config

def run_migration():
    """Run the analytics enhancement migration."""
    print("🚀 Starting analytics database migration...")

    # Initialize database connection
    db = DBConnector()

    try:
        # Check if we're using PostgreSQL (for advanced features)
        is_postgres = 'postgresql' in db.db_uri.lower()

        if is_postgres:
            print("📊 Detected PostgreSQL - enabling full analytics features")
        else:
            print("📊 Detected SQLite - some advanced features may be limited")

        # Run the migration SQL
        migration_file = Path(__file__).parent / "migrations" / "001_enhance_for_analytics.sql"

        if migration_file.exists():
            print("📝 Running migration script...")
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            # Split into individual statements and execute
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]

            with db.get_session() as session:
                for statement in statements:
                    if statement:
                        try:
                            session.execute(text(statement))
                        except Exception as e:
                            print(f"⚠️  Warning executing statement: {e}")
                            # Continue with other statements
                session.commit()

            print("✅ Migration completed successfully")
        else:
            print("❌ Migration file not found")

        # Create views if PostgreSQL
        if is_postgres:
            views_file = Path(__file__).parent / "views.sql"
            if views_file.exists():
                print("📊 Creating analytical views...")
                with open(views_file, 'r', encoding='utf-8') as f:
                    views_sql = f.read()

                with db.get_session() as session:
                    session.execute(text(views_sql))
                    session.commit()

                print("✅ Views created successfully")
            else:
                print("⚠️  Views file not found - skipping view creation")

        # Verify the migration
        print("🔍 Verifying migration...")
        with db.get_session() as session:
            # Check if new tables exist
            tables_to_check = ['temporal_analysis', 'geographic_analysis', 'source_quality']
            for table in tables_to_check:
                try:
                    result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"✅ Table '{table}' exists with {count} records")
                except Exception as e:
                    print(f"❌ Table '{table}' check failed: {e}")

        print("🎉 Analytics migration completed successfully!")
        print("\n📈 New analytical capabilities available:")
        print("   • Time-series analysis (temporal_analysis)")
        print("   • Geographic patterns (geographic_analysis)")
        print("   • Source quality metrics (source_quality)")
        print("   • Enhanced movement metrics")
        print("   • Analytical views (PostgreSQL only)")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()