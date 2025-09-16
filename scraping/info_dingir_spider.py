# 📁 scraping/info_dingir_spider.py
import scrapy
import datetime

class InfoDingirSpider(scrapy.Spider):
    name = "info_dingir"
    allowed_domains = ["info.dingir.cz"]
    start_urls = ["https://info.dingir.cz/"]

    custom_settings = {
        "FEEDS": {
            "export/csv/info_dingir_raw.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8",
            }
        },
        "LOG_LEVEL": "INFO",
        # --- Zde přidáváme nastavení ---
        "AUTOTHROTTLE_ENABLED": True,
        # Minimální zpoždění, které AutoThrottle bude respektovat (ve vteřinách)
        "AUTOTHROTTLE_START_DELAY": 0.5,
        # Maximální zpoždění, které AutoThrottle může použít (ve vteřinách)
        "AUTOTHROTTLE_MAX_DELAY": 60,
        # Průměrný počet současných požadavků, které Scrapy odesílá na doménu
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,
        # Zapni si AutoThrottle debugging pro lepší přehled v logu
        "AUTOTHROTTLE_DEBUG": False,
        # --- Konec nastavení ---
    }

    def parse(self, response):
        articles = response.css("article")
        for article in articles:
            url = article.css("h2.entry-title a::attr(href)").get()
            if url:
                yield response.follow(url, callback=self.parse_article)

        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_article(self, response):
        title = response.css("h1.entry-title::text").get()
        paragraphs = response.css("div.entry-content p::text").getall()
        full_text = " ".join(p.strip() for p in paragraphs if p.strip())

        date_str = response.css("time.entry-date::attr(datetime)").get()
        date = None
        if date_str:
            try:
                date = datetime.datetime.fromisoformat(date_str)
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