"""
Basic settings for all spiders - ensures ethical scraping
"""
import random

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
]

# Basic settings for ethical scraping
ETHICAL_SCRAPING_SETTINGS = {
    # Respect robots.txt
    "ROBOTSTXT_OBEY": True,
    
    # Bot identification
    "USER_AGENT": random.choice(USER_AGENTS),
    
    # Delay between requests
    "DOWNLOAD_DELAY": 2,  # basic 2 seconds between requests
    "RANDOMIZE_DOWNLOAD_DELAY": True,
    
    # Autothrottle - automatic speed adjustment
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 1,
    "AUTOTHROTTLE_MAX_DELAY": 60,
    "AUTOTHROTTLE_TARGET_CONCURRENCY": 1.0,
    
    # Cache - reduce server load
    "HTTPCACHE_ENABLED": True,
    "HTTPCACHE_EXPIRATION_SECS": 86400,  # 24 hours
    
    # Limits
    "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
    "CONCURRENT_REQUESTS": 1,
    
    # Cookies
    "COOKIES_ENABLED": False,
    
    # Retry on errors
    "RETRY_ENABLED": True,
    "RETRY_TIMES": 3,
    "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
}

# CSV export settings
CSV_EXPORT_SETTINGS = {
    "format": "csv",
    "overwrite": True,
    "encoding": "utf8",
}