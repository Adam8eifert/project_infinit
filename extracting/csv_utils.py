"""
Utilities for consistent CSV exports across spiders.
- get_output_csv_for_source(source_key)
- ensure_export_dir_exists()
- ensure_csv_header(path)
- append_row(path, row_dict)

CSV columns standardized to: source_name, source_type, title, url, text, scraped_at, author, published_at, categories
"""
from pathlib import Path
import csv
import json
from typing import Dict
from .config_loader import get_config_loader

CSV_COLUMNS = [
    "source_name",
    "source_type",
    "title",
    "url",
    "text",
    "scraped_at",
    "author",
    "published_at",
    "categories",
]

EXPORT_DIR = Path("export/csv")


def ensure_export_dir_exists() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def get_output_csv_for_source(source_key: str) -> Path:
    """Return the configured output CSV path for a source, or a sensible default.
    Ensures the export directory exists.
    """
    ensure_export_dir_exists()
    try:
        loader = get_config_loader()
        src = loader.get_source(source_key)
    except FileNotFoundError:
        # No YAML config in this environment - fall back to default
        return EXPORT_DIR / f"{source_key}_raw.csv"
    except Exception:
        return EXPORT_DIR / f"{source_key}_raw.csv"

    if not src:
        return EXPORT_DIR / f"{source_key}_raw.csv"

    path = src.get("output_csv")
    if path:
        return Path(path)
    return EXPORT_DIR / f"{source_key}_raw.csv"


def ensure_csv_header(path: Path) -> None:
    """Ensure CSV exists and has the standardized header. Does nothing if header present."""
    path = Path(path)
    ensure_export_dir_exists()
    if not path.exists():
        with path.open("w", encoding="utf8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
            writer.writeheader()


def append_row(path: Path, row: Dict) -> None:
    """Append a row to CSV, ensuring header and serializing complex fields."""
    path = Path(path)
    ensure_csv_header(path)

    # Normalize row to expected columns
    out = {}
    for col in CSV_COLUMNS:
        val = row.get(col, "")
        # categories can be list -> serialize as JSON
        if col == "categories" and isinstance(val, (list, tuple)):
            val = json.dumps(val, ensure_ascii=False)
        out[col] = val

    with path.open("a", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writerow(out)
