# 📁 extracting/spiders/rss_spider.py
import scrapy
import feedparser
import random
from datetime import datetime, timezone
from pathlib import Path
from w3lib.html import remove_tags # For cleaning HTML from RSS feeds

# Internal project imports
from config_loader import get_config_loader
from keywords import contains_relevant_keywords
from spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS

class RSSSpider(scrapy.Spider):
    """
    Universal spider for parsing RSS/Atom feeds.
    Reads configuration from sources_config.yaml and processes all RSS sources.
    """
    name = "rss_universal"
    
    # Combined settings for robustness
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "ROBOTSTXT_OBEY": False, # Essential for mainstream RSS (Seznam, iRozhlas)
        "FEEDS": {
            "export/csv/rss_combined_raw.csv": {
                **CSV_EXPORT_SETTINGS,
                "overwrite": True # Ensuring we have a fresh file each full run
            }
        },
        "LOG_LEVEL": "INFO",
        "RETRY_TIMES": 5,
        "DOWNLOAD_TIMEOUT": 30
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.sources = self._get_rss_sources()
        
        # Ensure export directory exists
        Path("export/csv").mkdir(parents=True, exist_ok=True)
        
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
                self.logger.info(f"🔗 Requesting RSS: {source_config['name']}")
                yield scrapy.Request(
                    feed_url,
                    callback=self.parse_rss,
                    # We pass all metadata needed for CSV rows
                    meta={
                        'source_key': source_key,
                        'source_config': source_config,
                        'source_name': source_config['name'],
                        'source_type': 'RSS'
                    },
                    errback=self.handle_error,
                    dont_filter=True # RSS feeds update often, don't filter duplicate URLs
                )

    def parse_rss(self, response):
        """
        Parses RSS/Atom feed content and extracts relevant articles.
        """
        try:
            # Parse the XML/Atom content using feedparser
            feed = feedparser.parse(response.text)
            
            if not feed.entries:
                self.logger.warning(f"⚠️ No entries found for {response.meta['source_name']}")
                return

            self.logger.info(f"📰 Found {len(feed.entries)} items in {response.meta['source_name']}")
            
            for entry in feed.entries:
                # 1. Title extraction
                title = entry.get('title', '')
                
                # 2. Link extraction
                link = entry.get('link', '')
                
                # 3. Content extraction (priority: content -> summary -> description)
                raw_content = ""
                if 'content' in entry:
                    raw_content = entry.content[0].value
                elif 'summary' in entry:
                    raw_content = entry.summary
                elif 'description' in entry:
                    raw_content = entry.description
                
                # Clean HTML tags and excessive whitespace
                clean_text = remove_tags(raw_content).strip() if raw_content else ""
                clean_title = remove_tags(title).strip() if title else ""

                # 4. Relevance check using your custom keyword logic
                combined_text = f"{clean_title} {clean_text}"
                if not contains_relevant_keywords(combined_text):
                    continue
                
                # 5. Metadata extraction
                author = entry.get('author', 'Unknown')
                if isinstance(author, dict):
                    author = author.get('name', 'Unknown')
                
                date_published = entry.get('published', '')
                
                # Extract tags/categories
                categories = []
                if 'tags' in entry:
                    categories = [tag.get('term', '') for tag in entry.tags if isinstance(tag, dict)]

                # Final Item delivery
                yield {
                    'source_name': response.meta['source_name'],
                    'source_type': response.meta['source_type'],
                    'title': clean_title,
                    'url': link,
                    'text': clean_text,
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    'author': str(author),
                    'published_at': date_published,
                    'categories': categories
                }
        
        except Exception as e:
            self.logger.error(f"❌ Error parsing RSS for {response.meta.get('source_name')}: {e}")
    
    def handle_error(self, failure):
        """Standard error handling for failed requests."""
        request = failure.request
        source_name = request.meta.get('source_name', 'Unknown')
        self.logger.error(f"❌ Connection failed for {source_name}: {failure.value}")