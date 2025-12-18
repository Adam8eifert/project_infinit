# 📁 scraping/wikipedia_spider.py
# Wikipedia API místo přímého scrapingu - etičtější přístup s filtrováním

import scrapy
import json
import re
from datetime import datetime
from urllib.parse import urlencode, unquote
from .spider_settings import ETHICAL_SCRAPING_SETTINGS, CSV_EXPORT_SETTINGS
from .keywords import contains_relevant_keywords, KNOWN_MOVEMENTS, YEAR_PATTERNS

class WikipediaSpider(scrapy.Spider):
    name = "wikipedia"
    allowed_domains = ["cs.wikipedia.org"]
    api_url = "https://cs.wikipedia.org/w/api.php"
    
    # Kombinace etického nastavení s vlastním nastavením pro API
    custom_settings = {
        **ETHICAL_SCRAPING_SETTINGS,
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 3,  # Vyšší zpoždění pro Wikipedia API
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "FEEDS": {
            "export/csv/wikipedia_raw.csv": CSV_EXPORT_SETTINGS
        },
        "LOG_LEVEL": "INFO"
    }

    def start_requests(self):
        """Inicializace API requestu s meta daty"""
        params = {
            "action": "parse",
            "page": "Seznam_církví_a_náboženských_společností_v_Česku",
            "format": "json",
            "prop": "wikitext",
            "formatversion": 2
        }
        
        url = f"{self.api_url}?{urlencode(params)}"
        yield scrapy.Request(
            url=url,
            callback=self.parse_api,
            meta={
                'source_name': 'Wikipedia',
                'source_type': 'Encyklopedie',
                'base_url': 'https://cs.wikipedia.org/wiki/'
            },
            errback=self.handle_error
        )

    def parse_api(self, response):
        """Parsování API odpovědi a extrakce seznamu náboženských skupin."""
        try:
            data = json.loads(response.text)
            if 'parse' in data and 'wikitext' in data['parse']:
                wikitext = data['parse']['wikitext']
                
                # Hledáme názvy skupin v wikitextu
                movement_matches = re.finditer(r"\[\[(.*?)\]\]", wikitext)
                for match in movement_matches:
                    page_name = match.group(1).split('|')[0]  # Bere první část před |
                    if any(mov.lower() in page_name.lower() for mov in KNOWN_MOVEMENTS):
                        params = {
                            "action": "query",
                            "titles": page_name,
                            "prop": "extracts|categories|info",
                            "exintro": True,
                            "explaintext": True,
                            "format": "json",
                            "formatversion": 2,
                            "inprop": "url"
                        }
                        api_url = f"{self.api_url}?{urlencode(params)}"
                        yield scrapy.Request(
                            url=api_url,
                            callback=self.parse_movement,
                            meta={
                                **response.meta,
                                'movement_name': page_name
                            },
                            errback=self.handle_error
                        )
        except Exception as e:
            self.logger.error(f"Chyba při parsování API odpovědi: {e}")
            
    def parse_movement(self, response):
        """Zpracování detailů o náboženském hnutí."""
        try:
            data = json.loads(response.text)
            pages = data.get('query', {}).get('pages', [])
            if not pages:
                return
                
            page = pages[0]  # Ve formatversion 2 dostáváme pole
            if 'missing' in page:
                return
                
            title = page.get('title', '')
            text = page.get('extract', '')
            categories = [cat.get('title', '') for cat in page.get('categories', [])]
            
            # Extrakce roku založení
            year_founded = None
            for pattern in YEAR_PATTERNS:
                match = re.search(pattern, text)
                if match:
                    year_founded = match.group(1)
                    break
                    
            # Kontrola relevance
            if not contains_relevant_keywords(text):
                return
                
            yield {
                'source_name': response.meta.get('source_name', 'Wikipedia'),
                'source_type': response.meta.get('source_type', 'Encyklopedie'),
                'title': title,
                'url': page.get('canonicalurl', ''),
                'text': text,
                'scraped_at': datetime.utcnow().isoformat(),
                'categories': categories,
                'year_founded': year_founded,
                'movement_name': response.meta.get('movement_name'),
                'last_modified': page.get('touched')
            }
        except Exception as e:
            self.logger.error(f"Chyba při parsování detailů hnutí: {e}")
            
    def handle_error(self, failure):
        """Rozšířené logování chyb API požadavků."""
        request = failure.request
        self.logger.error(f"Chyba API požadavku na {request.url}: {failure.value}")
        self.logger.error(f"Headers: {request.headers}")
        self.logger.error(f"Meta: {request.meta}")
        if hasattr(failure.value, 'response') and failure.value.response:
            self.logger.error(f"Response body: {failure.value.response.body}")
