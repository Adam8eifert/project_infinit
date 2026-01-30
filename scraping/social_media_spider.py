# Compatibility shim to expose `scraping.social_media_spider` import path.
# Re-export the main symbols so tests and older code can patch module-level
# functions/attributes (e.g., get_config_loader, praw, contains_relevant_keywords).
from extracting.social_media_spider import RedditSpider, XTwitterSpider, contains_relevant_keywords
from config_loader import get_config_loader
import praw

__all__ = ["RedditSpider", "XTwitterSpider", "get_config_loader", "contains_relevant_keywords", "praw"]

