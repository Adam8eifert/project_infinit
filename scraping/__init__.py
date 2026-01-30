# Compatibility shim for older imports referencing `scraping` package.
# Prefer using `extracting` package going forward.
# Be defensive: avoid raising if `extracting` is not importable at import time.
try:
    from extracting.keywords import *  # noqa: F401,F403
except Exception:
    # If extracting package is not available on import (e.g., tests running in
    # isolated environments), provide a harmless fallback to allow test
    # discovery to proceed. Specific shims (e.g., scraping.config_loader)
    # should import the concrete implementations when needed.
    __all__ = []
