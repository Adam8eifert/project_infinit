# 📁 extracting/google_spider.py
# Scrapy spider for Google News using the RSS bypass (No Consent Wall)

import scrapy
from urllib.parse import quote
from datetime import datetime
import lxml.etree as ET # Useful for cleaner XML parsing

from extracting.keywords import SEARCH_TERMS, EXCLUDE_TERMS
from extracting.csv_utils import get_output_csv_for_source, append_row, ensure_csv_header

class GoogleNewsRSSSpider(scrapy.Spider):
    name = "google_news_spider"
    allowed_domains = ["news.google.com"]

    # Base settings — FEEDS will be set dynamically in __init__ to honor config
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 1.5,
        'COOKIES_ENABLED': False, # Not needed for RSS
        'LOG_LEVEL': 'INFO'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SOURCE_KEY = 'google_news'
        try:
            from .csv_utils import get_output_csv_for_source, ensure_csv_header
            out = str(get_output_csv_for_source(self.SOURCE_KEY))
            ensure_csv_header(get_output_csv_for_source(self.SOURCE_KEY))
            # Use explicit dict copy to satisfy static type checkers
            new_settings = dict(self.custom_settings)  # type: ignore  # Scrapy Settings type stubs incomplete
            new_settings['FEEDS'] = {out: {'format': 'csv', 'encoding': 'utf8', 'overwrite': True}}  # type: ignore
            self.custom_settings = new_settings  # type: ignore
        except Exception:
            # fallback
            new_settings = dict(self.custom_settings)  # type: ignore  # Scrapy Settings type stubs incomplete
            new_settings['FEEDS'] = {'export/csv/google_news_raw.csv': {'format': 'csv', 'encoding': 'utf8', 'overwrite': True}}  # type: ignore
            self.custom_settings = new_settings  # type: ignore

    def start_requests(self):
        """Generates requests for Google News RSS feed"""
        # Ensure per-source CSV header exists
        try:
            from extracting.csv_utils import ensure_csv_header
            ensure_csv_header(get_output_csv_for_source('google_news'))
        except Exception:
            pass

        for term in SEARCH_TERMS:
            # RSS endpoint is different from the web search endpoint
            query = quote(term + ' ' + ' '.join(EXCLUDE_TERMS))
            # Added /rss/ to the path
            url = f"https://news.google.com/rss/search?q={query}&hl=cs&gl=CZ&ceid=CZ%3Acs"

            yield scrapy.Request(
                url=url,
                callback=self.parse_rss,
                meta={'query': term}
            )

    def parse_rss(self, response):
        """Parses the XML RSS feed from Google"""
        # Scrapy can use selectors on XML just like on HTML
        items = response.xpath('//item')
        
        for item in items:
            title = item.xpath('title/text()').get()
            # Google News RSS links often contain a redirect tracker
            google_link = item.xpath('link/text()').get()
            pub_date = item.xpath('pubDate/text()').get()
            source = item.xpath('source/text()').get()

            # Follow the link to get the actual article content
            yield scrapy.Request(
                url=google_link,
                callback=self.parse_article,
                meta={
                    'title': title,
                    'query': response.meta['query'],
                    'date_published': pub_date,
                    'source_name': source
                }
            )

    def parse_article(self, response):
        """Extracts the full text from the final destination page"""
        # Sometimes Google redirects through multiple layers
        final_url = response.url
        
        # Select all paragraphs to get the body text
        # We use a broad selector to cover various news sites
        paragraphs = response.css('article p::text, .article-body p::text, p::text').getall()
        full_text = ' '.join([p.strip() for p in paragraphs if len(p.strip()) > 30])

        if len(full_text) < 100:
            # Likely a paywall or cookie wall on the target site itself
            full_text = "[Content extraction failed or limited - possible paywall]"

        item = {
            "source_name": response.meta.get('source_name') or "Google News",
            "source_type": "news_aggregator",
            "title": response.meta.get('title'),
            "url": final_url,
            "text": full_text[:8000], # Limit for database safety
            "scraped_at": datetime.now().isoformat(),
            "query": response.meta.get('query'),
            "date_published": response.meta.get('date_published')
        }

        try:
            out_path = get_output_csv_for_source('google_news')
            append_row(out_path, item)
        except Exception:
            pass

        yield item