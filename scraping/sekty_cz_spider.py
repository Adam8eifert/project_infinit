# 📁 scraping/sekty_cz_spider.py
# Scrapy spider pro sekty.cz - specializovaný web o náboženských hnutích

import scrapy
from datetime import datetime
import re
from .spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS
from .keywords import contains_relevant_keywords, KNOWN_MOVEMENTS, YEAR_PATTERNS

class SektyCZSpider(scrapy.Spider):
    name = "sekty_cz"
    allowed_domains = ["sekty.cz"]
    start_urls = ["https://sekty.cz/prehled"]

    # Kombinace etického nastavení s vlastním nastavením
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "FEEDS": {
            "export/csv/sekty_cz_raw.csv": CSV_EXPORT_SETTINGS
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
                    'source_name': 'Sekty.cz',
                    'source_type': 'Informační web'
                }
            )

    def parse(self, response):
        """Parsování seznamu článků s předběžným filtrováním."""
        try:
            articles = response.css("div.tdb_module_loop article")
            for article in articles:
                title = article.css("h3 a::text").get()
                excerpt = article.css("div.td-excerpt::text").get()
                url = article.css("h3 a::attr(href)").get()
                
                # Předběžná kontrola relevance
                if title and url:
                    combined_text = f"{title} {excerpt or ''}"
                    if contains_relevant_keywords(combined_text) or any(mov.lower() in combined_text.lower() for mov in KNOWN_MOVEMENTS):
                        yield response.follow(
                            url,
                            callback=self.parse_article,
                            meta={
                                **response.meta,
                                'title': title,
                                'excerpt': excerpt
                            },
                            errback=self.handle_error
                        )
        except Exception as e:
            self.logger.error(f"Chyba při parsování seznamu: {e}")

    def parse_article(self, response):
        """Parsování jednotlivého článku s rozšířenou extrakcí dat."""
        try:
            # Základní extrakce
            title = response.meta.get('title') or response.css("h1.entry-title::text").get()
            content = response.css("div.td-post-content p::text, div.td-post-content li::text").getall()
            full_text = " ".join([t.strip() for t in content if t.strip()])
            
            # Metadata
            author = response.css(".td-post-author-name a::text").get() or "Neznámý"
            date_str = response.css(".td-post-date time::attr(datetime)").get()
            categories = response.css(".td-category a::text").getall()
            tags = response.css("ul.td-tags li a::text").getall()
            
            # Extrakce roku založení
            year_founded = None
            for pattern in YEAR_PATTERNS:
                match = re.search(pattern, full_text)
                if match:
                    year_founded = match.group(1)
                    break

            # Validace
            if not all([title, full_text]):
                self.logger.warning(f"Nekompletní data v článku: {response.url}")
                return
            
            # Kontrola relevance celého textu
            if not contains_relevant_keywords(full_text):
                self.logger.info(f"Článek není relevantní: {response.url}")
                return

            # Výstup ve formátu kompatibilním s DB schématem
            yield {
                "source_name": response.meta.get('source_name', 'Sekty.cz'),
                "source_type": response.meta.get('source_type', 'Informační web'),
                "title": title.strip(),
                "url": response.url,
                "text": full_text,
                "scraped_at": datetime.utcnow().isoformat(),
                "author": author.strip(),
                "published_at": date_str,
                "categories": categories,
                "tags": tags,
                "excerpt": response.meta.get('excerpt', ''),
                "year_founded": year_founded
            }
        except Exception as e:
            self.logger.error(f"Chyba při parsování článku {response.url}: {e}")

    def handle_error(self, failure):
        """Podrobné zpracování chyb při stahování."""
        request = failure.request
        self.logger.error(f"Chyba při stahování {request.url}: {failure.value}")
        self.logger.error(f"Headers: {request.headers}")
        self.logger.error(f"Meta: {request.meta}")
