# 📁 scraping/rss_spider.py
# Univerzální Scrapy spider pro RSS/Atom feedy
# Dynamicky čte konfiguraci ze sources_config.yaml

import scrapy
import feedparser
from datetime import datetime
from pathlib import Path
from scraping.config_loader import get_config_loader
from scraping.keywords import contains_relevant_keywords


class RSSSpider(scrapy.Spider):
    """
    Univerzální spider pro parsování RSS/Atom feedů.
    Čte konfiguraci z sources_config.yaml a zpracovává všechny RSS zdroje.
    """
    name = "rss_universal"
    allowed_domains = []
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.sources = self._get_rss_sources()
        self.logger.info(f"📡 Inicializuji RSS spider s {len(self.sources)} zdroji")
    
    def _get_rss_sources(self):
        """Vrátí seznam všech povolených RSS zdrojů z konfigurace."""
        all_sources = self.config_loader.get_enabled_sources()
        rss_sources = {
            key: source for key, source in all_sources.items()
            if source.get('type') == 'rss' and source.get('enabled', True)
        }
        return rss_sources
    
    def start_requests(self):
        """Generuje požadavky pro každý RSS feed."""
        for source_key, source_config in self.sources.items():
            feed_url = source_config.get('url')
            if feed_url:
                self.logger.info(f"🔗 Zpracovávám RSS feed: {source_config['name']} ({feed_url})")
                yield scrapy.Request(
                    feed_url,
                    callback=self.parse_rss,
                    meta={
                        'source_key': source_key,
                        'source_config': source_config,
                        'source_name': source_config['name'],
                        'source_type': source_config.get('source_type', 'RSS'),
                        'output_csv': source_config.get('output_csv', 'export/csv/rss_raw.csv')
                    },
                    errback=self.handle_error
                )
    
    def parse_rss(self, response):
        """
        Parsuje RSS/Atom feed pomocí feedparser.
        Extrahuje články a ukládá do CSV.
        """
        try:
            # Parsuj RSS obsah
            feed = feedparser.parse(response.text)
            source_config = response.meta['source_config']
            selectors = source_config.get('selectors', {})
            
            self.logger.info(f"📰 Nalezeno {len(feed.entries)} položek v {response.meta['source_name']}")
            
            for entry in feed.entries:
                # Extrakce dat z RSS položky
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                # Obsah - zkušíme více polí
                content = entry.get('content', [{}])[0].get('value', '')
                if not content:
                    content = entry.get('summary', '')
                if not content:
                    content = entry.get('description', '')
                
                # Autor
                author = entry.get('author', 'Unknown')
                if isinstance(author, dict):
                    author = author.get('name', 'Unknown')
                
                # Datum publikace
                date_published = entry.get('published', '')
                
                # Kategorie
                categories = [tag.get('term', '') for tag in entry.get('tags', [])]
                
                # Kontrola relevance
                combined_text = f"{title} {content}"
                if not contains_relevant_keywords(combined_text):
                    self.logger.debug(f"⏭️  Článek není relevantní: {title}")
                    continue
                
                # Výstup
                yield {
                    'source_name': response.meta['source_name'],
                    'source_type': response.meta['source_type'],
                    'title': title.strip(),
                    'url': link,
                    'text': content.strip(),
                    'scraped_at': datetime.utcnow().isoformat(),
                    'author': author.strip(),
                    'published_at': date_published,
                    'categories': categories
                }
        
        except Exception as e:
            self.logger.error(f"❌ Chyba při parsování RSS: {e}")
    
    def handle_error(self, failure):
        """Zpracování chyb při stahování feedu."""
        request = failure.request
        source_name = request.meta.get('source_name', 'Unknown')
        self.logger.error(f"❌ Chyba při stahování {source_name}: {failure.value}")


# Alternativní spider pro jednotlivý zdroj (pokud potřebujete spustit konkrétní RSS)
class SingleRSSSpider(scrapy.Spider):
    """Spider pro spuštění jednoho konkrétního RSS feedu."""
    name = "rss_single"
    
    def __init__(self, source_key='sekty_cz', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_key = source_key
        config_loader = get_config_loader()
        self.source_config = config_loader.get_source(source_key)
        
        if not self.source_config:
            raise ValueError(f"Zdroj '{source_key}' nenalezen v konfiguraci")
        
        if self.source_config.get('type') != 'rss':
            raise ValueError(f"Zdroj '{source_key}' není typu RSS")
        
        self.allowed_domains = [self.source_config.get('domain', '')]
        self.start_urls = [self.source_config.get('url', '')]
    
    def parse(self, response):
        """Totéž jako RSSSpider.parse_rss."""
        try:
            feed = feedparser.parse(response.text)
            self.logger.info(f"📰 Nalezeno {len(feed.entries)} položek")
            
            for entry in feed.entries:
                title = entry.get('title', '')
                link = entry.get('link', '')
                content = entry.get('content', [{}])[0].get('value', '') or entry.get('summary', '')
                author = entry.get('author', 'Unknown')
                date_published = entry.get('published', '')
                categories = [tag.get('term', '') for tag in entry.get('tags', [])]
                
                combined_text = f"{title} {content}"
                if not contains_relevant_keywords(combined_text):
                    continue
                
                yield {
                    'source_name': self.source_config['name'],
                    'source_type': 'RSS',
                    'title': title.strip(),
                    'url': link,
                    'text': content.strip(),
                    'scraped_at': datetime.utcnow().isoformat(),
                    'author': author.strip(),
                    'published_at': date_published,
                    'categories': categories
                }
        
        except Exception as e:
            self.logger.error(f"❌ Chyba při parsování RSS: {e}")
