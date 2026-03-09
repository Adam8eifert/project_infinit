# 📁 processing/relevance_report.py
# Suspicious relevance report for manual QA of imported articles

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_loader import Article, DBConnector
from extracting.keywords import contains_relevant_keywords, is_excluded_content, match_movement_from_text


def _source_type_to_text(source_type_value) -> str:
    if source_type_value is None:
        return "unknown"
    return str(getattr(source_type_value, "value", source_type_value)).lower()


def collect_suspicious_articles(db: DBConnector, limit: int = 20) -> List[Dict]:
    """Return top suspicious articles for manual relevance review."""
    session = db.get_session()
    try:
        suspicious: List[Dict] = []
        for article in session.query(Article).all():
            combined_text = f"{article.title or ''} {article.content or ''}".strip()
            movement_names = [movement.name for movement in article.movements]
            movement_count = len(movement_names)

            reasons: List[str] = []
            score = 0

            if not combined_text or len(combined_text) < 80:
                score += 2
                reasons.append("short_or_empty_text")

            excluded = is_excluded_content(combined_text) if combined_text else True
            if excluded:
                score += 4
                reasons.append("excluded_context")

            has_keywords = contains_relevant_keywords(combined_text, min_hits=2) if combined_text else False
            if not has_keywords:
                score += 3
                reasons.append("no_nnh_keywords")

            strict_movement_id = match_movement_from_text(combined_text, min_score=90) if combined_text else None
            if movement_count == 0:
                score += 3
                reasons.append("no_movement_link")
            elif strict_movement_id is None:
                score += 2
                reasons.append("movement_link_without_strict_match")
            else:
                if not any(movement.id == strict_movement_id for movement in article.movements):
                    score += 2
                    reasons.append("movement_link_mismatch")

            if score < 4:
                continue

            suspicious.append(
                {
                    "id": int(article.id),
                    "title": (article.title or "")[:180],
                    "source_name": article.source_name or "Unknown",
                    "source_type": _source_type_to_text(article.source_type),
                    "movements": movement_names,
                    "reasons": reasons,
                    "score": score,
                }
            )

        suspicious.sort(key=lambda row: (-row["score"], row["id"]))
        return suspicious[:limit]
    finally:
        session.close()


def print_suspicious_articles_report(db: DBConnector, limit: int = 20) -> None:
    """Print top suspicious articles for quick manual review."""
    items = collect_suspicious_articles(db, limit=limit)

    print(f"\n🔎 Suspicious relevance report (top {limit})")
    if not items:
        print("   • No suspicious articles found")
        return

    for item in items:
        movement_text = ", ".join(item["movements"]) if item["movements"] else "None"
        reasons_text = ", ".join(item["reasons"]) if item["reasons"] else "none"
        print(f"   [{item['score']:02d}] #{item['id']} {item['title']}")
        print(
            "      "
            f"source={item['source_name']} ({item['source_type']}) | "
            f"movements={movement_text} | reasons={reasons_text}"
        )


def export_suspicious_articles_csv(
    db: DBConnector,
    output_csv: str = "export/csv/suspicious_articles_report.csv",
    limit: int = 200,
) -> int:
    """Export suspicious relevance rows into CSV and return exported row count."""
    items = collect_suspicious_articles(db, limit=max(1, int(limit)))

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "id",
                "title",
                "source_name",
                "source_type",
                "movements",
                "reasons",
                "score",
            ],
        )
        writer.writeheader()

        for item in items:
            writer.writerow(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "source_name": item["source_name"],
                    "source_type": item["source_type"],
                    "movements": "; ".join(item["movements"]),
                    "reasons": "; ".join(item["reasons"]),
                    "score": item["score"],
                }
            )

    return len(items)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print suspicious relevance report for articles")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of rows to print")
    parser.add_argument(
        "--csv-out",
        type=str,
        default="export/csv/suspicious_articles_report.csv",
        help="CSV output path",
    )
    parser.add_argument("--csv-limit", type=int, default=200, help="Maximum number of CSV rows")
    args = parser.parse_args()

    db = DBConnector()
    print_suspicious_articles_report(db, limit=max(1, int(args.limit)))
    exported = export_suspicious_articles_csv(
        db,
        output_csv=args.csv_out,
        limit=max(1, int(args.csv_limit)),
    )
    print(f"🗂️ Suspicious relevance CSV exported: {exported} rows -> {args.csv_out}")


if __name__ == "__main__":
    main()
