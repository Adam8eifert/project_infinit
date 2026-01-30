# Compatibility shim: re-export extracting.keywords to avoid requiring code changes
# in tests or external imports that still use `scraping.keywords`.

from extracting.keywords import *  # noqa: F401,F403
