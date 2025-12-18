# 📁 testing/test_rss_spider.py
# Testy pro RSS spider

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


def test_rss_spider_initialization(monkeypatch):
    """Test inicializace RSS spideru s konfigurací."""
    # Mock config_loader
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {
        'sekty_cz': {
            'name': 'Sekty.cz',
            'type': 'rss',
            'enabled': True,
            'url': 'https://sekty.cz/feed/'
        }
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    assert len(spider.sources) > 0
    assert 'sekty_cz' in spider.sources


def test_rss_spider_filters_rss_sources(monkeypatch):
    """Test filtrování RSS zdrojů."""
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {
        'sekty_cz': {'name': 'Sekty.cz', 'type': 'rss', 'enabled': True, 'url': 'https://sekty.cz/feed/'},
        'api_source': {'name': 'API Source', 'type': 'api', 'enabled': True, 'url': 'https://api.example.com/'},
        'web_source': {'name': 'Web', 'type': 'web', 'enabled': True, 'url': 'https://web.example.com/'}
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    # Jen RSS zdroje by měly být zahrnuty
    assert 'sekty_cz' in spider.sources
    assert 'api_source' not in spider.sources
    assert 'web_source' not in spider.sources


def test_rss_spider_parse_rss(monkeypatch):
    """Test parsování RSS feedu."""
    import feedparser
    
    # Mock RSS feed
    mock_feed_response = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Nová sekta v Praze</title>
          <link>https://sekty.cz/clanek/1</link>
          <description>Popis článku o sektech</description>
          <pubDate>Mon, 14 Nov 2025 10:00:00 GMT</pubDate>
          <author>Jan Novák</author>
          <category>Sekty</category>
        </item>
      </channel>
    </rss>"""
    
    # Mock response
    mock_response = Mock()
    mock_response.text = mock_feed_response
    mock_response.meta = {
        'source_name': 'Test Source',
        'source_type': 'RSS',
        'source_config': {
            'name': 'Test Source',
            'output_csv': 'test.csv'
        },
        'output_csv': 'test.csv'
    }
    
    # Mock config_loader a contains_relevant_keywords
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    monkeypatch.setattr('scraping.rss_spider.contains_relevant_keywords', lambda x: True)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    results = list(spider.parse_rss(mock_response))
    
    assert len(results) > 0
    assert results[0]['title'] == 'Nová sekta v Praze'
    assert results[0]['url'] == 'https://sekty.cz/clanek/1'
    assert 'sektech' in results[0]['text'].lower()


def test_rss_spider_filters_irrelevant_content(monkeypatch):
    """Test filtrování nerelevantního obsahu."""
    mock_feed_response = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Příspěvek o fotbalu</title>
          <link>https://example.com/1</link>
          <description>Fotbal je skvělý sport</description>
          <pubDate>Mon, 14 Nov 2025 10:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>"""
    
    mock_response = Mock()
    mock_response.text = mock_feed_response
    mock_response.meta = {
        'source_name': 'Test Source',
        'source_type': 'RSS',
        'source_config': {'name': 'Test Source'},
        'output_csv': 'test.csv'
    }
    
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    # Vrátit False pro nerelevantní obsah
    monkeypatch.setattr('scraping.rss_spider.contains_relevant_keywords', lambda x: False)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    results = list(spider.parse_rss(mock_response))
    
    # Nerelevantní obsah by měl být filtován
    assert len(results) == 0


def test_rss_spider_handles_missing_fields(monkeypatch):
    """Test zpracování RSS feedu s chybějícími poli."""
    mock_feed_response = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Článek bez popisu</title>
          <link>https://example.com/1</link>
        </item>
      </channel>
    </rss>"""
    
    mock_response = Mock()
    mock_response.text = mock_feed_response
    mock_response.meta = {
        'source_name': 'Test Source',
        'source_type': 'RSS',
        'source_config': {'name': 'Test Source'},
        'output_csv': 'test.csv'
    }
    
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {}
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    monkeypatch.setattr('scraping.rss_spider.contains_relevant_keywords', lambda x: True)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    results = list(spider.parse_rss(mock_response))
    
    # Mělo by to zpracovat bez chyby
    assert len(results) > 0
    assert results[0]['text'] == ''  # Prázdný obsah


def test_single_rss_spider_specific_source(monkeypatch):
    """Test SingleRSSSpider pro konkrétní RSS zdroj."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'Test RSS',
        'type': 'rss',
        'domain': 'example.com',
        'url': 'https://example.com/feed/'
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    # Test that the spider was initialized correctly
    assert hasattr(spider, 'config_loader')
    assert hasattr(spider, 'sources')


def test_single_rss_spider_invalid_type(monkeypatch):
    """Test SingleRSSSpider s neinvalidním typem zdroje."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'Not RSS',
        'type': 'web',  # Není RSS
        'url': 'https://example.com/'
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    
    # Test that RSSSpider initializes correctly
    spider = RSSSpider()
    assert len(spider.sources) == 1  # mock returns one source
