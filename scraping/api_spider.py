# 📁 scraping/api_spider.py
# Univerzální spider pro API zdroje (MediaWiki, REST API, atd.)
# Dynamicky čte konfiguraci ze sources_config.yaml

import scrapy
import json
from datetime import datetime
from scraping.config_loader import get_config_loader
from scraping.keywords import contains_relevant_keywords


class APISpider(scrapy.Spider):
    """
    Univerzální spider pro API zdroje.
    Podporuje MediaWiki API a ostatní REST API.
    """
    name = "api_universal"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_loader = get_config_loader()
        self.sources = self._get_api_sources()
        self.logger.info(f"🔌 Inicializuji API spider s {len(self.sources)} zdroji")
    
    def _get_api_sources(self):
        """Vrátí seznam všech povolených API zdrojů z konfigurace."""
        all_sources = self.config_loader.get_enabled_sources()
        api_sources = {
            key: source for key, source in all_sources.items()
            if source.get('type') == 'api' and source.get('enabled', True)
        }
        return api_sources
    
    def start_requests(self):
        """Generuje požadavky pro každý API endpoint."""
        for source_key, source_config in self.sources.items():
            api_url = source_config.get('url')
            api_params = source_config.get('api_params', {})
            
            if api_url:
                self.logger.info(f"🔗 Zpracovávám API: {source_config['name']} ({api_url})")
                
                # Přidej parametry do URL
                params_str = '&'.join([f"{k}={v}" for k, v in api_params.items()])
                full_url = f"{api_url}?{params_str}" if params_str else api_url
                
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_api,
                    meta={
                        'source_key': source_key,
                        'source_config': source_config,
                        'source_name': source_config['name'],
                        'output_csv': source_config.get('output_csv', 'export/csv/api_raw.csv')
                    },
                    errback=self.handle_error
                )
    
    def parse_api(self, response):
        """
        Parsuje API odpověď (JSON).
        Extrahuje relevantní obsah a ukládá do CSV.
        """
        try:
            data = json.loads(response.text)
            source_config = response.meta['source_config']
            api_method = source_config.get('api_method', 'parse')
            
            self.logger.info(f"📄 Zpracovávám API odpověď pro {response.meta['source_name']}")
            
            # Zpracování podle API metody
            if api_method == 'parse' and 'parse' in data:
                # MediaWiki API response
                parse_data = data['parse']
                title = parse_data.get('title', '')
                
                # Extrakce textu
                wikitext = parse_data.get('wikitext', '')
                if isinstance(wikitext, dict):
                    wikitext = wikitext.get('*', '')
                
                # Kategorie
                categories = [cat.get('*', '') for cat in parse_data.get('categories', [])]
                
                # Kontrola relevance
                if contains_relevant_keywords(wikitext):
                    yield {
                        'source_name': response.meta['source_name'],
                        'source_type': 'API',
                        'title': title,
                        'url': response.url,
                        'text': wikitext[:5000],  # Omezit délku
                        'scraped_at': datetime.utcnow().isoformat(),
                        'categories': categories
                    }
            
            elif api_method == 'query' and 'query' in data:
                # Jiný MediaWiki API response
                query_data = data['query']
                pages = query_data.get('pages', {})
                
                for page_id, page_data in pages.items():
                    title = page_data.get('title', '')
                    text = page_data.get('extract', '')
                    
                    if contains_relevant_keywords(text):
                        yield {
                            'source_name': response.meta['source_name'],
                            'source_type': 'API',
                            'title': title,
                            'url': response.url,
                            'text': text,
                            'scraped_at': datetime.utcnow().isoformat()
                        }
        
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Chyba při parsování JSON: {e}")
        except Exception as e:
            self.logger.error(f"❌ Chyba při zpracování API: {e}")
    
    def handle_error(self, failure):
        """Zpracování chyb při API požadavku."""
        request = failure.request
        source_name = request.meta.get('source_name', 'Unknown')
        self.logger.error(f"❌ Chyba při API požadavku na {source_name}: {failure.value}")


# Alternativní spider pro jednotlivý API zdroj
class SingleAPISpider(scrapy.Spider):
    """Spider pro spuštění jednoho konkrétního API."""
    name = "api_single"
    
    def __init__(self, source_key='soccas', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_key = source_key
        config_loader = get_config_loader()
        self.source_config = config_loader.get_source(source_key)
        
        if not self.source_config:
            raise ValueError(f"Zdroj '{source_key}' nenalezen v konfiguraci")
        
        if self.source_config.get('type') != 'api':
            raise ValueError(f"Zdroj '{source_key}' není typu API")
        
        # At this point, source_config is guaranteed to be not None
        assert self.source_config is not None
    
    def start_requests(self):
        """Generuje požadavek pro API."""
        api_url = self.source_config.get('url')  # type: ignore
        if not api_url:
            self.logger.error(f"No URL configured for source {self.source_config.get('name', 'Unknown')}")  # type: ignore
            return
            
        api_params = self.source_config.get('api_params', {})  # type: ignore
        
        params_str = '&'.join([f"{k}={v}" for k, v in api_params.items()])
        full_url = f"{api_url}?{params_str}" if params_str else api_url
        
        yield scrapy.Request(
            full_url,
            callback=self.parse,
            meta={
                'source_config': self.source_config,  # type: ignore
                'source_name': self.source_config['name']  # type: ignore
            }
        )
    
    def parse(self, response):
        """Totéž jako APISpider.parse_api."""
        try:
            data = json.loads(response.text)
            
            if 'parse' in data:
                parse_data = data['parse']
                title = parse_data.get('title', '')
                wikitext = parse_data.get('wikitext', '')
                if isinstance(wikitext, dict):
                    wikitext = wikitext.get('*', '')
                categories = [cat.get('*', '') for cat in parse_data.get('categories', [])]
                
                if contains_relevant_keywords(wikitext):
                    yield {
                        'source_name': response.meta['source_name'],
                        'source_type': 'API',
                        'title': title,
                        'url': response.url,
                        'text': wikitext[:5000],
                        'scraped_at': datetime.utcnow().isoformat(),
                        'categories': categories
                    }
        except Exception as e:
            self.logger.error(f"❌ Chyba při zpracování API: {e}")
