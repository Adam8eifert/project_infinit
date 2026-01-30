# Ensure tests can import top-level modules like `extracting` and `scraping`.
# This adds the repository root to sys.path at test collection time.
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
