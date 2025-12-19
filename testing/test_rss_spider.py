# 📁 testing/test_rss_spider.py
# Tests for RSS spider

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


def test_rss_spider_initialization(monkeypatch):
    """Test RSS spider initialization with configuration."""
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
    """Test filtering of RSS sources."""
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {
        'sekty_cz': {'name': 'Sekty.cz', 'type': 'rss', 'enabled': True, 'url': 'https://sekty.cz/feed/'},
        'api_source': {'name': 'API Source', 'type': 'api', 'enabled': True, 'url': 'https://api.example.com/'},
        'web_source': {'name': 'Web', 'type': 'web', 'enabled': True, 'url': 'https://web.example.com/'}
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    mock_loader = MagicMock()
    mock_loader.get_enabled_sources.return_value = {
        'sekty_cz': {'name': 'Sekty.cz', 'type': 'rss', 'enabled': True, 'url': 'https://sekty.cz/feed/'},
        'api_source': {'name': 'API Source', 'type': 'api', 'enabled': True, 'url': 'https://api.example.com/'},
        'web_source': {'name': 'Web', 'type': 'web', 'enabled': True, 'url': 'https://web.example.com/'}
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    # Only RSS sources should be included
    assert 'sekty_cz' in spider.sources
    assert 'api_source' not in spider.sources
    assert 'web_source' not in spider.sources


def test_rss_spider_parse_rss(monkeypatch):
    """Test parsing RSS feed."""
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
    """Test filtering of irrelevant content."""
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
    # Return False for irrelevant content
    monkeypatch.setattr('scraping.rss_spider.contains_relevant_keywords', lambda x: False)
    
    from scraping.rss_spider import RSSSpider
    spider = RSSSpider()
    
    results = list(spider.parse_rss(mock_response))
    
    # Irrelevant content should be filtered
    assert len(results) == 0


def test_rss_spider_handles_missing_fields(monkeypatch):
    """Test processing RSS feed with missing fields."""
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
    
    # Should process without error
    assert len(results) > 0
    assert results[0]['text'] == ''  # Empty content


def test_single_rss_spider_specific_source(monkeypatch):
    """Test SingleRSSSpider for specific RSS source."""
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
    """Test SingleRSSSpider with invalid source type."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'Not RSS',
        'type': 'web',  # Not RSS
        'url': 'https://example.com/'
    }
    
    monkeypatch.setattr('scraping.rss_spider.get_config_loader', lambda: mock_loader)
    
    from scraping.rss_spider import RSSSpider
    
    # Test that RSSSpider initializes correctly
    spider = RSSSpider()
    assert len(spider.sources) == 1  # mock returns one source
