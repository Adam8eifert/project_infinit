#!/usr/bin/env python3
# database/deduplicate_sources.py
"""
Script for managing duplicate sources in the database.
Provides commands for:
- Updating content hashes
- Finding and removing duplicates
- Reporting duplicate statistics
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_loader import DBConnector
from database.models import Source

def update_hashes(args):
    """Update content hashes for sources that don't have them."""
    print("🔄 Updating content hashes...")

    db = DBConnector()
    stats = db.update_content_hashes(batch_size=args.batch_size)

    print("✅ Content hash update completed:")
    print(f"   • Processed: {stats['processed']}")
    print(f"   • Updated: {stats['updated']}")
    print(f"   • Errors: {stats['errors']}")

def find_duplicates(args):
    """Find and report duplicate sources."""
    print("🔍 Scanning for duplicate sources...")

    db = DBConnector()
    stats = db.remove_duplicates(dry_run=True)  # Dry run to just count

    print("📊 Duplicate scan results:")
    print(f"   • Sources scanned: {stats['scanned']}")
    print(f"   • Duplicates found: {stats['duplicates_found']}")

    if stats['duplicates_found'] > 0:
        print("\n⚠️  Run with --remove to actually delete duplicates")
        print("   This was a dry run - no changes made")
    else:
        print("🎉 No duplicates found!")

def remove_duplicates(args):
    """Remove duplicate sources from database."""
    print("🗑️  Removing duplicate sources...")
    print("⚠️  This operation cannot be undone!")

    if not args.force:
        confirm = input("Are you sure you want to remove duplicates? (type 'yes' to confirm): ")
        if confirm.lower() != 'yes':
            print("❌ Operation cancelled")
            return

    db = DBConnector()
    stats = db.remove_duplicates(dry_run=False)

    print("✅ Duplicate removal completed:")
    print(f"   • Sources scanned: {stats['scanned']}")
    print(f"   • Duplicates found: {stats['duplicates_found']}")
    print(f"   • Duplicates removed: {stats['duplicates_removed']}")
    print(f"   • Errors: {stats['errors']}")

def show_stats(args):
    """Show database statistics related to duplicates."""
    print("📈 Database duplicate statistics...")

    db = DBConnector()
    session = db.get_session()

    try:
        # Count sources with/without hashes
        total_sources = session.query(Source).count()
        with_hashes = session.query(Source).filter(
            Source.content_hash.isnot(None)
        ).count()
        without_hashes = total_sources - with_hashes

        # Count unique content hashes
        unique_hashes = session.query(Source.content_hash).distinct().count()

        # Find hash groups with duplicates
        from sqlalchemy import func
        hash_counts = session.query(
            Source.content_hash,
            func.count(Source.id).label('count')
        ).group_by(Source.content_hash).all()

        duplicate_groups = [h for h in hash_counts if h.count > 1]
        total_duplicates = sum(h.count - 1 for h in duplicate_groups)

        print("📊 Database Statistics:")
        print(f"   • Total sources: {total_sources}")
        print(f"   • Sources with content hash: {with_hashes} ({with_hashes/total_sources*100:.1f}%)")
        print(f"   • Sources without content hash: {without_hashes}")
        print(f"   • Unique content hashes: {unique_hashes}")
        print(f"   • Duplicate groups: {len(duplicate_groups)}")
        print(f"   • Total duplicate sources: {total_duplicates}")

        if duplicate_groups:
            print("\n🔍 Largest duplicate groups:")
            sorted_groups = sorted(duplicate_groups, key=lambda x: x.count, reverse=True)[:5]
            for i, group in enumerate(sorted_groups, 1):
                print(f"   {i}. Hash group with {group.count} sources")

    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description="Manage duplicate sources in Project Infinit database")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Update hashes command
    update_parser = subparsers.add_parser('update-hashes', help='Update content hashes for sources')
    update_parser.add_argument('--batch-size', type=int, default=1000,
                              help='Batch size for processing (default: 1000)')
    update_parser.set_defaults(func=update_hashes)

    # Find duplicates command
    find_parser = subparsers.add_parser('find', help='Find duplicate sources (dry run)')
    find_parser.set_defaults(func=find_duplicates)

    # Remove duplicates command
    remove_parser = subparsers.add_parser('remove', help='Remove duplicate sources')
    remove_parser.add_argument('--force', action='store_true',
                              help='Skip confirmation prompt')
    remove_parser.set_defaults(func=remove_duplicates)

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show duplicate statistics')
    stats_parser.set_defaults(func=show_stats)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        args.func(args)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()