# 📁 scraping/google_spider.py – Scrapy spider pro Google News (raw export bez NLP)

import scrapy
from urllib.parse import quote
import datetime

class GoogleNewsSpider(scrapy.Spider):
    name = "google_news_spider"

    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'LOG_LEVEL': 'INFO',
        'FEEDS': {
            'export/csv/google_news_raw.csv': {
                'format': 'csv',
                'overwrite': True,
                'encoding': 'utf8'
            }
        }
    }

    search_terms = [
        "sekta",
        "nové náboženské hnutí",
        "nová náboženská hnutí",
        "nové duchovní hnutí",
        "nová duchovní hnutí",
        "náboženská skupina",
        "náboženská komunita",
        "alternativní náboženství",
        "kontroverzní náboženská společnost",
        "destruktivní kult",
        "kult",
        "nové spirituální hnutí"
    ]

    exclude_terms = [
        "-politika", "-film", "-hudba", "-hra", "-počítačová"
    ]

    def start_requests(self):
        for term in self.search_terms:
            query = quote(term + ' ' + ' '.join(self.exclude_terms))
            url = f"https://news.google.com/search?q={query}&hl=cs&gl=CZ&ceid=CZ%3Acs"
            yield scrapy.Request(url=url, callback=self.parse, meta={'query': term})

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
        title = response.meta['title']
        url = response.meta['url']
        text = ' '.join(response.css('article p::text').getall())

        yield {
            "source_name": "Google News",
            "source_type": "zpravodajství",
            "title": title,
            "url": url,
            "text": text,
            "scraped_at": datetime.datetime.now().isoformat()
        }
