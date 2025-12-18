# 📁 scraping/config_loader.py
# Načítání a správa konfigurace zdrojů z YAML

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class SourcesConfigLoader:
    """Nahraje a zpracuje konfiguraci zdrojů ze YAML souboru."""
    
    def __init__(self, config_path: str = "scraping/sources_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Any:
        """Načte YAML konfiguraci."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Konfiguační soubor nenalezen: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_all_sources(self) -> Dict[str, Any]:
        """Vrátí všechny zdroje."""
        return self.config.get('sources', {})
    
    def get_enabled_sources(self) -> Dict[str, Any]:
        """Vrátí pouze povolené zdroje."""
        return {
            key: source
            for key, source in self.config.get('sources', {}).items()
            if source.get('enabled', True)
        }
    
    def get_source(self, source_key: str) -> Optional[Dict[str, Any]]:
        """Vrátí konfiguraci konkrétního zdroje."""
        return self.config.get('sources', {}).get(source_key)
    
    def get_scraping_settings(self) -> Dict[str, Any]:
        """Vrátí globální nastavení scrapingu."""
        return self.config.get('scraping_settings', {})
    
    def get_content_filters(self) -> Dict[str, Any]:
        """Vrátí filtry obsahu."""
        return self.config.get('content_filters', {})
    
    def get_source_urls(self) -> Dict[str, str]:
        """Vrátí všechny URL zdroje (jméno -> URL)."""
        return {
            key: source.get('url', '')
            for key, source in self.config.get('sources', {}).items()
            if source.get('enabled', True)
        }
    
    def get_source_list_as_table(self) -> List[Dict[str, Any]]:
        """Vrátí seznam zdrojů ve formátu tabulky."""
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
            print(f"    Doména: {source.get('domain', 'N/A')}")
            print(f"    Typ: {source.get('type', 'web')}")
            print()


# Jednoduchá globální instance pro snadný přístup
_default_loader = None


def get_config_loader(config_path: str = "scraping/sources_config.yaml") -> SourcesConfigLoader:
    """Vrátí nebo vytvoří globální instanci loaderu."""
    global _default_loader
    if _default_loader is None:
        _default_loader = SourcesConfigLoader(config_path)
    return _default_loader


if __name__ == "__main__":
    loader = SourcesConfigLoader()
    print("✅ Konfigurace úspěšně načtena")
    print(f"Celkem zdrojů: {len(loader.get_all_sources())}")
    print(f"Povolených zdrojů: {len(loader.get_enabled_sources())}")
    loader.print_enabled_sources()
