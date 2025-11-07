# 📁 scraping/info_dingir_spider.py
import scrapy
from datetime import datetime
from .spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS
from .keywords import contains_relevant_keywords

class InfoDingirSpider(scrapy.Spider):
    name = "info_dingir"
    allowed_domains = ["info.dingir.cz"]
    start_urls = ["https://info.dingir.cz/"]

    # Spojení základního etického nastavení s nastavením pro tento spider
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "FEEDS": {
            "export/csv/info_dingir_raw.csv": CSV_EXPORT_SETTINGS
        },
        "LOG_LEVEL": "INFO"
    }

    def start_requests(self):
        """Přidává počáteční request s informací o zdroji v meta"""
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                meta={
                    'source_name': 'Dingir.cz',
                    'source_type': 'Odborný web'
                }
            )

    def parse(self, response):
        """Parsování seznamu článků s filtrováním podle klíčových slov"""
        articles = response.css("article")
        for article in articles:
            title = article.css("h2.entry-title a::text").get()
            url = article.css("h2.entry-title a::attr(href)").get()
            excerpt = article.css(".entry-summary p::text").get()
            
            # Kontrola relevance podle nadpisu a úryvku
            if contains_relevant_keywords(f"{title} {excerpt or ''}"):
                meta = {
                    **response.meta,
                    'title': title,
                    'excerpt': excerpt
                }
                yield response.follow(
                    url,
                    callback=self.parse_article,
                    meta=meta
                )

        # Stránkování s respektováním robots.txt
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(
                next_page,
                callback=self.parse,
                meta=response.meta
            )

    def parse_article(self, response):
        """Parsování článku s validací dat a kontrolou relevance."""
        try:
            # Extrakce základních dat
            title = response.meta.get('title') or response.css("h1.entry-title::text").get()
            paragraphs = response.css("div.entry-content p::text").getall()
            full_text = " ".join(p.strip() for p in paragraphs if p.strip())
            date_str = response.css("time.entry-date::attr(datetime)").get()
            author = response.css(".author-name::text, .byline::text").get() or "Neznámý"
            tags = response.css(".tags-links a::text").getall()

            # Validace povinných polí a relevance
            if not all([title, full_text, response.url]):
                self.logger.warning(f"Chybí povinná data v článku: {response.url}")
                return

            # Kontrola relevance celého textu
            if not contains_relevant_keywords(full_text):
                self.logger.info(f"Článek není relevantní: {response.url}")
                return

            # Zpracování data s fallbackem
            try:
                published_at = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S%z") if date_str else None
            except ValueError:
                published_at = None

            # Výstup ve formátu kompatibilním s DB schématem
            yield {
                'source_name': response.meta.get('source_name', 'Dingir.cz'),
                'source_type': response.meta.get('source_type', 'Odborný web'),
                'title': title.strip(),
                'url': response.url,
                'text': full_text,
                'scraped_at': datetime.utcnow().isoformat(),
                'published_at': published_at.isoformat() if published_at else None,
                'author': author.strip(),
                'tags': tags,
                'excerpt': response.meta.get('excerpt', '')
            }
            except ValueError:
                pass

        yield {
            "source_name": "info.dingir.cz",
            "source_type": "web",
            "title": title,
            "url": response.url,
            "text": full_text,
            "publication_date": date.isoformat() if date else None,
            "scraped_at": datetime.datetime.now().isoformat()
        }