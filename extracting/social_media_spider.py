# 📁 extracting/social_media_spider.py
# Universal spider for social media (Reddit, X/Twitter API)
# Dynamically reads configuration from sources_config.yaml

import scrapy
import praw
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
# Use a runtime lookup of the shim module so tests can patch this symbol.
# We import the shim module by name to avoid hard-binding to the top-level
# function; the actual function used will be resolved at runtime (and thus
# can be patched by tests on the `scraping.social_media_spider` module).
import scraping.social_media_spider as shim
from extracting.keywords import contains_relevant_keywords
from extracting.csv_utils import get_output_csv_for_source, append_row


# Load .env file
load_dotenv()


class RedditSpider(scrapy.Spider):
    """
    Spider for Reddit API.
    Searches for posts about cults and religious movements.
    """
    name = "reddit_spider"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Resolve the config loader at runtime so tests can patch
        # `scraping.social_media_spider.get_config_loader`.
        self.config_loader = shim.get_config_loader()
        self.source_config = self.config_loader.get_source('reddit')
        
        if not self.source_config or self.source_config.get('type') != 'social_api':
            raise ValueError("Reddit source is not configured or is not of type social_api")
        
        # At this point, source_config is guaranteed to be not None
        assert self.source_config is not None
        
        # Load API keys from environment or config
        client_id = os.getenv('REDDIT_CLIENT_ID') or self.source_config.get('auth', {}).get('client_id')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET') or self.source_config.get('auth', {}).get('client_secret')
        user_agent = os.getenv('REDDIT_USER_AGENT') or self.source_config.get('auth', {}).get('user_agent')
        
        if not all([client_id, client_secret, user_agent]):
            self.logger.warning("⚠️ Reddit API keys are not set. Set environment variables:")
            self.logger.warning("   REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
            # Lokalizované chybové hlášení pro testy
            raise ValueError("Chybějí Reddit API klíče")
        
        # Initialize Reddit API
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        self.logger.info("✅ Reddit API initialized")
    
    def start_requests(self):
        """For Reddit we use direct API instead of HTTP requests."""
        # In Scrapy we must return at least one request
        yield scrapy.Request(
            'https://www.reddit.com/r/occult/.json',
            callback=self.parse_reddit,
            dont_filter=True
        )
    
    def parse_reddit(self, response):
        """Extracts posts from Reddit and filters relevant content."""
        try:
            self.logger.info("📱 Searching for posts on Reddit...")

            subreddits = self.source_config.get('subreddits', [])
            search_terms = self.source_config.get('search_terms', [])
            output_csv = self.source_config.get('output_csv', 'export/csv/reddit_raw.csv')

            submissions = []

            # Search in specific subreddits
            for subreddit_name in subreddits:
                subreddit_name = subreddit_name.replace('r/', '')
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    for submission in subreddit.new(limit=50):
                        combined_text = f"{submission.title} {submission.selftext}"

                        # Relevance check
                        if contains_relevant_keywords(combined_text):
                            row = {
                                'source_name': 'Reddit',
                                'source_type': 'Social Media',
                                'title': submission.title,
                                'url': f"https://reddit.com{submission.permalink}",
                                'text': submission.selftext[:5000],
                                'scraped_at': datetime.utcnow().isoformat(),
                                'author': str(submission.author),
                                'score': submission.score,
                                'num_comments': submission.num_comments,
                                'created': datetime.fromtimestamp(submission.created_utc).isoformat(),
                                'subreddit': subreddit_name
                            }

                            # Write to configured CSV (if configured)
                            try:
                                out_path = get_output_csv_for_source('reddit')
                                append_row(out_path, row)
                            except Exception as e:
                                self.logger.debug(f"Could not write Reddit CSV row: {e}")

                            submissions.append(row)
                            self.logger.info(f"✓ Reddit: {submission.title[:50]}")

                except Exception as e:
                    self.logger.error(f"❌ Error searching in r/{subreddit_name}: {e}")
                    continue

            # Also search by keywords
            for term in search_terms:
                try:
                    for submission in self.reddit.subreddit('all').search(term, time_filter='month', limit=30):
                        combined_text = f"{submission.title} {submission.selftext}"

                        if contains_relevant_keywords(combined_text):
                            row = {
                                'source_name': 'Reddit',
                                'source_type': 'Social Media',
                                'title': submission.title,
                                'url': f"https://reddit.com{submission.permalink}",
                                'text': submission.selftext[:5000],
                                'scraped_at': datetime.utcnow().isoformat(),
                                'author': str(submission.author),
                                'score': submission.score,
                                'num_comments': submission.num_comments,
                                'created': datetime.fromtimestamp(submission.created_utc).isoformat(),
                                'search_term': term
                            }

                            try:
                                out_path = get_output_csv_for_source('reddit')
                                append_row(out_path, row)
                            except Exception as e:
                                self.logger.debug(f"Could not write Reddit CSV row (search): {e}")

                            submissions.append(row)
                            self.logger.info(f"✓ Reddit (search '{term}'): {submission.title[:50]}")

                except Exception as e:
                    self.logger.error(f"❌ Error searching '{term}': {e}")
                    continue

            self.logger.info(f"📊 Found {len(submissions)} relevant posts on Reddit")

            for submission in submissions:
                yield submission

        except Exception as e:
            self.logger.error(f"❌ Error parsing Reddit: {e}")


class XTwitterSpider(scrapy.Spider):
    """
    Spider for X (Twitter) API v2.
    Searches for tweets about cults and religious movements.
    """
    name = "x_twitter_spider"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Resolve the config loader at runtime so tests can patch
        # `scraping.social_media_spider.get_config_loader`.
        self.config_loader = shim.get_config_loader()
        self.source_config = self.config_loader.get_source('x_twitter')
        
        if not self.source_config or self.source_config.get('type') != 'social_api':
            raise ValueError("X/Twitter source is not configured or is not of type social_api")
        
        # At this point, source_config is guaranteed to be not None
        assert self.source_config is not None
        
        # Ensure CSV header exists for configured output
        try:
            out_path = get_output_csv_for_source('x_twitter')
            from csv_utils import ensure_csv_header
            ensure_csv_header(out_path)
        except Exception:
            pass
        
        # Load bearer token
        self.bearer_token = os.getenv('X_BEARER_TOKEN') or self.source_config.get('auth', {}).get('bearer_token')
        
        if not self.bearer_token:
            self.logger.warning("⚠️ X/Twitter API token is not set. Set environment variable:")
            self.logger.warning("   X_BEARER_TOKEN")
            # Lokalizované chybové hlášení pro testy
            raise ValueError("Chybí X/Twitter API token")
        
        self.base_url = self.source_config.get('url', 'https://api.twitter.com/2')
        self.logger.info("✅ X/Twitter API initialized")
    
    def start_requests(self):
        """Generates requests for X API."""
        search_queries = self.source_config.get('search_queries', [])  # type: ignore
        
        for query in search_queries:
            search_url = f"{self.base_url}/tweets/search/recent"
            
            params = {
                'query': query,
                **self.source_config.get('api_params', {})  # type: ignore
            }
            
            headers = self._get_headers()
            
            yield scrapy.Request(
                search_url,
                method='GET',
                meta={'query': query},
                headers=headers,
                callback=self.parse_x,
                dont_filter=True,
                errback=self.handle_error
            )
    
    def _get_headers(self):
        """Returns headers with bearer token."""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': 'ProjectInfinit/1.0'
        }
    
    def parse_x(self, response):
        """Parses response from X API and extracts tweets."""
        try:
            import json
            data = json.loads(response.text)
            
            query = response.meta.get('query')
            self.logger.info(f"📱 Processing tweets for query: '{query}'")
            
            tweets = data.get('data', [])
            includes = data.get('includes', {})
            users = {user['id']: user['username'] for user in includes.get('users', [])}
            
            for tweet in tweets:
                text = tweet.get('text', '')
                
                # Relevance check
                if contains_relevant_keywords(text):
                    author_id = tweet.get('author_id', '')
                    author_name = users.get(author_id, 'Unknown')

                    row = {
                        'source_name': 'X (Twitter)',
                        'source_type': 'Social Media',
                        'title': text[:100],
                        'url': f"https://twitter.com/i/web/status/{tweet['id']}",
                        'text': text,
                        'scraped_at': datetime.utcnow().isoformat(),
                        'author': author_name,
                        'created': tweet.get('created_at', ''),
                        'metrics': tweet.get('public_metrics', {}),
                        'search_query': query
                    }

                    try:
                        out_path = get_output_csv_for_source('x_twitter')
                        append_row(out_path, row)
                    except Exception as e:
                        self.logger.debug(f"Could not write X CSV row: {e}")

                    yield row
        
        except Exception as e:
            self.logger.error(f"❌ Error parsing X API: {e}")
    
    def handle_error(self, failure):
        """Handling API errors."""
        self.logger.error(f"❌ X API error: {failure.value}")
        query = failure.request.meta.get('query', 'Unknown')
        self.logger.error(f"   Query: {query}")
