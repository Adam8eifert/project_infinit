# Compatibility shim for scraping.idnes_spider
# Forwards to extracting.idnes_spider
import importlib
import sys

_impl = importlib.import_module('extracting.idnes_spider')

from extracting.idnes_spider import *  # type: ignore
