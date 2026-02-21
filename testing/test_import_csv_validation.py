from processing.import_csv_to_db import CSVtoDatabaseLoader


def test_validate_row_accepts_good():
    loader = CSVtoDatabaseLoader()
    good = {
        'source_name': 'Test',
        'source_type': 'RSS',
        'title': 'Some Title',
        'url': 'https://example.com/article',
        'text': 'This is a sufficiently long content for testing.',
        'scraped_at': '2020-01-01T12:00:00Z',
        'categories': '[]'
    }
    assert loader.validate_row(good, 'dummy.csv') is True


def test_validate_row_rejects_bad_date():
    loader = CSVtoDatabaseLoader()
    bad = {
        'source_name': 'Test',
        'source_type': 'RSS',
        'title': 'Some Title',
        'url': 'https://example.com/article',
        'text': 'This is a sufficiently long content for testing.',
        'scraped_at': 'not-a-date',
        'categories': '[]'
    }
    assert loader.validate_row(bad, 'dummy.csv') is False


def test_validate_row_rejects_bad_categories():
    loader = CSVtoDatabaseLoader()
    bad = {
        'source_name': 'Test',
        'source_type': 'RSS',
        'title': 'Some Title',
        'url': 'https://example.com/article',
        'text': 'This is a sufficiently long content for testing.',
        'scraped_at': '2020-01-01T12:00:00Z',
        'categories': '{not: json]'
    }
    assert loader.validate_row(bad, 'dummy.csv') is False


def test_clean_row_serializes_categories():
    loader = CSVtoDatabaseLoader()
    row = {
        'source_name': 'Test',
        'source_type': 'RSS',
        'title': 'Some Title',
        'url': 'https://example.com/article',
        'text': 'This is a sufficiently long content for testing.',
        'scraped_at': '2020-01-01T12:00:00Z',
        'categories': '["a","b"]'
    }
    cleaned = loader.clean_row(row)
    assert cleaned is not None
    assert 'keywords_found' in cleaned
    assert cleaned['keywords_found'] == '["a", "b"]' or cleaned['keywords_found'] == '["a","b"]'
