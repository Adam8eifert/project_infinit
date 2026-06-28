import sys
import types

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
