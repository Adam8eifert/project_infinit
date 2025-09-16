# 📁 scraping/pastorace_spider.py
# Scrapy spider pro pastorace.cz – kategorie Sekty a kulty

import scrapy
import datetime

class PastoraceSpider(scrapy.Spider):
    name = "pastorace"
    allowed_domains = ["pastorace.cz"]
    start_urls = ["https://www.pastorace.cz/Clanky/Nabozenstvi/Sekty-a-kulty"]

    custom_settings = {
        "FEEDS": {
            "export/csv/pastorace_raw.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8",
            }
        },
        "LOG_LEVEL": "INFO"
    }

    keywords = [
        "sekta", "nové náboženské hnutí", "nová náboženská hnutí",
        "nové duchovní hnutí", "nová duchovní hnutí",
        "náboženská skupina", "náboženská komunita",
        "alternativní náboženství", "kontroverzní náboženská společnost",
        "destruktivní kult", "kult", "nové spirituální hnutí"
    ]

    def parse(self, response):
        links = response.css(".list-articles a::attr(href)").getall()
        for href in links:
            full_url = response.urljoin(href)
            yield response.follow(full_url, callback=self.parse_article)

    def parse_article(self, response):
        title = response.css("h1::text").get()
        content = response.css("div.article *::text").getall()
        full_text = " ".join([t.strip() for t in content if t.strip()])

        yield {
            "source_name": "pastorace.cz",
            "source_type": "web",
            "title": title,
            "url": response.url,
            "text": full_text,
            "scraped_at": datetime.datetime.now().isoformat()
        }
