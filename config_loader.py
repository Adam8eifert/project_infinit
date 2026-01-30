"""Top-level shim for backwards-compatible imports.
Exports the primary config loader from `extracting.config_loader` so code that
imports `config_loader` continues to work.
"""
from extracting.config_loader import get_config_loader, SourcesConfigLoader

__all__ = ["get_config_loader", "SourcesConfigLoader"]
