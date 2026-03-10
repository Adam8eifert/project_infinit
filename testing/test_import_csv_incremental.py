from datetime import datetime

import pandas as pd

from database.db_loader import Article, DBConnector, Movement, SourceType
from processing.import_csv_to_db import CSVtoDatabaseLoader


def _create_loader():
    db = DBConnector("sqlite:///:memory:")
    db.create_tables()
    return db, CSVtoDatabaseLoader(db)


def _write_csv(path, rows):
    pd.DataFrame(rows).to_csv(path, index=False)


def _row(title="Sample title", text="Sample content"):
    return {
        "source_name": "unit-test",
        "source_type": "rss",
        "title": title,
        "url": "https://example.test/article-1",
        "text": text,
        "scraped_at": "2026-01-01T00:00:00Z",
    }


def test_incremental_insert_new_article(tmp_path, monkeypatch):
    db, loader = _create_loader()
    monkeypatch.setattr(loader, "_is_article_relevant", lambda cleaned, csv_path=None: True)

    csv_path = tmp_path / "sample_raw.csv"
    _write_csv(csv_path, [_row()])

    changed = loader.load_csv_to_articles(csv_path)
    assert changed == 1

    session = db.get_session()
    try:
        assert session.query(Article).count() == 1
    finally:
        session.close()


def test_incremental_skip_unchanged_article(tmp_path, monkeypatch):
    db, loader = _create_loader()
    monkeypatch.setattr(loader, "_is_article_relevant", lambda cleaned, csv_path=None: True)

    db.add_article(
        title="Sample title",
        content="Sample content",
        url="https://example.test/article-1",
        source_name="unit-test",
        source_type=SourceType.rss,
        domain="example.test",
        language="cs",
        published_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    csv_path = tmp_path / "sample_raw.csv"
    _write_csv(csv_path, [_row()])

    changed = loader.load_csv_to_articles(csv_path)
    assert changed == 0

    session = db.get_session()
    try:
        article = session.query(Article).filter(Article.url == "https://example.test/article-1").one()
        assert article.title == "Sample title"
        assert article.content == "Sample content"
    finally:
        session.close()


def test_incremental_update_existing_article(tmp_path, monkeypatch):
    db, loader = _create_loader()
    monkeypatch.setattr(loader, "_is_article_relevant", lambda cleaned, csv_path=None: True)

    db.add_article(
        title="Old title",
        content="Old content",
        url="https://example.test/article-1",
        source_name="unit-test",
        source_type=SourceType.rss,
        domain="example.test",
        language="cs",
        published_at=datetime(2026, 1, 1, 0, 0, 0),
    )

    csv_path = tmp_path / "sample_raw.csv"
    _write_csv(csv_path, [_row(title="New title", text="New content")])

    changed = loader.load_csv_to_articles(csv_path)
    assert changed == 1

    session = db.get_session()
    try:
        article = session.query(Article).filter(Article.url == "https://example.test/article-1").one()
        assert article.title == "New title"
        assert article.content == "New content"
    finally:
        session.close()


def test_incremental_updates_movement_link(tmp_path, monkeypatch):
    db, loader = _create_loader()
    monkeypatch.setattr(loader, "_is_article_relevant", lambda cleaned, csv_path=None: True)

    session = db.get_session()
    try:
        movement_a = Movement(name="Movement A")
        movement_b = Movement(name="Movement B")
        article = Article(
            title="Movement title",
            content="Movement content",
            url="https://example.test/article-1",
            source_name="unit-test",
            source_type=SourceType.rss,
            domain="example.test",
            language="cs",
            published_at=datetime(2026, 1, 1, 0, 0, 0),
        )
        article.movements = [movement_a]

        session.add_all([movement_a, movement_b, article])
        session.commit()

        movement_b_id = movement_b.id
    finally:
        session.close()

    csv_path = tmp_path / "sample_raw.csv"
    _write_csv(csv_path, [_row(title="Movement title", text="Movement content")])

    monkeypatch.setattr(loader, "validate_row", lambda row, csv_file: True)
    monkeypatch.setattr(
        loader,
        "clean_row",
        lambda row: {
            "title": "Movement title",
            "content": "Movement content",
            "url": "https://example.test/article-1",
            "source_name": "unit-test",
            "source_type": SourceType.rss,
            "author": None,
            "domain": "example.test",
            "language": "cs",
            "published_at": datetime(2026, 1, 1, 0, 0, 0),
            "movement_id": movement_b_id,
        },
    )

    changed = loader.load_csv_to_articles(csv_path)
    assert changed == 1

    session = db.get_session()
    try:
        article = session.query(Article).filter(Article.url == "https://example.test/article-1").one()
        movement_ids = sorted(m.id for m in article.movements)
        assert movement_ids == [movement_b_id]
    finally:
        session.close()
