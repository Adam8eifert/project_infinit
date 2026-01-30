# Compatibility shim for older imports referencing `scraping` package.
# Prefer using `extracting` package going forward.
from importlib import import_module

# Lazy import helper could be added here if needed.
_ex = import_module("extracting")

# Export commonly used symbols from extracting
from extracting.keywords import *  # noqa: F401,F403