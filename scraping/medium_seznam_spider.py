import scrapy
import datetime
from scraping.keywords import contains_relevant_keywords, is_excluded_content

class MediumSeznamSpider(scrapy.Spider):
    """
    Spider pro scraping článků z Medium.seznam.cz týkajících se náboženských hnutí.
    """
    name = "medium_seznam"
    allowed_domains = ["medium.seznam.cz"]
    start_urls = ["https://medium.seznam.cz/"]

    custom_settings = {
        "FEEDS": {
            "export/csv/medium_seznam_raw.csv": {
                "format": "csv",
                "overwrite": True,
                "encoding": "utf8",
                "fields": ["source_name", "source_type", "title", "url", "text", "scraped_at"]
            }
        },
        "ROBOTSTXT_OBEY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,  # Více etický start delay
        "AUTOTHROTTLE_MAX_DELAY": 10.0,   # Větší max delay pro lepší rozložení requestů
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "DOWNLOAD_DELAY": 3,  # Základní delay mezi requesty
        "LOG_LEVEL": "INFO",
        "USER_AGENT": "Mozilla/5.0 (compatible; ProjectInfinit/1.0; +https://github.com/yourusername/project_infinit)"
    }

    def parse(self, response):
        """Prochází seznam článků a následuje relevantní odkazy."""
        articles = response.css("article")
        for article in articles:
            title = article.css("h3::text").get() or ""
            link = article.css("a::attr(href)").get()
            
            # Přeskočíme články, které zjevně nejsou relevantní
            if not contains_relevant_keywords(title) or is_excluded_content(title):
                continue
                
            if link:
                yield response.follow(link, callback=self.parse_article)

        # Následuj další stránku, pokud existuje
        next_page = response.css("a.pagination__next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_article(self, response):
        """Extrahuje data z článku a kontroluje relevanci obsahu."""
        title = response.css("h1::text").get() or ""
        text = " ".join(response.css("article p::text").getall()).strip()
        
        # Přeskočíme články, které po přečtení nejsou relevantní
        if not contains_relevant_keywords(text) or is_excluded_content(text):
            return
            
        # Extrahuj metadata
        author = response.css("span.author-name::text").get() or "Unknown"
        date_published = response.css("time::attr(datetime)").get()
        
        yield {
            "source_name": "medium.seznam.cz",
            "source_type": "web",
            "title": title,
            "url": response.url,
            "text": text,
            "scraped_at": datetime.datetime.now().isoformat(),
            "author": author,
            "date_published": date_published
        }
