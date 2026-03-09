# 📁 testing/test_idnes_archive_spider.py
# Tests for iDNES archive spider

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime


def test_idnes_spider_initialization(monkeypatch):
    """Test iDNES archive spider initialization with configuration."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'iDNES.cz Archiv - Sekty, kulty, mesiáši',
        'type': 'web',
        'enabled': True,
        'url': 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268',
        'output_csv': 'export/csv/idnes_archive_sekty_raw.csv'
    }
    
    monkeypatch.setattr('extracting.idnes_archive_spider.get_config_loader', lambda: mock_loader)
    
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    spider = IDNESArchiveSpider()
    
    assert spider.name == 'idnes_archive'
    assert spider.SOURCE_KEY == 'idnes_archive_sekty'
    assert spider.enabled is True
    assert 'idnes.cz' in spider.archive_url


def test_idnes_spider_disabled_source(monkeypatch):
    """Test spider respects enabled=False configuration."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'name': 'iDNES.cz Archiv',
        'type': 'web',
        'enabled': False,
        'url': 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268',
        'output_csv': 'export/csv/idnes_archive_sekty_raw.csv'
    }
    
    monkeypatch.setattr('extracting.idnes_archive_spider.get_config_loader', lambda: mock_loader)
    
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    spider = IDNESArchiveSpider()
    
    requests = list(spider.start_requests())
    assert len(requests) == 0


def test_idnes_article_url_validation():
    """Test article URL validation regex."""
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz'}
    
    with patch('extracting.idnes_archive_spider.get_config_loader', return_value=mock_loader):
        spider = IDNESArchiveSpider()
    
    # Valid article URLs
    assert spider._is_article_url('https://www.idnes.cz/zpravy/domaci/scientologie.A261201_123456_domaci_knn') is True
    assert spider._is_article_url('https://idnes.cz/zpravy/zahranicni/sekty.A250101_999999_zahranicni_abc') is True
    
    # Invalid URLs
    assert spider._is_article_url('https://www.idnes.cz/zpravy/archiv/sekty.K64268') is False
    assert spider._is_article_url('https://www.idnes.cz/zpravy/domaci/test.A123/diskuse') is False
    assert spider._is_article_url('https://example.com/article') is False


def test_idnes_parse_archive_cards(monkeypatch):
    """Test parsing archive page with article cards."""
    mock_html = """
    <html>
        <body>
            <div class="col-a">
                <div class="art">
                    <a class="art-link" href="/zpravy/domaci/scientologie-clanek.A261201_123456_domaci_knn">
                        <h3>Scientologie expanduje v Praze</h3>
                    </a>
                    <p>Krátký popis článku o scientologii</p>
                    <span class="time" datetime="2026-12-01T10:00:00+01:00"></span>
                </div>
                <div class="art">
                    <a class="art-link" href="/zpravy/zahranicni/kult-article.A261202_789012_zahranicni_abc">
                        <h3>Nový kult v zahraničí</h3>
                    </a>
                    <p>Zpráva o kultu</p>
                    <span class="time" datetime="2026-12-02T14:00:00+01:00"></span>
                </div>
            </div>
        </body>
    </html>
    """
    
    mock_response = Mock()
    mock_response.text = mock_html
    mock_response.url = 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268'
    mock_response.meta = {'page_number': 1}
    
    def mock_css(selector):
        mock_sel = Mock()
        if selector == "div.col-a > div.art":
            card1 = Mock()
            card1_link = Mock()
            card1_link.get.return_value = "/zpravy/domaci/scientologie-clanek.A261201_123456_domaci_knn"
            card1.css.side_effect = lambda s: card1_link if "::attr(href)" in s else Mock(get=lambda: "Scientologie expanduje v Praze" if "h3::text" in s else "Krátký popis" if "p::text" in s else "2026-12-01T10:00:00")
            
            card2 = Mock()
            card2_link = Mock()
            card2_link.get.return_value = "/zpravy/zahranicni/kult-article.A261202_789012_zahranicni_abc"
            card2.css.side_effect = lambda s: card2_link if "::attr(href)" in s else Mock(get=lambda: "Nový kult v zahraničí" if "h3::text" in s else "Zpráva o kultu" if "p::text" in s else "2026-12-02T14:00:00")
            
            mock_sel.__iter__ = Mock(return_value=iter([card1, card2]))
            return mock_sel
        elif selector == "a.contentwall_login":
            return []
        else:
            return Mock(getall=Mock(return_value=[]))
    
    mock_response.css = mock_css
    mock_response.urljoin = lambda url: f"https://www.idnes.cz{url}" if url.startswith('/') else url
    
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz', 'name': 'iDNES'}
    
    monkeypatch.setattr('extracting.idnes_archive_spider.get_config_loader', lambda: mock_loader)
    
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    spider = IDNESArchiveSpider()
    
    requests = list(spider.parse_archive(mock_response))
    
    # Should generate 2 article requests (no next page in this mock)
    article_requests = [r for r in requests if 'A261201_123456' in r.url or 'A261202_789012' in r.url]
    assert len(article_requests) == 2
    assert any('scientologie-clanek' in r.url for r in article_requests)


def test_idnes_parse_article(monkeypatch):
    """Test parsing individual article."""
    mock_html = """
    <html>
        <head>
            <meta property="og:title" content="Scientologie otevírá centrum v Praze" />
            <meta property="article:published_time" content="2026-12-01T10:00:00+01:00" />
            <meta name="keywords" content="sekty,scientologie,Praha" />
        </head>
        <body>
            <h1 class="arttit">Scientologie otevírá centrum v Praze</h1>
            <div class="opener" itemprop="description">Scientologická církev oznámila otevření nového centra.</div>
            <div id="art-text">
                <p>Scientologická církev včera oznámila, že v Praze otevře nové centrum pro své členy.</p>
                <p>Centrum bude sloužit jako místo pro setkávání a kurzy.</p>
            </div>
            <div class="authors">
                <a class="name"><span itemprop="name">Jan Novák</span></a>
            </div>
        </body>
    </html>
    """
    
    mock_response = Mock()
    mock_response.text = mock_html
    mock_response.url = 'https://www.idnes.cz/zpravy/domaci/scientologie-clanek.A261201_123456_domaci_knn'
    mock_response.meta = {
        'preview_title': 'Scientologie otevírá centrum',
        'preview_summary': 'Krátký popis',
        'preview_published': '2026-12-01T10:00:00'
    }
    
    def mock_css(selector):
        if "h1.arttit::text" in selector or "h1::text" in selector:
            return Mock(get=lambda: "Scientologie otevírá centrum v Praze - iDNES.cz")
        elif "div.opener" in selector:
            return Mock(getall=lambda: ["Scientologická církev oznámila otevření nového centra."])
        elif "div#art-text" in selector or "articleBody" in selector:
            return Mock(getall=lambda: [
                "Scientologická církev včera oznámila, že v Praze otevře nové centrum pro své členy.",
                "Centrum bude sloužit jako místo pro setkávání a kurzy."
            ])
        elif ".authors" in selector and "name" in selector:
            return Mock(get=lambda: "Jan Novák")
        elif "span.time-date::attr(content)" in selector:
            return Mock(get=lambda: "2026-12-01T10:00:00+01:00")
        return Mock(get=lambda: None, getall=lambda: [])
    
    def mock_xpath(selector):
        if "article:published_time" in selector:
            return Mock(get=lambda: "2026-12-01T10:00:00+01:00")
        elif "keywords" in selector:
            return Mock(get=lambda: "sekty,scientologie,Praha")
        elif "author" in selector:
            return Mock(get=lambda: "Jan Novák")
        return Mock(get=lambda: None)
    
    mock_response.css = mock_css
    mock_response.xpath = mock_xpath
    
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz', 'name': 'iDNES Archiv', 'output_csv': 'test.csv'}
    
    monkeypatch.setattr('extracting.idnes_archive_spider.get_config_loader', lambda: mock_loader)
    monkeypatch.setattr('extracting.idnes_archive_spider.append_row', lambda path, item: None)
    
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    spider = IDNESArchiveSpider()
    
    results = list(spider.parse_article(mock_response))
    
    assert len(results) == 1
    item = results[0]
    assert 'Scientologie' in item['title']
    assert 'centrum' in item['text']
    assert item['author'] == 'Jan Novák'
    assert 'scientologie' in item['categories'].lower()


def test_idnes_paywall_detection():
    """Test detection of paywalled articles."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz', 'name': 'iDNES'}
    
    with patch('extracting.idnes_archive_spider.get_config_loader', return_value=mock_loader):
        from extracting.idnes_archive_spider import IDNESArchiveSpider
        spider = IDNESArchiveSpider()
    
    # Paywalled content
    paywalled_text = "Dočtěte tento exkluzivní článek s předplatným iDNES Premium Předplatit"
    assert spider._looks_paywalled(paywalled_text) is True
    
    # Normal content
    normal_text = "Scientologická církev otevírá nové centrum v Praze."
    assert spider._looks_paywalled(normal_text) is False
    
    # Empty text
    assert spider._looks_paywalled("") is True


def test_idnes_consent_wall_detection(monkeypatch):
    """Test detection of consent wall."""
    mock_html = """
    <html>
        <body>
            <a class="contentwall_login">Přihlásit se</a>
            <div>Musíte souhlasit s cookies</div>
        </body>
    </html>
    """
    
    mock_response = Mock()
    mock_response.text = mock_html
    mock_response.url = 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268'
    mock_response.meta = {'page_number': 1}
    
    def mock_css(selector):
        if "div.col-a > div.art" in selector:
            return []  # No article cards found
        elif "a.contentwall_login" in selector:
            return [Mock()]  # Consent wall present
        return Mock(getall=lambda: [])
    
    mock_response.css = mock_css
    
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz', 'name': 'iDNES'}
    
    monkeypatch.setattr('extracting.idnes_archive_spider.get_config_loader', lambda: mock_loader)
    
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    spider = IDNESArchiveSpider()
    
    requests = list(spider.parse_archive(mock_response))
    
    # Should return empty when consent wall is detected
    assert len(requests) == 0


def test_idnes_pagination_extraction():
    """Test extraction of next page URL."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz', 'name': 'iDNES'}
    
    with patch('extracting.idnes_archive_spider.get_config_loader', return_value=mock_loader):
        from extracting.idnes_archive_spider import IDNESArchiveSpider
        spider = IDNESArchiveSpider()
    
    mock_response = Mock()
    mock_response.url = 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268'
    
    def mock_css(selector):
        if "navbox" in selector:
            next_link = Mock()
            next_link.getall.return_value = ['/zpravy/archiv/sekty-kulty-mesiasi.K64268/2']
            return next_link
        return Mock(getall=lambda: [])
    
    mock_response.css = mock_css
    mock_response.urljoin = lambda url: f"https://www.idnes.cz{url}" if url.startswith('/') else url
    
    next_url = spider._get_next_page_url(mock_response)
    
    assert next_url is not None
    assert 'K64268/2' in next_url


def test_idnes_max_pages_limit(monkeypatch):
    """Test that spider respects max_pages limit."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {
        'enabled': True,
        'url': 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268',
        'name': 'iDNES'
    }
    
    monkeypatch.setattr('extracting.idnes_archive_spider.get_config_loader', lambda: mock_loader)
    
    from extracting.idnes_archive_spider import IDNESArchiveSpider
    spider = IDNESArchiveSpider(max_pages=2)
    
    assert spider.max_pages == 2
    
    # Mock response for page 2 (should not generate page 3 request)
    mock_response = Mock()
    mock_response.url = 'https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268/2'
    mock_response.meta = {'page_number': 2}
    
    def mock_css(selector):
        if "div.col-a > div.art" in selector:
            return []
        elif "navbox" in selector and "next" in selector.lower():
            return Mock(getall=lambda: ['/zpravy/archiv/sekty-kulty-mesiasi.K64268/3'])
        return Mock(getall=lambda: [])
    
    mock_response.css = mock_css
    mock_response.urljoin = lambda url: f"https://www.idnes.cz{url}"
    
    requests = list(spider.parse_archive(mock_response))
    
    # Should not generate next page request because we're at max_pages
    pagination_requests = [r for r in requests if hasattr(r, 'callback') and 'parse_archive' in str(r.callback)]
    assert len(pagination_requests) == 0


def test_idnes_body_cleaning():
    """Test cleaning of article body text with paywall fragments."""
    mock_loader = MagicMock()
    mock_loader.get_source.return_value = {'enabled': True, 'url': 'https://idnes.cz', 'name': 'iDNES'}
    
    with patch('extracting.idnes_archive_spider.get_config_loader', return_value=mock_loader):
        from extracting.idnes_archive_spider import IDNESArchiveSpider
        spider = IDNESArchiveSpider()
    
    # Body with paywall fragments
    dirty_body = [
        "Scientologická církev otevírá centrum.",
        "Dočtěte tento exkluzivní článek",
        "s předplatným iDNES Premium",
        "Předplatit",
        "Další text článku."
    ]
    
    cleaned = spider._clean_body(dirty_body)
    
    assert "Scientologická církev" in cleaned
    assert "Další text článku" in cleaned
    assert "Dočtěte tento exkluzivní" not in cleaned
    assert "Předplatit" not in cleaned
