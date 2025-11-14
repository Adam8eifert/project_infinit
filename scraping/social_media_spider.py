# 📁 scraping/social_media_spider.py
# Univerzální spider pro sociální média (Reddit, X/Twitter API)
# Dynamicky čte konfiguraci ze sources_config.yaml

import scrapy
import praw
import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from scraping.config_loader import get_config_loader
from scraping.keywords import contains_relevant_keywords


# Načtení .env souboru
load_dotenv()


class RedditSpider(scrapy.Spider):
    """
    Spider pro Reddit API.
    Hledá příspěvky o sektách a náboženských hnutích.
    """
    name = "reddit_spider"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.source_config = self.config_loader.get_source('reddit')
        
        if not self.source_config or self.source_config.get('type') != 'social_api':
            raise ValueError("Reddit zdroj není nakonfigurován nebo není typu social_api")
        
        # Načti API klíče z environment nebo config
        client_id = os.getenv('REDDIT_CLIENT_ID') or self.source_config.get('auth', {}).get('client_id')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET') or self.source_config.get('auth', {}).get('client_secret')
        user_agent = os.getenv('REDDIT_USER_AGENT') or self.source_config.get('auth', {}).get('user_agent')
        
        if not all([client_id, client_secret, user_agent]):
            self.logger.warning("⚠️ Reddit API klíče nejsou nastaveny. Nastavte env proměnné:")
            self.logger.warning("   REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT")
            raise ValueError("Chybějí Reddit API klíče")
        
        # Inicializuj Reddit API
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        self.logger.info("✅ Reddit API inicializován")
    
    def start_requests(self):
        """Pro Reddit používáme přímé API místo HTTP requestů."""
        # V Scrapymu musíme vrátit alespoň jeden request
        yield scrapy.Request(
            'https://www.reddit.com/r/occult/.json',
            callback=self.parse_reddit,
            dont_download=True,
            dont_filter=True
        )
    
    def parse_reddit(self, response):
        """Extrahuje příspěvky z Redditu a filtruje relevantní obsah."""
        try:
            self.logger.info("📱 Hledám příspěvky na Redditu...")
            
            subreddits = self.source_config.get('subreddits', [])
            search_terms = self.source_config.get('search_terms', [])
            output_csv = self.source_config.get('output_csv', 'export/csv/reddit_raw.csv')
            
            submissions = []
            
            # Hledej v konkrétních subredditech
            for subreddit_name in subreddits:
                subreddit_name = subreddit_name.replace('r/', '')
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Hledej nové příspěvky
                    for submission in subreddit.new(limit=50):
                        combined_text = f"{submission.title} {submission.selftext}"
                        
                        # Kontrola relevance
                        if contains_relevant_keywords(combined_text):
                            submissions.append({
                                'source_name': 'Reddit',
                                'source_type': 'Social Media',
                                'title': submission.title,
                                'url': f"https://reddit.com{submission.permalink}",
                                'text': submission.selftext[:5000],  # Omezení délky
                                'scraped_at': datetime.utcnow().isoformat(),
                                'author': str(submission.author),
                                'score': submission.score,
                                'num_comments': submission.num_comments,
                                'created': datetime.fromtimestamp(submission.created_utc).isoformat(),
                                'subreddit': subreddit_name
                            })
                            self.logger.info(f"✓ Reddit: {submission.title[:50]}")
                
                except Exception as e:
                    self.logger.error(f"❌ Chyba při hledání v r/{subreddit_name}: {e}")
                    continue
            
            # Také hledej podle klíčových slov
            for term in search_terms:
                try:
                    for submission in self.reddit.subreddit('all').search(term, time_filter='month', limit=30):
                        combined_text = f"{submission.title} {submission.selftext}"
                        
                        if contains_relevant_keywords(combined_text):
                            submissions.append({
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
                            })
                            self.logger.info(f"✓ Reddit (hledání '{term}'): {submission.title[:50]}")
                
                except Exception as e:
                    self.logger.error(f"❌ Chyba při hledání '{term}': {e}")
                    continue
            
            self.logger.info(f"📊 Nalezeno {len(submissions)} relevantních příspěvků na Redditu")
            
            for submission in submissions:
                yield submission
        
        except Exception as e:
            self.logger.error(f"❌ Chyba při parsování Redditu: {e}")


class XTwitterSpider(scrapy.Spider):
    """
    Spider pro X (Twitter) API v2.
    Hledá tweety o sektách a náboženských hnutích.
    """
    name = "x_twitter_spider"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.source_config = self.config_loader.get_source('x_twitter')
        
        if not self.source_config or self.source_config.get('type') != 'social_api':
            raise ValueError("X/Twitter zdroj není nakonfigurován nebo není typu social_api")
        
        # Načti bearer token
        self.bearer_token = os.getenv('X_BEARER_TOKEN') or self.source_config.get('auth', {}).get('bearer_token')
        
        if not self.bearer_token:
            self.logger.warning("⚠️ X/Twitter API token není nastaven. Nastavte env proměnnou:")
            self.logger.warning("   X_BEARER_TOKEN")
            raise ValueError("Chybí X/Twitter API token")
        
        self.base_url = self.source_config.get('url', 'https://api.twitter.com/2')
        self.logger.info("✅ X/Twitter API inicializován")
    
    def start_requests(self):
        """Generuje požadavky pro X API."""
        search_queries = self.source_config.get('search_queries', [])
        
        for query in search_queries:
            search_url = f"{self.base_url}/tweets/search/recent"
            
            params = {
                'query': query,
                **self.source_config.get('api_params', {})
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
        """Vrátí headers s bearer token."""
        return {
            'Authorization': f'Bearer {self.bearer_token}',
            'User-Agent': 'ProjectInfinit/1.0'
        }
    
    def parse_x(self, response):
        """Parsuje odpověď z X API a extrahuje tweety."""
        try:
            import json
            data = json.loads(response.text)
            
            query = response.meta.get('query')
            self.logger.info(f"📱 Zpracovávám tweety pro dotaz: '{query}'")
            
            tweets = data.get('data', [])
            includes = data.get('includes', {})
            users = {user['id']: user['username'] for user in includes.get('users', [])}
            
            for tweet in tweets:
                text = tweet.get('text', '')
                
                # Kontrola relevance
                if contains_relevant_keywords(text):
                    author_id = tweet.get('author_id', '')
                    author_name = users.get(author_id, 'Unknown')
                    
                    yield {
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
                    self.logger.info(f"✓ X: @{author_name}: {text[:50]}")
            
            self.logger.info(f"📊 Nalezeno {len([t for t in tweets if contains_relevant_keywords(t.get('text', ''))])} relevantních tweetů")
        
        except Exception as e:
            self.logger.error(f"❌ Chyba při parsování X API: {e}")
    
    def handle_error(self, failure):
        """Zpracování chyb API."""
        self.logger.error(f"❌ X API chyba: {failure.value}")
        query = failure.request.meta.get('query', 'Unknown')
        self.logger.error(f"   Dotaz: {query}")
