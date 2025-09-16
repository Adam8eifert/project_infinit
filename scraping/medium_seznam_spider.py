import scrapy
import datetime
from scraping.keywords import keywords

class MediumSeznamSpider(scrapy.Spider):
    name = "medium_seznam"
    allowed_domains = ["medium.seznam.cz"]
    start_urls = ["https://medium.seznam.cz/"]

    custom_settings = {
        "FEEDS": {
            "export/csv/medium_seznam_raw.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8",
            }
        },
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 5.0,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "LOG_LEVEL": "INFO"
    }

    def parse(self, response):
        articles = response.css("article a::attr(href)").getall()
        for link in articles:
            yield response.follow(link, callback=self.parse_article)

    def parse_article(self, response):
        text = " ".join(response.css("article *::text").getall()).strip()
        title = response.css("h1::text").get() or ""
        yield {
            "source_name": "medium.seznam.cz",
            "source_type": "web",
            "title": title,
            "url": response.url,
            "text": text,
            "scraped_at": datetime.datetime.now().isoformat()
        }
