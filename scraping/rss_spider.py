# Compatibility shim for `scraping.rss_spider` used by tests.
# This shim sets small forwarding wrappers so tests can monkeypatch
# `get_config_loader` and `contains_relevant_keywords` on the
# `scraping.rss_spider` module and have those patches affect the
# underlying implementation in `extracting.rss_spider`.
import importlib
import sys

_impl = importlib.import_module('extracting.rss_spider')


def _get_config_loader_wrapper(*args, **kwargs):
    fn = getattr(sys.modules[__name__], 'get_config_loader', None)
    if fn:
        return fn(*args, **kwargs)
    return _impl.get_config_loader(*args, **kwargs)


def _contains_relevant_keywords_wrapper(text, *args, **kwargs):
    fn = getattr(sys.modules[__name__], 'contains_relevant_keywords', None)
    if fn:
        return fn(text, *args, **kwargs)
    return _impl.contains_relevant_keywords(text, *args, **kwargs)

_impl.get_config_loader = _get_config_loader_wrapper
_impl.contains_relevant_keywords = _contains_relevant_keywords_wrapper

from extracting.rss_spider import *  # type: ignore
