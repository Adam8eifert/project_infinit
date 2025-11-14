# 📁 testing/test_config_loader.py
import pytest
from scraping.config_loader import SourcesConfigLoader


def test_config_loader_loads_yaml():
    """Test načtení konfigurace."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    assert loader.config is not None
    assert 'sources' in loader.config


def test_get_all_sources():
    """Test načtení všech zdrojů."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    sources = loader.get_all_sources()
    assert isinstance(sources, dict)
    assert len(sources) > 0
    # Ověřujeme, že máme očekávané zdroje
    assert 'sekty_tv' in sources
    assert 'sekty_cz' in sources
    assert 'google_news' in sources


def test_get_enabled_sources():
    """Test načtení pouze povolených zdrojů."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    enabled = loader.get_enabled_sources()
    # Všechny zdroje by měly být povoleny
    assert len(enabled) > 0
    for source in enabled.values():
        assert source.get('enabled', True) is True


def test_get_source():
    """Test načtení konkrétního zdroje."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    source = loader.get_source('sekty_cz')
    assert source is not None
    assert source['name'] == 'Sekty.cz'
    assert 'url' in source
    assert 'domain' in source


def test_get_source_urls():
    """Test export všech URL zdrojů."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    urls = loader.get_source_urls()
    assert isinstance(urls, dict)
    assert 'sekty_tv' in urls
    assert urls['sekty_tv'] == 'https://sekty.tv/'


def test_get_scraping_settings():
    """Test načtení globálních nastavení scrapingu."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    settings = loader.get_scraping_settings()
    assert isinstance(settings, dict)
    assert 'robots_txt_obey' in settings
    assert 'download_delay' in settings


def test_get_content_filters():
    """Test načtení filtrů obsahu."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    filters = loader.get_content_filters()
    assert isinstance(filters, dict)
    assert 'required_keywords' in filters
    assert 'exclude_keywords' in filters


def test_is_source_enabled():
    """Test kontroly, zda je zdroj povolený."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    assert loader.is_source_enabled('sekty_tv') is True
    assert loader.is_source_enabled('nonexistent') is False


def test_toggle_source():
    """Test povolení/zakázání zdroje."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    original_state = loader.is_source_enabled('sekty_tv')
    loader.toggle_source('sekty_tv', not original_state)
    assert loader.is_source_enabled('sekty_tv') == (not original_state)
    # Vrátíme původní stav
    loader.toggle_source('sekty_tv', original_state)


def test_add_custom_source():
    """Test přidání vlastního zdroje."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    custom_source = {
        'name': 'Test Source',
        'url': 'https://example.test/',
        'enabled': True
    }
    loader.add_custom_source('test_source', custom_source)
    assert loader.get_source('test_source') == custom_source


def test_source_list_as_table():
    """Test export zdrojů jako tabulka."""
    loader = SourcesConfigLoader("scraping/sources_config.yaml")
    table = loader.get_source_list_as_table()
    assert isinstance(table, list)
    assert len(table) > 0
    assert all('key' in item and 'name' in item and 'url' in item for item in table)
