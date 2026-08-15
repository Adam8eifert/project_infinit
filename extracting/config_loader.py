# 📁 extracting/config_loader.py
# Loading and managing source configuration from YAML

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class SourcesConfigLoader:
    """Load and process source configuration from YAML file."""
    
    def __init__(self, config_path: str = "extracting/sources_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Any:
        """Load YAML configuration."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_all_sources(self) -> Dict[str, Any]:
        """Return all sources."""
        return self.config.get('sources', {})
    
    def get_enabled_sources(self) -> Dict[str, Any]:
        """Return only enabled sources."""
        return {
            key: source
            for key, source in self.config.get('sources', {}).items()
            if source.get('enabled', True)
        }
    
    def get_source(self, source_key: str) -> Optional[Dict[str, Any]]:
        """Return configuration of specific source."""
        return self.config.get('sources', {}).get(source_key)
    
    def get_scraping_settings(self) -> Dict[str, Any]:
        """Return global scraping settings."""
        return self.config.get('scraping_settings', {})
    
    def get_content_filters(self) -> Dict[str, Any]:
        """Return content filters."""
        return self.config.get('content_filters', {})
    
    def get_sources_by_type(self, source_type: str) -> Dict[str, Any]:
        """Return sources matching a specific declared source type."""
        source_type = (source_type or '').strip().lower()
        return {
            key: source
            for key, source in self.get_all_sources().items()
            if str(source.get('type', '')).strip().lower() == source_type
        }

    def get_sources_by_acquisition(self, acquisition_method: str) -> Dict[str, Any]:
        """Return sources using a specific acquisition method from config."""
        acquisition_method = (acquisition_method or '').strip().lower()
        result = {}
        for key, source in self.get_all_sources().items():
            acquisition = source.get('acquisition') or {}
            if str(acquisition.get('method', '')).strip().lower() == acquisition_method:
                result[key] = source
        return result

    def get_source_acquisition(self, source_key: str) -> Dict[str, Any]:
        """Return acquisition settings for a specific source, if present."""
        source = self.get_source(source_key)
        return source.get('acquisition', {}) if source else {}

    def get_source_urls(self) -> Dict[str, str]:
        """Return all source URLs (name -> URL)."""
        return {
            key: source.get('url', '')
            for key, source in self.config.get('sources', {}).items()
            if source.get('enabled', True)
        }
    
    def get_source_list_as_table(self) -> List[Dict[str, Any]]:
        """Return list of sources in table format."""
        result = []
        for key, source in self.config.get('sources', {}).items():
            result.append({
                'key': key,
                'name': source.get('name', ''),
                'domain': source.get('domain', ''),
                'url': source.get('url', ''),
                'enabled': source.get('enabled', True),
                'type': source.get('type', 'web')
            })
        return result
    
    def is_source_enabled(self, source_key: str) -> bool:
        """Kontrola, zda je zdroj povolený."""
        source = self.get_source(source_key)
        return source.get('enabled', True) if source else False
    
    def toggle_source(self, source_key: str, enabled: bool):
        """Povolí/zakáže zdroj (bez uložení do souboru)."""
        if source_key in self.config.get('sources', {}):
            self.config['sources'][source_key]['enabled'] = enabled
    
    def add_custom_source(self, key: str, source_config: Dict[str, Any]):
        """Přidá nový zdroj do konfigurace (bez uložení do souboru)."""
        if 'sources' not in self.config:
            self.config['sources'] = {}
        self.config['sources'][key] = source_config
    
    def print_enabled_sources(self):
        """Vypíše všechny povolené zdroje."""
        print("\n📋 Povolené zdroje:\n")
        for key, source in self.get_enabled_sources().items():
            print(f"  • {source.get('name', key)}")
            print(f"    URL: {source.get('url', 'N/A')}")
            print(f"    Domain: {source.get('domain', 'N/A')}")
            print(f"    Type: {source.get('type', 'web')}")
            print()


# Simple global instance for easy access
_default_loader = None


def get_config_loader(config_path: str = "extracting/sources_config.yaml") -> SourcesConfigLoader:
    """Return or create global loader instance."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SourcesConfigLoader(config_path)
    return _default_loader


def _normalize_movement_entry(name: str, entry: Any) -> Dict[str, Any]:
    """Normalize flexible movement entry shapes into canonical dict.

    Supported input shapes (from YAML):
    - movements: { name: { aliases: [...], category: 'x', founded_year: 1990 } }
    - movements: { name: [alias1, alias2] }
    - legacy: known_movements + movement_aliases + movement_categories + founded_years
    """
    out = {
        'name': name,
        'aliases': [],
        'category': None,
        'founded_year': None,
    }
    try:
        if isinstance(entry, dict):
            # Expect possible keys: aliases, alias, category, founded_year, founded
            aliases = entry.get('aliases') or entry.get('alias') or []
            if isinstance(aliases, str):
                aliases = [aliases]
            out['aliases'] = aliases or []
            out['category'] = entry.get('category') or entry.get('movement_category')
            fy = entry.get('founded_year') or entry.get('founded')
            try:
                out['founded_year'] = int(fy) if fy is not None else None
            except Exception:
                out['founded_year'] = None
        elif isinstance(entry, list):
            out['aliases'] = entry
        elif isinstance(entry, str):
            out['aliases'] = [entry]
    except Exception:
        pass
    return out


class KeywordsAccessor:
    """Helper to access keywords-related structures from the loaded config.

    Provides compatibility with both the merged `keywords.movements` mapping
    and the legacy `known_movements` + `movement_aliases` layout.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config or {}

    def get_keywords(self) -> Dict[str, Any]:
        return self._config.get('keywords', {}) if isinstance(self._config.get('keywords', {}), dict) else {}

    def movements_map(self) -> Dict[str, Dict[str, Any]]:
        kw = self.get_keywords()
        # New merged layout: keywords.movements
        movements = kw.get('movements') if isinstance(kw.get('movements'), dict) else None
        result: Dict[str, Dict[str, Any]] = {}

        if movements:
            for name, entry in movements.items():
                normalized = _normalize_movement_entry(name, entry)
                result[name] = normalized
            return result

        # Fallback: legacy layout
        known_container = kw.get('known_movements', {}) if isinstance(kw.get('known_movements', {}), dict) else {}
        known_list = known_container.get('new_religious_movements') or []
        movement_aliases = kw.get('movement_aliases') if isinstance(kw.get('movement_aliases', {}), dict) else {}
        movement_categories = kw.get('movement_categories') if isinstance(kw.get('movement_categories', {}), dict) else {}
        founded_years = kw.get('founded_years') if isinstance(kw.get('founded_years', {}), dict) else {}

        for name in known_list:
            if not name:
                continue
            aliases = movement_aliases.get(name, []) or []
            result[name] = {
                'name': name,
                'aliases': aliases,
                'category': movement_categories.get(name),
                'founded_year': (int(founded_years.get(name)) if founded_years.get(name) is not None else None),
            }

        # Also ensure any movement explicitly declared in movement_aliases but missing from known_list is included
        for name, aliases in (movement_aliases or {}).items():
            if name not in result:
                result[name] = {
                    'name': name,
                    'aliases': aliases or [],
                    'category': movement_categories.get(name),
                    'founded_year': (int(founded_years.get(name)) if founded_years.get(name) is not None else None),
                }

        return result

    def person_aliases(self) -> Dict[str, List[str]]:
        kw = self.get_keywords()
        persons = kw.get('known_persons_aliases') if isinstance(kw.get('known_persons_aliases', {}), dict) else {}
        return persons


if __name__ == "__main__":
    loader = get_config_loader()
    print("✅ Configuration loaded successfully")
    ka = KeywordsAccessor(loader.config)
    movements_map = ka.movements_map()
    print(f"Movements definitions: {len(movements_map)}")


if __name__ == "__main__":
    loader = SourcesConfigLoader()
    print("✅ Configuration loaded successfully")
    print(f"Total sources: {len(loader.get_all_sources())}")
    print(f"Enabled sources: {len(loader.get_enabled_sources())}")
    loader.print_enabled_sources()
