"""
# 📁 processing/rematch_movements.py
# Migrator for re-matching existing sources to correct movements
# Useful after implementing movement matching functionality

Usage:
    python processing/rematch_movements.py [--dry-run] [--batch-size 100]
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_loader import DBConnector, Source, Movement
from extracting.keywords import match_movement_from_text, get_movement_name_by_id
import logging
from typing import Dict
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rematch_all_sources(dry_run: bool = True, batch_size: int = 100) -> Dict[str, int]:
    """
    Re-match all sources in database to correct movements.
    
    Args:
        dry_run: If True, only show what would be changed without saving
        batch_size: Number of sources to process in each batch
    
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total': 0,
        'matched': 0,
        'unchanged': 0,
        'failed': 0,
        'movement_distribution': {}
    }
    
    db = DBConnector()
    session = db.get_session()
    
    try:
        # Get total count
        total_sources = session.query(Source).count()
        stats['total'] = total_sources
        
        logger.info(f"🔄 Starting re-matching for {total_sources} sources...")
        logger.info(f"{'🧪 DRY RUN MODE - No changes will be saved' if dry_run else '✅ LIVE MODE - Changes will be saved'}")
        
        # Process in batches
        offset = 0
        while offset < total_sources:
            sources = session.query(Source).offset(offset).limit(batch_size).all()
            
            for source in sources:
                try:
                    # Combine title and content for matching
                    title = source.content_excerpt or ""
                    text = source.content_full or ""
                    combined = f"{title} {text}"
                    
                    if not combined.strip():
                        stats['failed'] += 1
                        continue
                    
                    # Try to match movement
                    new_movement_id = match_movement_from_text(combined)
                    
                    if new_movement_id is None:
                        # No match found, keep as is
                        stats['unchanged'] += 1
                        continue
                    
                    old_movement_id = source.movement_id
                    
                    if new_movement_id != old_movement_id:
                    old_id_int = int(old_movement_id) if old_movement_id else 0  # type: ignore[arg-type]
                    old_name = get_movement_name_by_id(old_id_int) if old_id_int else "None"
                    new_name = get_movement_name_by_id(new_movement_id)
                    
                    logger.debug(f"Re-matching: '{title[:50]}...' | {old_name} → {new_name}")
                    
                    if not dry_run:
                        source.movement_id = new_movement_id  # type: ignore[assignment]
                        stats['matched'] += 1
                    else:
                        stats['unchanged'] += 1
                    
                    # Track movement distribution
                    movement_name = get_movement_name_by_id(new_movement_id) or "Unknown"
                    stats['movement_distribution'][movement_name] = \
                        stats['movement_distribution'].get(movement_name, 0) + 1
                        
                except Exception as e:
                    logger.error(f"Error processing source {source.id}: {e}")
                    stats['failed'] += 1
            
            offset += batch_size
            
            # Commit batch if not dry run
            if not dry_run:
                session.commit()
                logger.info(f"✅ Committed batch {offset}/{total_sources}")
            else:
                logger.info(f"🔍 Processed {offset}/{total_sources} (dry run)")
        
        # Final commit
        if not dry_run:
            session.commit()
        
        # Print statistics
        logger.info("\n" + "="*60)
        logger.info("📊 Re-matching Statistics:")
        logger.info("="*60)
        logger.info(f"Total sources:       {stats['total']}")
        logger.info(f"Re-matched:          {stats['matched']}")
        logger.info(f"Unchanged:           {stats['unchanged']}")
        logger.info(f"Failed:              {stats['failed']}")
        logger.info("\n📌 Movement Distribution (Top 10):")
        
        sorted_movements = sorted(
            stats['movement_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for movement_name, count in sorted_movements[:10]:
            logger.info(f"  {movement_name}: {count}")
        
        if len(sorted_movements) > 10:
            logger.info(f"  ... and {len(sorted_movements) - 10} more movements")
        
        logger.info("="*60)
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error during re-matching: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def rematch_sources_by_movement(old_movement_id: int, dry_run: bool = True) -> Dict[str, int]:
    """
    Re-match only sources currently assigned to a specific movement.
    Useful for fixing sources incorrectly assigned to movement_id=1.
    
    Args:
        old_movement_id: ID of movement to re-match sources from
        dry_run: If True, only show what would be changed
    
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total': 0,
        'matched': 0,
        'unchanged': 0,
        'failed': 0
    }
    
    db = DBConnector()
    session = db.get_session()
    
    try:
        # Get sources with old movement
        sources = session.query(Source).filter(Source.movement_id == old_movement_id).all()
        stats['total'] = len(sources)
        
        old_movement_name = get_movement_name_by_id(old_movement_id)
        logger.info(f"🔄 Re-matching {len(sources)} sources from '{old_movement_name}'...")
        
        for source in sources:
            try:
                title = source.content_excerpt or ""
                text = source.content_full or ""
                combined = f"{title} {text}"
                
                if not combined.strip():
                    stats['failed'] += 1
                    continue
                
                new_movement_id = match_movement_from_text(combined)
                
                if new_movement_id and new_movement_id != old_movement_id:
                    new_name = get_movement_name_by_id(new_movement_id)
                    logger.info(f"✓ '{title[:50]}...' → {new_name}")
                    
                    if not dry_run:
                        source.movement_id = new_movement_id  # type: ignore[assignment]
                    
                    stats['matched'] += 1
                else:
                    stats['unchanged'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing source {source.id}: {e}")
                stats['failed'] += 1
        
        if not dry_run:
            session.commit()
        
        logger.info("\n📊 Results:")
        logger.info(f"  Total:     {stats['total']}")
        logger.info(f"  Re-matched: {stats['matched']}")
        logger.info(f"  Unchanged: {stats['unchanged']}")
        logger.info(f"  Failed:    {stats['failed']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Re-match sources to correct movements")
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Run without making changes (default: True)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Run in live mode and save changes to database'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of sources to process per batch (default: 100)'
    )
    parser.add_argument(
        '--movement-id',
        type=int,
        help='Only re-match sources from specific movement ID (e.g., 1 for default)'
    )
    
    args = parser.parse_args()
    
    # Determine dry_run mode
    dry_run = not args.live
    
    try:
        if args.movement_id:
            # Re-match specific movement
            rematch_sources_by_movement(args.movement_id, dry_run=dry_run)
        else:
            # Re-match all sources
            rematch_all_sources(dry_run=dry_run, batch_size=args.batch_size)
            
    except KeyboardInterrupt:
        logger.info("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
