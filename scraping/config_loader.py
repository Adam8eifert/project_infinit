# Compatibility shim to expose the old import path `scraping.config_loader`.
# New code lives in `extracting.config_loader` — re-export the loader here to
# avoid updating many call sites and tests.
from extracting.config_loader import SourcesConfigLoader

__all__ = ["SourcesConfigLoader"]
