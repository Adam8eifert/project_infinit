# 📁 extracting/idnes_spider.py
# Spider for scraping iDNES.cz rubrika "Sekty, kulty, mesiáši"
# 
# ⚠️ IMPORTANT: iDNES.cz has strict cookie consent protection that blocks automated scrapers.
#    This spider requires Playwright middleware to handle JavaScript consent forms.
#    
# INSTALLATION:
#    pip install scrapy-playwright
#    playwright install chromium
#
# ALTERNATIVE: Use iDNES RSS feed (already in sources_config.yaml):
#    - idnes_domaci: https://servis.idnes.cz/rss.aspx?c=zpravodaj_domaci
#    - Filter by keywords after scraping

import scrapy
from datetime import datetime, timezone
from pathlib import Path
from w3lib.html import remove_tags
import re

from extracting.config_loader import get_config_loader
from extracting.keywords import contains_relevant_keywords
from extracting.spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS

class IDNESSekySpider(scrapy.Spider):
    """
    Spider for scraping iDNES.cz rubrika 'Sekty, kulty, mesiáši'
    URL: https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268
    
    Requires Playwright middleware for cookie consent handling.
    """
    name = "idnes_sekty"
    
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": True,
        
        # Playwright middleware for JavaScript/cookie consent handling
        "DOWNLOAD_HANDLERS": {
            "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
            "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        },
        "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
        
        "FEEDS": {
            "export/csv/idnes_sekty_raw.csv": {
                **CSV_EXPORT_SETTINGS,
                "overwrite": True
            }
        },
        "LOG_LEVEL": "INFO",
        "DOWNLOAD_DELAY": 3,
        "RETRY_TIMES": 3,
    }
    
    start_urls = [
        "https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268"
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Path("export/csv").mkdir(parents=True, exist_ok=True)
        self.logger.info("🔍 iDNES Sekty spider initialized")
        self.logger.warning("⚠️ This spider requires Playwright middleware - see file comments for setup")
    
    def start_requests(self):
        """Generate initial requests"""
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse_listing,
                dont_filter=True,
                errback=self.handle_error,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_page_goto_kwargs': {
                        'wait_until': 'networkidle',
                        'timeout': 60000,
                    }
                }
            )
    
    def parse_listing(self, response):
        """Parse article listing page"""
        self.logger.info(f"📄 Parsing listing: {response.url}")
        
        # iDNES uses various CSS classes for article links
        # Try multiple selectors
        article_selectors = [
            'div.art a::attr(href)',
            'article a.art-link::attr(href)',
            'div.c-item a::attr(href)',
            'a[href*="/clanek/"]::attr(href)',
        ]
        
        article_links = []
        for selector in article_selectors:
            links = response.css(selector).getall()
            if links:
                article_links.extend(links)
                self.logger.info(f"Found {len(links)} articles with selector: {selector}")
        
        # Remove duplicates and filter valid article URLs
        unique_links = list(set(article_links))
        valid_links = [link for link in unique_links if '/clanek/' in link]
        
        self.logger.info(f"📰 Found {len(valid_links)} unique article links")
        
        for link in valid_links[:50]:  # Limit to first 50 articles
            if link.startswith('http'):
                full_url = link
            else:
                full_url = response.urljoin(link)
            
            yield scrapy.Request(
                full_url,
                callback=self.parse_article,
                meta={
                    'playwright': True,
                    'playwright_page_goto_kwargs': {
                        'wait_until': 'networkidle',
                    }
                }
            )
        
        # Handle pagination if present
        next_page = response.css('a.paging-next::attr(href)').get()
        if next_page:
            self.logger.info(f"➡️ Following next page: {next_page}")
            yield response.follow(
                next_page,
                callback=self.parse_listing,
                meta={
                    'playwright': True,
                    'playwright_page_goto_kwargs': {
                        'wait_until': 'networkidle',
                    }
                }
            )
    
    def parse_article(self, response):
        """Parse individual article page"""
        try:
            # Extract article data using iDNES selectors
            title = response.css('h1.art-full__perex::text, h1::text').get() or ""
            title = title.strip()
            
            # Extract article text from multiple possible containers
            text_selectors = [
                'div.art-full__text p::text',
                'div.opener::text',
                'article p::text',
                'div.nfull p::text'
            ]
            
            text_parts = []
            for selector in text_selectors:
                parts = response.css(selector).getall()
                if parts:
                    text_parts.extend(parts)
            
            raw_text = ' '.join(text_parts)
            clean_text = ' '.join(raw_text.split()).strip()
            
            # Extract metadata
            author = response.css('span.autor::text, div.authors a::text').get() or "Unknown"
            author = author.strip()
            
            # Extract publication date
            date_text = response.css('span.time::attr(datetime), time::attr(datetime)').get()
            if not date_text:
                date_text = response.css('span.time::text, time::text').get() or ""
            
            # Relevance check
            combined_text = f"{title} {clean_text}"
            if not contains_relevant_keywords(combined_text):
                self.logger.debug(f"⏭️ Skipping irrelevant article: {title[:50]}")
                return
            
            item = {
                'source_name': 'iDNES.cz - Sekty, kulty, mesiáši',
                'source_type': 'web_scraping',
                'title': title,
                'url': response.url,
                'text': clean_text,
                'scraped_at': datetime.now(timezone.utc).isoformat(),
                'author': author,
                'published_at': date_text,
                'categories': 'sekty-kulty-mesiasi'
            }
            
            self.logger.info(f"✅ Scraped: {title[:60]}")
            yield item
            
        except Exception as e:
            self.logger.error(f"❌ Error parsing article {response.url}: {e}")
    
    def handle_error(self, failure):
        """Handle request errors"""
        request = failure.request
        self.logger.error(f"❌ Request failed: {request.url}")
