import scrapy
import datetime
from extracting.keywords import contains_relevant_keywords, is_excluded_content

class MediumSeznamSpider(scrapy.Spider):
    """
    Spider for scraping articles from Medium.seznam.cz related to religious movements.
    """
    name = "medium_seznam"
    SOURCE_KEY = "medium_seznam"
    allowed_domains = ["medium.seznam.cz"]
    start_urls = ["https://medium.seznam.cz/"]

    # Base settings — FEEDS will be set dynamically in __init__ to honor config
    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 2.0,  # More ethical start delay
        "AUTOTHROTTLE_MAX_DELAY": 10.0,   # Larger max delay for better request distribution
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
        "DOWNLOAD_DELAY": 3,  # Base delay between requests
        "LOG_LEVEL": "INFO",
        "USER_AGENT": "Mozilla/5.0 (compatible; ProjectInfinit/1.0; +https://github.com/yourusername/project_infinit)"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set FEEDS based on sources_config.yaml
        try:
            from .csv_utils import get_output_csv_for_source, ensure_csv_header
            out = str(get_output_csv_for_source(self.SOURCE_KEY))
            ensure_csv_header(get_output_csv_for_source(self.SOURCE_KEY))
            # Use explicit dict copy to satisfy static type checkers
            new_settings = dict(self.custom_settings)
            new_settings['FEEDS'] = {out: {"format": "csv", "overwrite": True, "encoding": "utf8"}}
            self.custom_settings = new_settings
        except Exception:
            # If config missing, fall back to default static path
            new_settings = dict(self.custom_settings)
            new_settings['FEEDS'] = {"export/csv/medium_seznam_raw.csv": {"format": "csv", "overwrite": True, "encoding": "utf8"}}
            self.custom_settings = new_settings

    def parse(self, response):
        """Browses article list and follows relevant links."""
        articles = response.css("article")
        for article in articles:
            title = article.css("h3::text").get() or ""
            link = article.css("a::attr(href)").get()
            
            # Skip articles that are obviously not relevant
            if not contains_relevant_keywords(title) or is_excluded_content(title):
                continue
                
            if link:
                yield response.follow(link, callback=self.parse_article)

        # Follow next page if it exists
        next_page = response.css("a.pagination__next::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_article(self, response):
        """Extracts data from article and checks content relevance."""
        title = response.css("h1::text").get() or ""
        text = " ".join(response.css("article p::text").getall()).strip()
        
        # Skip articles that are not relevant after reading
        if not contains_relevant_keywords(text) or is_excluded_content(text):
            return
            
        # Extract metadata
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
