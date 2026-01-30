from pathlib import Path
import csv


def test_rss_and_web_share_same_csv(tmp_path, monkeypatch):
    """Simulate RSS and web spiders writing to the same CSV and assert both rows are present."""
    shared = tmp_path / 'combined.csv'

    # Monkeypatch csv_utils.get_output_csv_for_source so both spiders point to the same file
    import extracting.csv_utils as cu
    monkeypatch.setattr(cu, 'get_output_csv_for_source', lambda key: shared)

    # Import spiders (they will attempt to ensure CSV header in __init__)
    from extracting.medium_seznam_spider import MediumSeznamSpider
    from extracting.google_spider import GoogleNewsRSSSpider

    s1 = MediumSeznamSpider()
    s2 = GoogleNewsRSSSpider()

    # Verify that both spiders configured FEEDS to the same shared path
    feed1 = next(iter(s1.custom_settings.get('FEEDS', {}).keys()))
    feed2 = next(iter(s2.custom_settings.get('FEEDS', {}).keys()))

    assert str(shared) in str(feed1)
    assert str(shared) in str(feed2)

    # Write one row as each spider would do and validate the CSV contains both
    from extracting.csv_utils import append_row

    append_row(shared, {
        'source_name': 'medium.seznam', 'source_type': 'web', 'title': 'Medium Article',
        'url': 'http://media.example/1', 'text': 'Some content', 'scraped_at': '2020-01-01T00:00:00Z',
        'author': 'Author A', 'published_at': '', 'categories': []
    })

    append_row(shared, {
        'source_name': 'Google News', 'source_type': 'news_aggregator', 'title': 'Google Item',
        'url': 'http://news.example/2', 'text': 'Other content', 'scraped_at': '2020-01-02T00:00:00Z',
        'author': 'Author B', 'published_at': '', 'categories': []
    })

    # Read and assert
    assert shared.exists(), "Shared CSV must exist"

    with shared.open(encoding='utf8') as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    assert len(rows) == 2

    titles = {r['title'] for r in rows}
    assert 'Medium Article' in titles
    assert 'Google Item' in titles

    # Validate categories field is JSON and can be parsed back into a list
    import json
    for r in rows:
        assert 'categories' in r
        cat_raw = r['categories']
        # empty list serializes to '[]'
        parsed = json.loads(cat_raw) if cat_raw else []
        assert isinstance(parsed, list)

    # Validate scraped_at is ISO-8601 like
    from datetime import datetime
    for r in rows:
        ts = r['scraped_at']
        assert 'T' in ts, 'scraped_at should contain T separator'
        # Allow trailing 'Z' by normalizing
        norm = ts.replace('Z', '+00:00') if ts.endswith('Z') else ts
        datetime.fromisoformat(norm)  # will raise if not parseable
