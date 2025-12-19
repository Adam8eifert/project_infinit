# 📁 testing/test_api_spider.py
# Tests for API spider

import pytest
import json
from unittest.mock import Mock, MagicMock, patch


def test_api_spider_initialization(monkeypatch):
    """Test API spider initialization with configuration."""
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {
        'soccas': {
            'name': 'SOCCAS',
            'type': 'api',
            'enabled': True,
            'url': 'https://rg-encyklopedie.soc.cas.cz/api.php'
        }
    }
    
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.api_spider import APISpider
    spider = APISpider()
    
    assert len(spider.sources) > 0
    assert 'soccas' in spider.sources


def test_api_spider_filters_api_sources(monkeypatch):
    """Test filtering of API sources."""
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {
        'soccas': {'name': 'SOCCAS', 'type': 'api', 'enabled': True, 'url': 'https://api.example.com/'},
        'rss_source': {'name': 'RSS', 'type': 'rss', 'enabled': True, 'url': 'https://feed.example.com/'},
        'web_source': {'name': 'Web', 'type': 'web', 'enabled': True, 'url': 'https://web.example.com/'}
    }
    
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.api_spider import APISpider
    spider = APISpider()
    
    # Only API sources should be included
    assert 'soccas' in spider.sources
    assert 'rss_source' not in spider.sources
    assert 'web_source' not in spider.sources


def test_api_spider_parse_mediawiki_api(monkeypatch):
    """Test parsing MediaWiki API response."""
    mediawiki_response = {
        "parse": {
            "title": "Seznam církví a náboženských společností v Česku",
            "wikitext": "Questo je popis církví a sekt v České republice",
            "categories": [
                {"*": "Náboženství"}
            ]
        }
    }
    
    mock_response = Mock()
    mock_response.text = json.dumps(mediawiki_response)
    mock_response.url = 'https://api.example.com'
    mock_response.meta = {
        'source_name': 'Test API',
        'source_config': {
            'name': 'Test API',
            'api_method': 'parse'
        },
        'output_csv': 'test.csv'
    }
    
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    monkeypatch.setattr('scraping.api_spider.contains_relevant_keywords', lambda x: True)
    
    from scraping.api_spider import APISpider
    spider = APISpider()
    
    results = list(spider.parse_api(mock_response))
    
    assert len(results) > 0
    assert results[0]['title'] == 'Seznam církví a náboženských společností v Česku'
    assert 'církví' in results[0]['text']


def test_api_spider_filters_irrelevant_content(monkeypatch):
    """Test filtering of irrelevant content from API."""
    api_response = {
        "parse": {
            "title": "Jméno hráče",
            "wikitext": "Tento článek pojednává o fotbalistovi",
            "categories": []
        }
    }
    
    mock_response = Mock()
    mock_response.text = json.dumps(api_response)
    api_response = {
        "parse": {
            "title": "Jméno hráče",
            "wikitext": "Tento článek pojednává o fotbalistovi",
            "categories": []
        }
    }
    
    mock_response = Mock()
    mock_response.text = json.dumps(api_response)
    mock_response.url = 'https://api.example.com'
    mock_response.meta = {
        'source_name': 'Test API',
        'source_config': {'name': 'Test API', 'api_method': 'parse'},
        'output_csv': 'test.csv'
    }
    
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    # Return False for irrelevant content
    monkeypatch.setattr('scraping.api_spider.contains_relevant_keywords', lambda x: False)
    
    from scraping.api_spider import APISpider
    spider = APISpider()
    
    results = list(spider.parse_api(mock_response))
    
    # Irrelevant content should be filtered
    assert len(results) == 0


def test_api_spider_handles_invalid_json(monkeypatch):
    """Test zpracování neplatného JSON."""
    mock_response = Mock()
    mock_response.text = "{ invalid json }"
    mock_response.meta = {
        'source_name': 'Test API',
        'source_config': {'name': 'Test API'},
        'output_csv': 'test.csv'
    }
    
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.api_spider import APISpider
    spider = APISpider()
    
    # Should process without crashing
    results = list(spider.parse_api(mock_response))
    assert len(results) == 0


def test_api_spider_query_method(monkeypatch):
    """Test parsování MediaWiki API s query metodou."""
    api_response = {
        "query": {
            "pages": {
                "123": {
                    "title": "Nové náboženské hnutí",
                    "extract": "Popis hnutí o nových náboženských skupinách v ČR"
                }
            }
        }
    }
    
    mock_response = Mock()
    mock_response.text = json.dumps(api_response)
    mock_response.url = 'https://api.example.com'
    mock_response.meta = {
        'source_name': 'Test API Query',
        'source_config': {'name': 'Test API', 'api_method': 'query'},
        'output_csv': 'test.csv'
    }
    
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    monkeypatch.setattr('scraping.api_spider.contains_relevant_keywords', lambda x: True)
    
    from scraping.api_spider import APISpider
    spider = APISpider()
    
    results = list(spider.parse_api(mock_response))
    
    assert len(results) > 0
    assert results[0]['title'] == 'Nové náboženské hnutí'


def test_single_api_spider_specific_source(monkeypatch):
    """Test SingleAPISpider pro konkrétní API zdroj."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'Test API',
        'type': 'api',
        'url': 'https://api.example.com/',
        'api_params': {'action': 'query', 'format': 'json'}
    }
    
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.api_spider import SingleAPISpider
    spider = SingleAPISpider(source_key='test_api')
    
    assert spider.source_key == 'test_api'
    assert spider.source_config['type'] == 'api'  # type: ignore


def test_single_api_spider_invalid_type(monkeypatch):
    """Test SingleAPISpider with invalid source type."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'Not API',
        'type': 'rss',  # Not API
        'url': 'https://example.com/feed/'
    }
    
    monkeypatch.setattr('scraping.api_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.api_spider import SingleAPISpider
    
    with pytest.raises(ValueError, match="není typu API"):
        SingleAPISpider(source_key='not_api')
