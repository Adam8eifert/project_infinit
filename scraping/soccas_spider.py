# 📁 scraping/soccas_spider.py
# Scrapy spider pro RG Encyklopedii – hlavní přehled článků z homepage

import scrapy
import datetime

class SocCasSpider(scrapy.Spider):
    name = "soccas"
    allowed_domains = ["rg-encyklopedie.soc.cas.cz"]
    start_urls = ["https://rg-encyklopedie.soc.cas.cz/index.php/Hlavn%C3%AD_strana"]

    custom_settings = {
        "FEEDS": {
            "export/csv/soccas_raw.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8",
            }
        },
        "LOG_LEVEL": "INFO"
    }

    def parse(self, response):
        links = response.css("div#mw-content-text a::attr(href)").getall()
        for href in links:
            if href.startswith("/index.php/") and not href.startswith("/index.php/Hlavn%C3%AD_strana"):
                full_url = response.urljoin(href)
                yield response.follow(full_url, callback=self.parse_article)

    def parse_article(self, response):
        title = response.css("h1.firstHeading::text").get()
        paragraphs = response.css("div#mw-content-text p::text").getall()
        full_text = " ".join([p.strip() for p in paragraphs if p.strip()])

        yield {
            "source_name": "rg-encyklopedie.soc.cas.cz",
            "source_type": "encyklopedie",
            "title": title,
            "url": response.url,
            "text": full_text,
            "scraped_at": datetime.datetime.now().isoformat()
        }
