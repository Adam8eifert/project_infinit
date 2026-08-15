#!/usr/bin/env python3
"""Merge known_movements + movement_aliases into keywords.movements in sources_config.yaml
Writes a merged preview to extracting/sources_config.yaml.merged.yaml and a backup

Usage: python tools/merge_movements_config.py
"""
import sys
from pathlib import Path
import yaml

CONFIG = Path("extracting/sources_config.yaml")
OUT = Path("extracting/sources_config.yaml.merged.yaml")
BACKUP = Path("extracting/sources_config.yaml.bak.yaml")

if not CONFIG.exists():
    print(f"Config not found: {CONFIG}")
    sys.exit(1)

with CONFIG.open("r", encoding="utf-8") as f:
    data = yaml.safe_load(f) or {}

keywords = data.get("keywords", {}) or {}
known = keywords.get("known_movements", {}) or {}
km_list = known.get("new_religious_movements", []) or []
aliases = keywords.get("movement_aliases", {}) or {}
categories = keywords.get("movement_categories", {}) or {}
founded = keywords.get("founded_years", {}) or {}

# Build movements mapping
movements = {}
# Include all canonical names from known list
for name in km_list:
    if name is None:
        continue
    n = str(name)
    movements[n] = {
        "aliases": aliases.get(n) or [],
    }
    if n in categories:
        movements[n]["category"] = categories[n]
    if n in founded:
        movements[n]["founded_year"] = founded[n]

# Also include any keys from movement_aliases that were not in known_movements
for name, a in aliases.items():
    if name not in movements:
        movements[name] = {
            "aliases": a or [],
        }
        if name in categories:
            movements[name]["category"] = categories[name]
        if name in founded:
            movements[name]["founded_year"] = founded[name]

# Preserve keywords.* lists
merged = {
    "keywords": {
        "required": keywords.get("required", []),
        "exclude": keywords.get("exclude", []),
        "exclude_context_patterns": keywords.get("exclude_context_patterns", []),
        "movements": movements,
        "known_persons_aliases": keywords.get("known_persons_aliases", {}),
        "year_patterns": keywords.get("year_patterns", []),
    }
}

# Make a backup and write merged preview
if not BACKUP.exists():
    CONFIG.replace(BACKUP)
    print(f"Backup written to {BACKUP}")
else:
    print(f"Backup already exists: {BACKUP}")

with OUT.open("w", encoding="utf-8") as f:
    yaml.safe_dump(merged, f, allow_unicode=True, sort_keys=False)

print(f"Merged preview written to {OUT}")
print(f"Movements merged: {len(movements)}")

# Basic validation: ensure no movement from km_list lost
missing = [n for n in km_list if n not in movements]
if missing:
    print("WARNING: missing movements after merge:")
    for m in missing:
        print(" - ", m)
else:
    print("All known_movements preserved in merged output.")
