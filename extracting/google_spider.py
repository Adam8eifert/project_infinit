# 📁 extracting/google_spider.py
# Scrapy spider for Google News (raw export without NLP)

import scrapy
from urllib.parse import quote
from datetime import datetime
# Import settings and keywords from local project files
try:
    from spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS
    from keywords import SEARCH_TERMS, EXCLUDE_TERMS
except ImportError:
    # Fallback values if imports fail
    SEARCH_TERMS = ["sekty", "kult"]
    EXCLUDE_TERMS = ["-ufo"]

class GoogleNewsSpider(scrapy.Spider):
    name = "google_news_spider"
    allowed_domains = ["news.google.com", "google.com"]
    
    # FIXED INDENTATION: custom_settings must be inside the class
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'COOKIES_ENABLED': True, 
        'DOWNLOAD_DELAY': 2.5, # Be gentle to avoid being blocked by Google
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'cs,en-US;q=0.7,en;q=0.3',
            'Referer': 'https://www.google.com/'
        },
        # Direct export to CSV to ensure data is saved
        'FEEDS': {
            'export/csv/google_news_raw.csv': {
                'format': 'csv',
                'encoding': 'utf8',
                'overwrite': True,
            }
        }
    }

    def start_requests(self):
        """Generates requests for each search term defined in keywords.py"""
        for term in SEARCH_TERMS:
            # Combine term with excluded keywords and encode for URL
            query = quote(term + ' ' + ' '.join(EXCLUDE_TERMS))
            url = f"https://news.google.com/search?q={query}&hl=cs&gl=CZ&ceid=CZ%3Acs"
            
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'query': term,
                    'source_name': 'Google News'
                }
            )

    def parse(self, response):
        """Parses the search results page and follows article links"""
        articles = response.css('article')
        for article in articles:
            title = article.css('h3::text, h4::text, a::text').get()
            link = article.css('a::attr(href)').get()
            
            if link:
                # Handle relative links used by Google News
                full_url = response.urljoin(link.replace('./', ''))
                yield scrapy.Request(
                    full_url, 
                    callback=self.parse_article, 
                    meta={
                        'title': title,
                        'url': full_url,
                        'query': response.meta['query']
                    }
                )

    def parse_article(self, response):
        """Processes the final article page after redirection"""
        title = response.meta.get('title')
        url = response.url # Use final URL after redirects
        query = response.meta.get('query')
        
        # Extract text content using various common selectors
        text_parts = response.css('article p::text, .article-content p::text, .entry-content p::text, p::text').getall()
        # Filter out short fragments to get meaningful paragraphs
        text = ' '.join([p.strip() for p in text_parts if len(p.strip()) > 20])
        
        # Handle cases where extraction failed
        if not text:
            text = "Content extraction failed (possible dynamic content or bot protection)."

        yield {
            "source_name": "Google News",
            "source_type": "news",
            "title": title,
            "url": url,
            "text": text[:5000], # Limit text length for database storage
            "scraped_at": datetime.now().isoformat(),
            "query": query,
            "author": response.css('.author::text, meta[name="author"]::attr(content)').get() or "Unknown",
            "date_published": response.css('time::attr(datetime), meta[property="article:published_time"]::attr(content)').get()
        }