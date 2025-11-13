import config
import datetime
import pytest


def test_dbconnector_insert_and_query(monkeypatch):
    # Use in-memory SQLite for tests
    monkeypatch.setattr(config, 'DB_URI', 'sqlite:///:memory:')

    from database.db_loader import DBConnector, Source

    db = DBConnector()
    # create tables in the in-memory DB
    db.create_tables()

    sample = [{
        'movement_id': None,
        'source_name': 'unit-test',
        'source_type': 'test',
        'publication_date': None,
        'sentiment_rating': 'neutral',
        'url': 'http://example.test/1'
    }]

    # insert and verify
    db.insert_sources(sample)

    session = db.Session()
    try:
        res = session.query(Source).filter_by(url='http://example.test/1').one()
        assert res.source_name == 'unit-test'
        assert res.source_type == 'test'
    finally:
        session.close()
