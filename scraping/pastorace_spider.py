# 📁 scraping/pastorace_spider.py
# Scrapy spider pro pastorace.cz - sekce Sekty a kulty

import scrapy
from datetime import datetime
from .spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS

class PastoraceSpider(scrapy.Spider):
    name = "pastorace"
    allowed_domains = ["pastorace.cz"]
    start_urls = ["https://www.pastorace.cz/Clanky/Nabozenstvi/Sekty-a-kulty"]

    # Kombinace etického nastavení s vlastním nastavením
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "FEEDS": {
            "export/csv/pastorace_raw.csv": CSV_EXPORT_SETTINGS
        },
        "LOG_LEVEL": "INFO"
    }

    def start_requests(self):
        """Inicializace s meta daty o zdroji"""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'source_name': 'Pastorace.cz',
                    'source_type': 'Náboženský web'
                },
                errback=self.handle_error
            )

    def parse(self, response):
        """Parsování seznamu článků"""
        try:
            links = response.css(".list-articles a::attr(href)").getall()
            for href in links:
                full_url = response.urljoin(href)
                yield response.follow(
                    full_url,
                    callback=self.parse_article,
                    meta=response.meta,
                    errback=self.handle_error
                )
        except Exception as e:
            self.logger.error(f"Chyba při parsování seznamu: {e}")

    def parse_article(self, response):
        """Parsování jednotlivého článku s validací"""
        try:
            # Extrakce dat
            title = response.css("h1::text").get()
            content = response.css("div.article *::text").getall()
            full_text = " ".join([t.strip() for t in content if t.strip()])

            # Validace
            if not all([title, full_text]):
                self.logger.warning(f"Nekompletní data v článku: {response.url}")
                return

            # Výstup ve formátu kompatibilním s DB schématem
            yield {
                "source_name": response.meta.get('source_name', 'Pastorace.cz'),
                "source_type": response.meta.get('source_type', 'Náboženský web'),
                "title": title.strip(),
                "url": response.url,
                "text": full_text,
                "scraped_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Chyba při parsování článku {response.url}: {e}")

    def handle_error(self, failure):
        """Zpracování chyb při stahování"""
        self.logger.error(f"Chyba při stahování {failure.request.url}: {failure.value}")
