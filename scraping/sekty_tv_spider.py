# 📁 scraping/sekty_tv_spider.py
# Scrapy spider pro sekty.tv – extrahuje články a ukládá do export/csv/sekty_tv_raw.csv

import scrapy
import datetime
from pathlib import Path

class SektyTVSpider(scrapy.Spider):
    name = "sekty_tv"
    allowed_domains = ["sekty.tv"]
    start_urls = ["https://sekty.tv/"]

    custom_settings = {
        "FEEDS": {
            "export/csv/sekty_tv_raw.csv": {
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
        articles = response.css("article")
        for article in articles:
            url = article.css("h2.entry-title a::attr(href)").get()
            if url:
                yield response.follow(url, callback=self.parse_article)

    def parse_article(self, response):
        title = response.css("h1.entry-title::text").get()
        content = response.css("div.entry-content *::text").getall()
        full_text = " ".join([t.strip() for t in content if t.strip()])

        yield {
            "source_name": "sekty.tv",
            "source_type": "web",
            "title": title,
            "url": response.url,
            "text": full_text,
            "scraped_at": datetime.datetime.now().isoformat()
        }
