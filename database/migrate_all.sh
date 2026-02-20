#!/bin/bash
# Complete migration workflow for canonical names architecture
# This script applies both database schema migration and data migration

set -e  # Exit on error

echo "=========================================="
echo "CANONICAL NAMES MIGRATION WORKFLOW"
echo "=========================================="
echo ""
echo "This will:"
echo "1. Add display_name column to movements table (schema)"
echo "2. Migrate existing data to canonical slugs + display names"
echo ""

# Step 1: Database schema migration
echo "Step 1/2: Applying database schema migration..."
echo "------------------------------------------"
python database/run_migration.py 002_add_display_name.sql

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Schema migration failed. Aborting."
    exit 1
fi

echo ""
echo "✅ Schema migration completed"
echo ""

# Step 2: Data migration (dry run first)
echo "Step 2/2: Migrating data to canonical format..."
echo "------------------------------------------"
echo ""
echo "First, let's preview the changes (dry run):"
echo ""

python processing/migrate_canonical_names.py --dry-run

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Data migration preview failed. Aborting."
    exit 1
fi

echo ""
read -p "Do you want to apply these changes? [y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Migration cancelled by user"
    exit 1
fi

echo ""
echo "Applying data migration..."
python processing/migrate_canonical_names.py --live

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Data migration failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ MIGRATION COMPLETED SUCCESSFULLY"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Run the ETL pipeline: python main.py"
echo "  2. New imports will use canonical slugs automatically"
echo ""
