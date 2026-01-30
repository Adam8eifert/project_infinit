from pathlib import Path
import tempfile
import shutil
from extracting.csv_utils import get_output_csv_for_source, ensure_csv_header, append_row
from extracting.config_loader import get_config_loader


def test_get_output_csv_default(tmp_path, monkeypatch):
    # Point config loader to a temp config to simulate missing source
    monkeypatch.chdir(tmp_path)
    p = get_output_csv_for_source('nonexistent_source')
    assert str(p).endswith('nonexistent_source_raw.csv')


def test_get_output_csv_config():
    p = get_output_csv_for_source('google_news')
    assert str(p).endswith('google_news_raw.csv')


def test_ensure_and_append(tmp_path):
    dst = tmp_path / 'export' / 'csv'
    dst.mkdir(parents=True)
    csv_path = dst / 'test_source_raw.csv'

    ensure_csv_header(csv_path)
    assert csv_path.exists()

    append_row(csv_path, {
        'source_name': 'Test', 'source_type': 'RSS', 'title': 'T', 'url': 'http://x',
        'text': 'content', 'scraped_at': '2020-01-01T00:00:00Z', 'author': 'A', 'published_at': '', 'categories': []
    })

    content = csv_path.read_text(encoding='utf8')
    assert 'source_name' in content
    assert 'Test' in content
