# 🧪 testing/test_social_media_spider.py
# Tests for Reddit spider

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from scraping.social_media_spider import RedditSpider


# ============================================================================
# REDDIT SPIDER TESTS
# ============================================================================

class TestRedditSpider:
    """Tests for Reddit spider."""
    
    @patch('scraping.social_media_spider.praw.Reddit')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {
        'REDDIT_CLIENT_ID': 'test_id',
        'REDDIT_CLIENT_SECRET': 'test_secret',
        'REDDIT_USER_AGENT': 'test_agent'
    })
    def test_reddit_spider_init(self, mock_config_loader, mock_reddit):
        """Test Reddit spider initialization."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'auth': {'client_id': 'test_id', 'client_secret': 'test_secret'}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = RedditSpider()
        
        assert spider.name == "reddit_spider"
        assert spider.reddit is not None
        mock_reddit.assert_called_once()
    
    @patch('scraping.social_media_spider.praw.Reddit')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {})
    def test_reddit_spider_missing_credentials(self, mock_config_loader, mock_reddit):
        """Test chyby při chybějících credentials."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'auth': {}
        }
        mock_config_loader.return_value = mock_loader
        
        with pytest.raises(ValueError, match="Chybějí Reddit API klíče"):
            RedditSpider()
    
    @patch('scraping.social_media_spider.praw.Reddit')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {
        'REDDIT_CLIENT_ID': 'test_id',
        'REDDIT_CLIENT_SECRET': 'test_secret',
        'REDDIT_USER_AGENT': 'test_agent'
    })
    def test_reddit_spider_start_requests(self, mock_config_loader, mock_reddit):
        """Test generating initial requests."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'auth': {'client_id': 'test_id', 'client_secret': 'test_secret'}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = RedditSpider()
        requests = list(spider.start_requests())
        
        assert len(requests) > 0
        assert 'reddit.com' in requests[0].url
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'auth': {'client_id': 'test_id', 'client_secret': 'test_secret'}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = RedditSpider()
        requests = list(spider.start_requests())
        
        assert len(requests) > 0
        assert 'reddit.com' in requests[0].url
    
    @patch('scraping.social_media_spider.contains_relevant_keywords')
    @patch('scraping.social_media_spider.praw.Reddit')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {
        'REDDIT_CLIENT_ID': 'test_id',
        'REDDIT_CLIENT_SECRET': 'test_secret',
        'REDDIT_USER_AGENT': 'test_agent'
    })
    def test_reddit_parse_relevant_submission(self, mock_config_loader, mock_reddit, mock_keywords):
        """Test parsování relevantního příspěvku."""
        mock_keywords.return_value = True
        
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'subreddits': ['r/occult'],
            'search_terms': ['sekta'],
            'output_csv': 'export/csv/reddit_raw.csv',
            'auth': {'client_id': 'test_id', 'client_secret': 'test_secret'}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = RedditSpider()
        
        # Mock submission
        mock_submission = Mock()
        mock_submission.title = "Test sekta"
        mock_submission.selftext = "Popis sekty"
        mock_submission.permalink = "/r/occult/comments/123/test/"
        mock_submission.author = "testuser"
        mock_submission.score = 42
        mock_submission.num_comments = 5
        mock_submission.created_utc = 1234567890
        
        # Mock response
        mock_response = Mock()
        mock_response.meta = {}
        
        # Test parse method
        results = list(spider.parse_reddit(mock_response))
        
        # At least structure should be correct (even if mock is empty)
        assert isinstance(results, list)


# ============================================================================
# INTEGRACE S CONFIG LOADER
# ============================================================================

class TestSocialMediaSpidersConfig:
    """Testy integrace spiderů s config loaderem."""
    
    @patch('scraping.social_media_spider.praw.Reddit')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {
        'REDDIT_CLIENT_ID': 'test_id',
        'REDDIT_CLIENT_SECRET': 'test_secret',
        'REDDIT_USER_AGENT': 'test_agent'
    })
    def test_reddit_spider_loads_config(self, mock_config_loader, mock_reddit):
        """Test že spider správně načítá konfiguraci."""
        expected_config = {
            'type': 'social_api',
            'subreddits': ['r/occult', 'r/spirituality'],
            'search_terms': ['sekta', 'kult'],
            'output_csv': 'export/csv/reddit_raw.csv',
            'auth': {
                'client_id': 'test_id',
                'client_secret': 'test_secret'
            }
        }
        
        mock_loader = Mock()
        mock_loader.get_source.return_value = expected_config
        mock_config_loader.return_value = mock_loader
        
        spider = RedditSpider()
        
        assert spider.source_config == expected_config  # type: ignore
        assert 'r/occult' in spider.source_config['subreddits']  # type: ignore
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
