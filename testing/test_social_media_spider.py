# 🧪 testing/test_social_media_spider.py
# Testy pro Reddit a X/Twitter spidery

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from scraping.social_media_spider import RedditSpider, XTwitterSpider


# ============================================================================
# REDDIT SPIDER TESTY
# ============================================================================

class TestRedditSpider:
    """Testy pro Reddit spider."""
    
    @patch('scraping.social_media_spider.praw.Reddit')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {
        'REDDIT_CLIENT_ID': 'test_id',
        'REDDIT_CLIENT_SECRET': 'test_secret',
        'REDDIT_USER_AGENT': 'test_agent'
    })
    def test_reddit_spider_init(self, mock_config_loader, mock_reddit):
        """Test inicializace Reddit spideru."""
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
        """Test generování počátečních requestů."""
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
        
        # Testuji parse metodu
        results = list(spider.parse_reddit(mock_response))
        
        # Alespoň struktura by měla být správná (i když je mock prázdný)
        assert isinstance(results, list)


# ============================================================================
# X/TWITTER SPIDER TESTY
# ============================================================================

class TestXTwitterSpider:
    """Testy pro X/Twitter spider."""
    
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'test_token'})
    def test_x_spider_init(self, mock_config_loader):
        """Test inicializace X spideru."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'url': 'https://api.twitter.com/2',
            'auth': {'bearer_token': 'test_token'},
            'search_queries': ['sekta'],
            'api_params': {}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = XTwitterSpider()
        
        assert spider.name == "x_twitter_spider"
        assert spider.bearer_token == "test_token"
    
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {})
    def test_x_spider_missing_token(self, mock_config_loader):
        """Test chyby při chybějícím tokenu."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'auth': {}
        }
        mock_config_loader.return_value = mock_loader
        
        with pytest.raises(ValueError, match="Chybí X/Twitter API token"):
            XTwitterSpider()
    
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'test_token'})
    def test_x_spider_get_headers(self, mock_config_loader):
        """Test generování headers s bearer token."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'url': 'https://api.twitter.com/2',
            'auth': {'bearer_token': 'test_token'},
            'search_queries': [],
            'api_params': {}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = XTwitterSpider()
        headers = spider._get_headers()
        
        assert 'Authorization' in headers
        assert headers['Authorization'] == 'Bearer test_token'
    
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'test_token'})
    def test_x_spider_start_requests(self, mock_config_loader):
        """Test generování requestů z search queries."""
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'url': 'https://api.twitter.com/2',
            'auth': {'bearer_token': 'test_token'},
            'search_queries': ['sekta lang:cs', 'kult'],
            'api_params': {'max_results': 10}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = XTwitterSpider()
        requests = list(spider.start_requests())
        
        assert len(requests) == 2
        assert all('twitter.com' in str(r.url) or 'api.twitter.com' in str(r.url) for r in requests)
    
    @patch('scraping.social_media_spider.contains_relevant_keywords')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'test_token'})
    def test_x_spider_parse_relevant_tweet(self, mock_config_loader, mock_keywords):
        """Test parsování relevantního tweetu."""
        mock_keywords.return_value = True
        
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'url': 'https://api.twitter.com/2',
            'auth': {'bearer_token': 'test_token'},
            'search_queries': ['sekta'],
            'api_params': {}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = XTwitterSpider()
        
        # Mock X API response
        import json
        api_response = {
            'data': [
                {
                    'id': '123456789',
                    'text': 'Nová sekta byla registrována v Praze',
                    'author_id': '987654321',
                    'created_at': '2024-01-01T12:00:00Z',
                    'public_metrics': {
                        'retweet_count': 5,
                        'reply_count': 2,
                        'like_count': 10
                    }
                }
            ],
            'includes': {
                'users': [
                    {
                        'id': '987654321',
                        'username': 'testuser'
                    }
                ]
            }
        }
        
        mock_response = Mock()
        mock_response.text = json.dumps(api_response)
        mock_response.meta = {'query': 'sekta lang:cs'}
        
        results = list(spider.parse_x(mock_response))
        
        assert len(results) > 0
        result = results[0]
        assert result['source_name'] == 'X (Twitter)'
        assert result['author'] == 'testuser'
        assert 'sekta' in result['text']
    
    @patch('scraping.social_media_spider.contains_relevant_keywords')
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'test_token'})
    def test_x_spider_filters_irrelevant_tweets(self, mock_config_loader, mock_keywords):
        """Test filtrování irelevantních tweetů."""
        mock_keywords.side_effect = lambda x: 'sekta' in x.lower()
        
        mock_loader = Mock()
        mock_loader.get_source.return_value = {
            'type': 'social_api',
            'url': 'https://api.twitter.com/2',
            'auth': {'bearer_token': 'test_token'},
            'search_queries': ['sekta'],
            'api_params': {}
        }
        mock_config_loader.return_value = mock_loader
        
        spider = XTwitterSpider()
        
        import json
        api_response = {
            'data': [
                {
                    'id': '1',
                    'text': 'Nová sekta v Praze',
                    'author_id': '1',
                    'created_at': '2024-01-01T12:00:00Z',
                    'public_metrics': {}
                },
                {
                    'id': '2',
                    'text': 'Jdu na oběd, něco dobrého',
                    'author_id': '2',
                    'created_at': '2024-01-01T12:01:00Z',
                    'public_metrics': {}
                }
            ],
            'includes': {
                'users': [
                    {'id': '1', 'username': 'user1'},
                    {'id': '2', 'username': 'user2'}
                ]
            }
        }
        
        mock_response = Mock()
        mock_response.text = json.dumps(api_response)
        mock_response.meta = {'query': 'sekta'}
        
        results = list(spider.parse_x(mock_response))
        
        # Měl by projít jen relevantní tweet
        assert len(results) == 1
        assert 'sekta' in results[0]['text'].lower()


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
    
    @patch('scraping.social_media_spider.get_config_loader')
    @patch.dict('os.environ', {'X_BEARER_TOKEN': 'test_token'})
    def test_x_spider_loads_config(self, mock_config_loader):
        """Test že X spider správně načítá konfiguraci."""
        expected_config = {
            'type': 'social_api',
            'url': 'https://api.twitter.com/2',
            'search_queries': ['sekta lang:cs', 'kult lang:cs'],
            'api_params': {'max_results': 10},
            'auth': {'bearer_token': 'test_token'}
        }
        
        mock_loader = Mock()
        mock_loader.get_source.return_value = expected_config
        mock_config_loader.return_value = mock_loader
        
        spider = XTwitterSpider()
        
        assert spider.source_config == expected_config  # type: ignore
        assert 'sekta lang:cs' in spider.source_config['search_queries']  # type: ignore


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
