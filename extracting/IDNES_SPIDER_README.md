# iDNES.cz Spider - Sekty, kulty, mesiáši

## 🚨 Cookie Consent Problem

iDNES.cz má velmi přísnou JavaScript-based cookie consent ochranu, která blokuje automatické scrapery.

## Řešení

### Varianta 1: Použít Playwright (doporučeno pro web scraping)

```bash
# Instalace
mamba activate project_infinit
pip install scrapy-playwright
playwright install chromium

# Enable Playwright v extracting/idnes_spider.py:
# Odkomentuj řádky s DOWNLOAD_HANDLERS a TWISTED_REACTOR

# Spuštění
scrapy runspider extracting/idnes_spider.py
```

### Varianta 2: Použít iDNES RSS feed (jednodušší)

iDNES.cz má RSS feed pro domácí zprávy, který už je nakonfigurován:

```yaml
# V sources_config.yaml již existuje:
idnes_domaci:
  name: "iDNES.cz - Domaci"
  url: "https://servis.idnes.cz/rss.aspx?c=zpravodaj_domaci"
  enabled: true
```

RSS feed obsahuje všechny články včetně rubriky "Sekty, kulty, mesiáši". Keyword filtering automaticky vybere relevantní články.

**Výhody:**
- ✅ Žádné cookie consent problémy
- ✅ Už nakonfigurováno
- ✅ Běží stabilně
- ✅ Keyword filtering automaticky vybírá relevantní články

**Nevýhody:**
- ⚠️ RSS obsahuje všechny domácí články, ne jen rubriku "Sekty"
- ⚠️ Omezený počet posledních článků (~50)

### Varianta 3: Manuální scraping

Pokud potřebuješ historické články z archivu:
1. Otevři https://www.idnes.cz/zpravy/archiv/sekty-kulty-mesiasi.K64268 v prohlížeči
2. ScrapujHTML manuálně nebo použij browser extension
3. Ulož do CSV v formátu: `source_name,source_type,title,url,text,scraped_at,author,published_at,categories`

## Doporučení

Pro běžné použití: **Použij RSS feed** (idnes_domaci) - je už nakonfigurovaný a funguje spolehlivě.

Pro archivní články: **Nainstaluj Playwright** a aktivuj v spider konfiguraci.
