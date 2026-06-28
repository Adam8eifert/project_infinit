from extracting.configured_collectors import ConfiguredSourceCollector


class DummyLoader:
    def __init__(self, sources):
        self._sources = sources

    def get_all_sources(self):
        return self._sources

    def get_sources_by_acquisition(self, method):
        return {
            key: source
            for key, source in self._sources.items()
            if (source.get('acquisition') or {}).get('method') == method
        }


def test_parse_sitemap_urls_extracts_loc_entries():
    collector = ConfiguredSourceCollector(DummyLoader({}))
    xml_payload = """<?xml version=\"1.0\"?>
    <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
      <url><loc>https://example.cz/clanek-1</loc></url>
      <url><loc>https://example.cz/clanek-2</loc></url>
    </urlset>"""

    urls = collector._parse_sitemap_urls(xml_payload)

    assert urls == ["https://example.cz/clanek-1", "https://example.cz/clanek-2"]


def test_collect_api_source_uses_configured_endpoint_and_params(monkeypatch):
    calls = {}

    def fake_fetch_json(url, params=None, timeout=10):
        calls['url'] = url
        calls['params'] = params
        return {"items": [{"title": "Test title", "url": "https://example.cz/test", "content": "Sekta"}]}

    collector = ConfiguredSourceCollector(DummyLoader({}))
    monkeypatch.setattr(collector, "_fetch_json", fake_fetch_json)

    source = {
        "name": "Test API",
        "enabled": True,
        "type": "api",
        "acquisition": {
            "method": "api",
            "url": "https://example.cz/api",
            "params": {"q": "sekta"},
        },
    }

    wrote = collector._collect_api_source("test_api", source)

    assert wrote == 1
    assert calls['url'] == "https://example.cz/api"
    assert calls['params'] == {"q": "sekta"}


def test_collect_sitemap_source_follows_sitemap_index(monkeypatch):
    collector = ConfiguredSourceCollector(DummyLoader({}))
    calls = []

    def fake_fetch_text(url, timeout=15):
        calls.append(url)
        if url == "https://example.cz/sitemap.xml":
            return """<?xml version=\"1.0\"?>
            <sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
              <sitemap><loc>https://example.cz/sitemap-1.xml</loc></sitemap>
            </sitemapindex>"""
        if url == "https://example.cz/sitemap-1.xml":
            return """<?xml version=\"1.0\"?>
            <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
              <url><loc>https://example.cz/clanek</loc></url>
            </urlset>"""
        return ""

    monkeypatch.setattr(collector, "_fetch_text", fake_fetch_text)
    monkeypatch.setattr("extracting.configured_collectors.append_row", lambda *args, **kwargs: None)

    source = {
        "name": "Test sitemap",
        "enabled": True,
        "type": "sitemap",
        "acquisition": {
            "method": "sitemap",
            "url": "https://example.cz/sitemap.xml",
        },
    }

    wrote = collector._collect_sitemap_source("test_sitemap", source)

    assert wrote == 1
    assert calls[:2] == ["https://example.cz/sitemap.xml", "https://example.cz/sitemap-1.xml"]
    assert calls[2] == "https://example.cz/clanek"


def test_extract_api_items_supports_mediawiki_query_search_payload():
    collector = ConfiguredSourceCollector(DummyLoader({}))
    payload = {
        "query": {
            "search": [
                {"title": "Sekta", "snippet": "Příběh o sektě."},
                {"title": "Nové náboženské hnutí", "snippet": "Příklad hnutí."},
            ]
        }
    }

    items = collector._extract_api_items(payload, response_path="query.search")

    assert len(items) == 2
    assert items[0]["title"] == "Sekta"
    assert items[0]["content"] == "Příběh o sektě."
