"""
Základní nastavení pro všechny spidery - zajišťuje etický scraping
"""
import random

# User agents pro rotaci
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

# Základní nastavení pro etický scraping
ETHICAL_SCRAPING_SETTINGS = {
    # Respektování robots.txt
    "ROBOTSTXT_OBEY": True,
    
    # Identifikace bota
    "USER_AGENT": random.choice(USER_AGENTS),
    
    # Zpoždění mezi požadavky
    "DOWNLOAD_DELAY": 2,  # základní 2 sekundy mezi requesty
    "RANDOMIZE_DOWNLOAD_DELAY": True,
    
    # Autothrottle - automatické přizpůsobení rychlosti
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 1,
    "AUTOTHROTTLE_MAX_DELAY": 60,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
    
    # Cache - snížení zátěže serveru
    "HTTPCACHE_ENABLED": True,
    "HTTPCACHE_EXPIRATION_SECS": 86400,  # 24 hodin
    
    # Limity
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    "CONCURRENT_REQUESTS": 1,
    
    # Cookies
    "COOKIES_ENABLED": False,
    
    # Retry při chybách
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 3,
    "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
}

# CSV export nastavení
CSV_EXPORT_SETTINGS = {
    "format": "csv",
    "overwrite": True,
    "encoding": "utf8",
}