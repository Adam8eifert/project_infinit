# 📁 scraping/google_spider.py
# Scrapy spider pro Google News (raw export bez NLP)

import scrapy
from urllib.parse import quote
from datetime import datetime
from scraping.spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS
from scraping.keywords import SEARCH_TERMS, EXCLUDE_TERMS

class GoogleNewsSpider(scrapy.Spider):
    name = "google_news_spider"
    allowed_domains = ["news.google.com"]
    
    # Kombinace etického nastavení s vlastním nastavením
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        'ROBOTSTXT_OBEY': True,  # Explicitně respektujeme robots.txt
        'FEEDS': {
            'export/csv/google_news_raw.csv': CSV_EXPORT_SETTINGS
        },
        'LOG_LEVEL': 'INFO'
    }

    def start_requests(self):
        """Generuje požadavky pro každý vyhledávací termín"""
        for term in SEARCH_TERMS:
            query = quote(term + ' ' + ' '.join(EXCLUDE_TERMS))
            url = f"https://news.google.com/search?q={query}&hl=cs&gl=CZ&ceid=CZ%3Acs"
            
            # Přidáváme informace o zdroji do meta
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'query': term,
                    'source_name': 'Google News',
                    'source_type': 'Zpravodajský agregátor'
                }
            )

    def parse(self, response):
        articles = response.css('article')
        for article in articles:
            title = article.css('h3::text, h4::text').get()
            link = article.css('a::attr(href)').get()
            if link:
                full_url = response.urljoin(link.replace('./', ''))
                yield scrapy.Request(full_url, callback=self.parse_article, meta={
                    'title': title,
                    'url': full_url,
                    'query': response.meta['query']
                })

    def parse_article(self, response):
        """Zpracuje jednotlivý článek a extrahuje jeho obsah."""
        title = response.meta['title']
        url = response.meta['url']
        query = response.meta['query']
        
        # Extrahujeme text z článku (zkusíme několik běžných selektorů)
        text_parts = []
        text_parts.extend(response.css('article p::text').getall())
        if not text_parts:  # Záložní selektory
            text_parts.extend(response.css('.article-content p::text').getall())
            text_parts.extend(response.css('.entry-content p::text').getall())
            text_parts.extend(response.css('.post-content p::text').getall())
        
        text = ' '.join(text_parts).strip()
        
        # Metadata
        date_published = response.css('time::attr(datetime), meta[property="article:published_time"]::attr(content)').get()
        author = response.css('.author::text, .byline::text').get() or "Neznámý"
        
        yield {
            "source_name": "Google News",
            "source_type": "zpravodajství",
            "title": title,
            "url": url,
            "text": text,
            "scraped_at": datetime.now().isoformat(),
            "query": query,
            "author": author,
            "date_published": date_published
        }
