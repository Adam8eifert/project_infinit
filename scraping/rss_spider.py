import scrapy
import feedparser
from datetime import datetime
from pathlib import Path
from scraping.config_loader import get_config_loader
from scraping.keywords import contains_relevant_keywords
from scraping.spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS


class RSSSpider(scrapy.Spider):
    """
    Universal spider for parsing RSS/Atom feeds.
    Reads configuration from sources_config.yaml and processes all RSS sources.
    """
    name = "rss_universal"
    allowed_domains = []
    
    # Settings for exporting all RSS data to one CSV
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "FEEDS": {
            "export/csv/rss_combined_raw.csv": CSV_EXPORT_SETTINGS
        },
        "LOG_LEVEL": "INFO"
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.sources = self._get_rss_sources()
        self.logger.info(f"📡 Initializing RSS spider with {len(self.sources)} sources")
    
    def _get_rss_sources(self):
        """Returns a list of all enabled RSS sources from configuration."""
        all_sources = self.config_loader.get_enabled_sources()
        rss_sources = {
            key: source for key, source in all_sources.items()
            if source.get('type') == 'rss' and source.get('enabled', True)
        }
        return rss_sources
    
    def start_requests(self):
        """Generates requests for each RSS feed."""
        for source_key, source_config in self.sources.items():
            feed_url = source_config.get('url')
            if feed_url:
                self.logger.info(f"🔗 Processing RSS feed: {source_config['name']} ({feed_url})")
                yield scrapy.Request(
                    feed_url,
                    callback=self.parse_rss,
                    meta={
                        'source_key': source_key,
                        'source_config': source_config,
                        'source_name': source_config['name'],
                        'source_type': source_config.get('source_type', 'RSS'),
                        'output_csv': source_config.get('output_csv', 'export/csv/rss_raw.csv')
                    },
                    errback=self.handle_error
                )
    
    async def start(self):
        """Async start method for Scrapy 2.13+ compatibility."""
        for request in self.start_requests():
            yield request
    
    def parse_rss(self, response):
        """
        Parses RSS/Atom feed using feedparser.
        Extracts articles and saves to CSV.
        """
        try:
            # Parse RSS content
            feed = feedparser.parse(response.text)
            source_config = response.meta['source_config']
            selectors = source_config.get('selectors', {})
            
            self.logger.info(f"📰 Found {len(feed.entries)} items in {response.meta['source_name']}")
            
            for entry in feed.entries:
                # Data extraction from RSS item
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # Content - try multiple fields
                content_data = entry.get('content')
                if content_data and isinstance(content_data, list) and len(content_data) > 0:
                    content = content_data[0].get('value', '')
                else:
                    content = ''
                if not content:
                    content = entry.get('summary', '')
                if not content:
                    content = entry.get('description', '')
                
                # Author
                author = entry.get('author', 'Unknown')
                if isinstance(author, dict):
                    author = author.get('name', 'Unknown')
                
                # Publication date
                date_published = entry.get('published', '')
                
                # Categories
                tags = entry.get('tags', []) or []
                categories = [tag.get('term', '') for tag in tags if isinstance(tag, dict)]
                
                # Relevance check
                combined_text = f"{title} {content}"
                if not contains_relevant_keywords(combined_text):
                    self.logger.debug(f"⏭️  Article is not relevant: {title}")
                    continue
                
                # Output
                yield {
                    'source_name': response.meta['source_name'],
                    'source_type': response.meta['source_type'],
                    'title': str(title).strip() if title else '',
                    'url': link,
                    'text': str(content).strip() if content else '',
                    'scraped_at': datetime.utcnow().isoformat(),
                    'author': str(author).strip() if author else '',
                    'published_at': date_published,
                    'categories': categories
                }
        
        except Exception as e:
            self.logger.error(f"❌ Error parsing RSS: {e}")
    
    def handle_error(self, failure):
        """Handling errors when downloading feed."""
        request = failure.request
        source_name = request.meta.get('source_name', 'Unknown')
        self.logger.error(f"❌ Error downloading {source_name}: {failure.value}")


# Alternative spider for a single source (if you need to run a specific RSS)
# This spider is commented out because the main RSSSpider processes all sources
# class SingleRSSSpider(scrapy.Spider):
#     """Spider for running one specific RSS feed."""
#     name = "rss_single"
#     
#     def __init__(self, source_key='sekty_cz', *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.source_key = source_key
#         config_loader = get_config_loader()
#         self.source_config = config_loader.get_source(source_key)
#         
#         if not self.source_config:
#             raise ValueError(f"Source '{source_key}' not found in configuration")
#         
#         if self.source_config.get('type') != 'rss':
#            raise ValueError(f"Source '{source_key}' is not of type RSS")
#         
#         self.allowed_domains = [self.source_config.get('domain', '')]
#         self.start_urls = [self.source_config.get('url', '')]
#     
#     def parse(self, response):
#         """Same as RSSSpider.parse_rss."""
#         try:
#             feed = feedparser.parse(response.text)
#             self.logger.info(f"📰 Found {len(feed.entries)} items")
#             
#             for entry in feed.entries:
#                 title = entry.get('title', '')
#                 link = entry.get('link', '')
#                 content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
#                 author = entry.get('author', 'Unknown')
#                 date_published = entry.get('published', '')
#                 categories = [tag.get('term', '') for tag in entry.get('tags', [])]
#                 
#                 combined_text = f"{title} {content}"
#                 if not contains_relevant_keywords(combined_text):
#                     continue
#                 
#                 yield {
#                     'source_name': self.source_config['name'],
#                     'source_type': 'RSS',
#                     'title': title.strip(),
#                     'url': link,
#                     'text': content.strip(),
#                     'scraped_at': datetime.utcnow().isoformat(),
#                     'author': author.strip(),
#                     'published_at': date_published,
#                     'categories': categories
#                 }
#         
#         except Exception as e:
#             self.logger.error(f"❌ Error parsing RSS: {e}")
