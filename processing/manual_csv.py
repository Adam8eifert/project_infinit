"""Helper to process manual CSV uploads.

Usage:
  from processing.manual_csv import process_manual_csvs
  process_manual_csvs(manual_dir='csv_manual', target_dir='export/csv', do_import=True)

Behavior:
- Moves CSV files from `manual_dir` into `target_dir` with a `_raw.csv` suffix (idempotent rename if collisions).
- Optionally triggers immediate import via CSVtoDatabaseLoader.load_csv_to_sources.
- Returns a list of processed (target) file paths.
"""

from pathlib import Path
import shutil
import logging
from datetime import datetime
from typing import List

import pandas as pd

from processing.import_csv_to_db import CSVtoDatabaseLoader

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ["source_name", "source_type", "title", "url", "text", "scraped_at"]


def _normalize_csv_file(path: Path) -> bool:
    """Normalize a CSV file so it contains the required columns.

    - Maps common aliases to required column names (e.g., 'content' -> 'text').
    - Fills missing required columns with sensible defaults.
    - Writes back only the required columns in canonical order.

    Returns True if normalization succeeded, False otherwise.
    """
    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.error(f"Failed to read CSV for normalization {path}: {e}")
        return False

    # Lowercase column names for matching
    col_map = {c: c for c in df.columns}
    lowered = {c.lower(): c for c in df.columns}

    # Alias mapping
    aliases = {
        'content': 'text',
        'body': 'text',
        'description': 'text',
        'text_content': 'text',
        'date_published': 'scraped_at',
        'pubdate': 'scraped_at',
        'pub_date': 'scraped_at',
        'date': 'scraped_at',
        'source': 'source_name',
        'source_title': 'title',
        'headline': 'title',
        'link': 'url',
        'href': 'url'
    }

    # Rename any aliases found
    renames = {}
    for low, orig in lowered.items():
        if low in aliases and aliases[low] not in df.columns:
            renames[orig] = aliases[low]
    if renames:
        df = df.rename(columns=renames)
        logger.info(f"Applied column renames for normalization: {renames}")

    # Ensure required columns exist, fill defaults if missing
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            if col == 'source_name':
                df[col] = 'manual_upload'
            elif col == 'source_type':
                df[col] = 'manual'
            elif col == 'scraped_at':
                df[col] = datetime.utcnow().isoformat()
            else:
                df[col] = ''
            logger.info(f"Added missing column '{col}' with default values for {path}")

    # Keep only required columns in canonical order
    try:
        df = df[REQUIRED_COLUMNS]
        df.to_csv(path, index=False)
        return True
    except Exception as e:
        logger.error(f"Failed to write normalized CSV {path}: {e}")
        return False


def process_manual_csvs(manual_dir: str = "csv_manual", target_dir: str = "export/csv", do_import: bool = True) -> List[Path]:
    """Move CSVs from manual directory into pipeline export folder and optionally import them.

    - Renames file to <original_stem>_raw.csv unless that filename already exists, in which case
      appends a timestamp suffix to avoid overwrites.
    - Normalizes CSV to contain required columns before import.
    - If do_import is True, calls CSVtoDatabaseLoader().load_csv_to_sources on each moved file.
    """
    manual = Path(manual_dir)
    target = Path(target_dir)
    processed = []

    if not manual.exists():
        logger.info(f"Manual CSV directory does not exist, creating: {manual}")
        manual.mkdir(parents=True, exist_ok=True)
        return processed

    if not target.exists():
        target.mkdir(parents=True, exist_ok=True)

    files = list(manual.glob("*.csv"))
    if not files:
        logger.info(f"No manual CSV files found in {manual}")
        return processed

    loader = CSVtoDatabaseLoader() if do_import else None

    for f in files:
        stem = f.stem
        dest_name = f"{stem}_raw.csv"
        dest = target / dest_name
        # If target exists, append timestamp
        if dest.exists():
            ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            dest = target / f"{stem}_raw_{ts}.csv"

        try:
            shutil.move(str(f), str(dest))
            logger.info(f"Moved manual CSV {f} -> {dest}")
            processed.append(dest)

            # Normalize CSV to required columns
            ok = _normalize_csv_file(dest)
            if not ok:
                logger.warning(f"Normalization failed for {dest}; skipping import")
                continue

            if loader:
                try:
                    loader.load_csv_to_sources(dest)
                    logger.info(f"Imported manual CSV: {dest}")
                except Exception as e:
                    logger.error(f"Error importing manual CSV {dest}: {e}")
        except Exception as e:
            logger.error(f"Failed to move manual CSV {f}: {e}")

    return processed
