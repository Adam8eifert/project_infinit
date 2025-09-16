# 📁 scraping/wikipedia_spider.py – Wikipedia API místo scrappingu

import scrapy
import datetime
import json
from urllib.parse import urlencode

class WikipediaSpider(scrapy.Spider):
    name = "wikipedia"
    allowed_domains = ["cs.wikipedia.org"]

    custom_settings = {
        "FEEDS": {
            "export/csv/wikipedia_raw.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8"
            }
        },
        "LOG_LEVEL": "INFO"
    }

    def start_requests(self):
        params = {
            "action": "parse",
            "page": "Seznam_církví_a_náboženských_společností_v_Česku",
            "format": "json",
            "prop": "wikitext",
            "formatversion": 2
        }
        url = f"https://cs.wikipedia.org/w/api.php?{urlencode(params)}"
        yield scrapy.Request(url, callback=self.parse_api)

    def parse_api(self, response):
        data = json.loads(response.text)
        wikitext = data.get("parse", {}).get("wikitext", "")

        # velmi jednoduchý extraktor – spolehá se na formát seznamu s hvězdičkami
        lines = wikitext.split("\n")
        for line in lines:
            if line.startswith("*"):
                name = line.lstrip("* ").strip()
                if name:
                    yield {
                        "source_name": "Wikipedia",
                        "source_type": "encyklopedie",
                        "title": name,
                        "url": "https://cs.wikipedia.org/wiki/Seznam_církví_a_náboženských_společností_v_Česku",
                        "text": "",
                        "scraped_at": datetime.datetime.now().isoformat()
                    }
