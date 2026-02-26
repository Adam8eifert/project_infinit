# 📁 extracting/sekty_tv_spider.py
"""
Web scraper spider for Sekty.TV
Specialized website about cults and religious movements in Czech Republic
"""
import scrapy
from datetime import datetime, timezone
from pathlib import Path
from w3lib.html import remove_tags

from extracting.keywords import contains_relevant_keywords
from extracting.spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS
from extracting.csv_utils import append_row


class SektyTVSpider(scrapy.Spider):
    """
    Web scraper for sekty.tv - Specialist website about cults and religious movements
    Scrapes main page and paginated content
    """
    name = "sekty_tv_web"
    allowed_domains = ["sekty.tv"]
    start_urls = ["https://sekty.tv/"]
    
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "ROBOTSTXT_OBEY": False,  # sekty.tv respects crawlers
        "FEEDS": {
            "export/csv/sekty_tv_web_raw.csv": {
                **CSV_EXPORT_SETTINGS,
                "overwrite": True
            }
        },
        "LOG_LEVEL": "INFO",
        "RETRY_TIMES": 3,
        "DOWNLOAD_TIMEOUT": 20
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Path("export/csv").mkdir(parents=True, exist_ok=True)
        self.logger.info("🔍 Initializing Sekty.TV web scraper")
        self.articles_found = 0
    
    def parse(self, response):
        """
        Parse sekty.tv main page and article list pages
        WordPress structure with article classes
        """
        self.logger.info(f"📄 Scraping {response.url}")
        
        # CSS selectors for WordPress article structure
        articles = response.css('article.post, div.post.entry')
        
        if not articles:
            self.logger.warning("⚠️ No articles found on page")
            # Try to follow pagination
            next_page = response.css('a.next::attr(href)').get()
            if next_page:
                yield scrapy.Request(next_page, callback=self.parse)
            return
        
        self.logger.info(f"📰 Found {len(articles)} articles on page")
        
        for article in articles:
            try:
                # Title extraction
                title = article.css('h2 a::text, h3 a::text, .entry-title::text').get('').strip()
                if not title:
                    title = article.css('a::text').get('').strip()
                
                # URL extraction
                url = article.css('h2 a::attr(href), h3 a::attr(href), .entry-title a::attr(href)').get('')
                if not url:
                    url = article.css('a::attr(href)').get('')
                
                # Content extraction - get post excerpt
                excerpt = article.css('.entry-excerpt::text, .post-excerpt::text, p::text').getall()
                full_text = ' '.join(excerpt).strip() if excerpt else ''
                
                # If no excerpt, get first paragraph from content
                if not full_text:
                    paragraphs = article.css('.entry-content p::text, .post-content p::text').getall()
                    full_text = ' '.join(paragraphs[:3]).strip() if paragraphs else ''
                
                # Relevance check
                combined_text = f"{title} {full_text}"
                if not contains_relevant_keywords(combined_text):
                    continue
                
                # Author extraction
                author = article.css('.author::text, .post-author::text, .by-author::text').get('Unknown').strip()
                author = remove_tags(author) if author else 'Unknown'
                
                # Date extraction
                published_at = article.css('time::attr(datetime), .published::attr(datetime), .post-date::text').get('')
                if not published_at:
                    published_at = article.css('span.posted-on::text').get('')
                
                # Categories/tags
                categories = article.css('a[rel="category tag"]::text').getall()
                
                # Skip if missing critical fields
                if not title or not url:
                    self.logger.warning("⚠️ Skipping article - missing title or URL")
                    continue
                
                # Clean text
                clean_text = remove_tags(full_text).strip()
                
                item = {
                    'source_name': 'Sekty.TV (Web)',
                    'source_type': 'Web',
                    'title': title,
                    'url': url,
                    'text': clean_text,
                    'scraped_at': datetime.now(timezone.utc).isoformat(),
                    'author': author,
                    'published_at': published_at,
                    'categories': categories
                }
                
                self.articles_found += 1
                self.logger.info(f"✅ Article {self.articles_found}: {title[:60]}...")
                
                # Write to CSV
                try:
                    append_row('export/csv/sekty_tv_web_raw.csv', item)
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not write CSV: {e}")
                
                yield item
            
            except Exception as e:
                self.logger.error(f"❌ Error parsing article: {e}")
                continue
        
        # Follow pagination
        next_page = response.css('a.next::attr(href), a.page-numbers:last-child::attr(href)').get()
        if next_page:
            self.logger.info(f"🔗 Following pagination: {next_page}")
            yield scrapy.Request(next_page, callback=self.parse)
        else:
            self.logger.info(f"✅ Scraping complete. Found {self.articles_found} relevant articles")
    
    def errback_httpbin(self, failure):
        """Handle request errors"""
        self.logger.error(f"❌ Request failed: {failure.value}")
