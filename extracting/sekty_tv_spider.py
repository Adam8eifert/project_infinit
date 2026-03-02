# 📁 extracting/sekty_tv_spider.py
"""
Web scraper spider for Sekty.TV
Specialized website about cults and religious movements in Czech Republic
Scrapes full article content (title, text, metadata)
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
    Scrapes article pages for full content (title, text, metadata)
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
        self.articles_to_process = []  # Queue links to follow for full content
    
    def parse(self, response):
        """
        Parse sekty.tv main page and article list pages
        Collects article links for content extraction
        """
        self.logger.info(f"📄 Scraping {response.url}")
        
        # CSS selectors for WordPress article structure on sekty.tv
        article_links = response.css('article.post h2 a::attr(href), article.post h3 a::attr(href), '
                                     'article.post .entry-title a::attr(href), '
                                     'article.post a::attr(href)').getall()
        
        if not article_links:
            self.logger.warning("⚠️  No article links found on page")
            # Try alternative selectors
            article_links = response.css('a.read-more::attr(href)').getall()
        
        if article_links:
            self.logger.info(f"📰 Found {len(article_links)} article links on page")
            
            # Follow each article link to get full content
            for link in article_links:
                full_url = response.urljoin(link)
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_article,
                    errback=self.handle_error
                )
        
        # Follow pagination
        next_page = response.css('a.next::attr(href), a.page-numbers:last-child::attr(href)').get()
        if next_page:
            self.logger.info(f"🔗 Following pagination: {next_page}")
            yield scrapy.Request(next_page, callback=self.parse)
        else:
            self.logger.info(f"✅ Main page scraping complete. Processing {len(article_links)} articles...")

    def parse_article(self, response):
        """
        Parse individual article page and extract full content
        """
        try:
            # Title extraction
            title = response.css('h1.entry-title::text, h1.post-title::text, h1::text').get('').strip()
            if not title:
                title = response.css('header.entry-header h1::text').get('').strip()
            if not title:
                title = response.css('title::text').get('').strip()
                if ' - ' in title:
                    title = title.split(' - ')[0].strip()
            
            # Content extraction - FULL TEXT (not just excerpt)
            # Try multiple selectors for WordPress content
            content_selectors = [
                'div.entry-content p::text',
                'div.post-content p::text',
                'article.post p::text',
                'div.the-content p::text',
                'div.content-wrapper p::text'
            ]
            
            full_text = ""
            for selector in content_selectors:
                parts = response.css(selector).getall()
                if parts:
                    full_text = ' '.join(parts).strip()
                    if len(full_text) > 50:  # Only accept if substantial
                        break
            
            # Clean HTML tags and normalize whitespace
            clean_text = remove_tags(full_text).strip() if full_text else ""
            clean_text = ' '.join(clean_text.split())  # Normalize whitespace
            
            # Relevance check BEFORE processing
            combined_text = f"{title} {clean_text}"
            if not contains_relevant_keywords(combined_text):
                self.logger.debug(f"⏭️  Skipping irrelevant article: {title[:50]}")
                return
            
            # Author extraction
            author = response.css('span.author-name::text, .post-author::text, .by-author::text').get('Unknown').strip()
            author = remove_tags(author) if author else 'Unknown'
            
            # Date extraction
            published_at = response.css('time::attr(datetime), time::text').get('')
            if not published_at:
                published_at = response.css('span.posted-on::text').get('')
            
            # Categories/tags extraction
            categories = response.css('a[rel="category tag"]::text').getall()
            categories_str = ','.join(categories) if categories else ''
            
            # URL and validation
            url = response.url
            if not url.startswith(('http://', 'https://')):
                self.logger.warning("⚠️  Skipping article - invalid URL")
                return
            
            # Skip if missing critical fields
            if not title:
                self.logger.warning("⚠️  Skipping article - missing title")
                return
            
            if len(clean_text) < 3:  # Very minimal text requirement
                self.logger.debug(f"⚠️  Skipping article with very short content: {title[:50]}")
                return
            
            item = {
                'source_name': 'Sekty.TV (Web)',
                'source_type': 'Web',
                'title': title,
                'url': url,
                'text': clean_text,
                'scraped_at': datetime.now(timezone.utc).isoformat(),
                'author': author,
                'published_at': published_at,
                'categories': categories_str
            }
            
            self.articles_found += 1
            self.logger.info(f"✅ Article {self.articles_found}: {title[:60]}...")
            
            # Write to CSV immediately
            try:
                append_row(Path('export/csv/sekty_tv_web_raw.csv'), item)
            except Exception as e:
                self.logger.warning(f"⚠️  Could not write CSV: {e}")
            
            yield item
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing article {response.url}: {e}")
    
    def handle_error(self, failure):
        """Handle request errors gracefully"""
        self.logger.error(f"❌ Request failed for {failure.request.url}: {failure.value}")
