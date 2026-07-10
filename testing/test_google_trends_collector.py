import sys
import types
from datetime import datetime

# Stub pytrends if it is not installed to allow unit tests to import the collector.
if 'pytrends' not in sys.modules:
    pytrends = types.ModuleType('pytrends')
    pytrends.request = types.ModuleType('pytrends.request')
    class DummyTrendReq:
        def __init__(self, hl=None, tz=None):
            pass
    pytrends.request.TrendReq = DummyTrendReq
    sys.modules['pytrends'] = pytrends
    sys.modules['pytrends.request'] = pytrends.request

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.db_loader import Base, GoogleTrend
from trends.google_trends_collector import GoogleTrendsCollector


class DummyConfigLoader:
    def __init__(self, config):
        self.config = config


def make_collector(config):
    collector = object.__new__(GoogleTrendsCollector)
    collector.config_loader = DummyConfigLoader(config)
    collector.trends_config = collector._load_trends_config()
    return collector


def test_load_trend_keywords_merges_explicit_and_global_required_keywords():
    config = {
        "keywords": {
            "required": ["sekta", "kult"],
            "google_trends": {
                "keywords": ["explicit term"]
            }
        }
    }
    collector = make_collector(config)

    keywords = collector._load_trend_keywords()

    assert "explicit term" in keywords
    assert "sekta" in keywords
    assert "kult" in keywords
    assert keywords[0] == "explicit term"


def test_load_trend_keywords_filters_global_excludes():
    config = {
        "keywords": {
            "required": ["sekta", "film sekta"],
            "exclude": ["film"],
            "google_trends": {
                "keywords": ["explicit", "politika"]
            }
        },
        "content_filters": {
            "exclude_keywords": ["politika"]
        }
    }
    collector = make_collector(config)

    keywords = collector._load_trend_keywords()

    assert "film sekta" not in keywords
    assert "politika" not in keywords
    assert "sekta" in keywords
    assert "explicit" in keywords


def test_clear_existing_trend_rows_removes_stale_regions_and_current_keywords():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    session.add_all([
        GoogleTrend(keyword="sekta", date=datetime(2024, 1, 1), interest_value=10, region="CZ"),
        GoogleTrend(keyword="sekta", date=datetime(2024, 1, 2), interest_value=20, region="SK"),
        GoogleTrend(keyword="scientologie", date=datetime(2024, 1, 3), interest_value=30, region="CZ"),
    ])
    session.commit()

    collector = object.__new__(GoogleTrendsCollector)
    collector.session = session

    collector._clear_existing_trend_rows()

    remaining = session.query(GoogleTrend).all()
    assert remaining == []
