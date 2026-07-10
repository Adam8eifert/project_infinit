import config
import datetime
import pytest


def test_infer_movement_founded_year_uses_config_mapping():
    from main import _infer_movement_founded_year

    config_data = {
        "keywords": {
            "founded_years": {
                "Scientologická církev": 1954,
                "Svědkové Jehovovi": 1872,
            }
        }
    }

    assert _infer_movement_founded_year("Scientologická církev", config_data) == 1954
    assert _infer_movement_founded_year("Svědkové Jehovovi", config_data) == 1872
    assert _infer_movement_founded_year("Neznámé hnutí", config_data) is None


def test_dbconnector_insert_and_query(monkeypatch):
    # Use in-memory SQLite for tests
    monkeypatch.setattr(config, 'DB_URI', 'sqlite:///:memory:')

    from database.db_loader import DBConnector, Article, SourceType

    db = DBConnector()
    # create tables in the in-memory DB
    db.create_tables()

    # insert article and verify
    db.add_article(
        title='Test Article',
        content='Test content for unit testing',
        url='http://example.test/1',
        source_name='unit-test',
        source_type=SourceType.manual,
        language='cs'
    )

    session = db.get_session()
    try:
        res = session.query(Article).filter_by(url='http://example.test/1').one()
        assert res.title == 'Test Article'  # type: ignore
        assert res.source_name == 'unit-test'  # type: ignore
        assert res.source_type == SourceType.manual  # type: ignore
        assert res.content == 'Test content for unit testing'  # type: ignore
    finally:
        session.close()
