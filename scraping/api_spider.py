# Compatibility shim for `scraping.api_spider` used by tests.
# This module forwards key function lookups to the shim namespace so tests
# can monkeypatch functions like `get_config_loader` and
# `contains_relevant_keywords` via `scraping.api_spider`.
import importlib
import sys

_impl = importlib.import_module('extracting.api_spider')

# Forwarding wrappers consult the shim module (this module) first so
# monkeypatching `scraping.api_spider.X` will affect behavior inside the
# underlying implementation.

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

# Patch the implementation module so its functions call through our wrappers
_impl.get_config_loader = _get_config_loader_wrapper
_impl.contains_relevant_keywords = _contains_relevant_keywords_wrapper

# Finally re-export public symbols from the implementation for compatibility
from extracting.api_spider import *  # type: ignore
