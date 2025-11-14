# 📁 testing/README.md
# Testing Guide for Project Infinit

Kompletní test suite pro projekt Infinit. Všechny testy používají pytest a monkeypatching pro testování bez externích závislostí.

## Instalace závislostí pro testování

```bash
pip install pytest pytest-cov pytest-mock
```

## Struktura testů

```
testing/
├── test_keywords.py           # Testy pro keyword filtering
├── test_db_loader.py          # Testy pro database layer (in-memory SQLite)
├── test_nlp_analysis.py       # Testy pro NLP wrapper (mock Stanza/Transformers)
├── test_config_loader.py      # Testy pro YAML config loader
├── test_rss_spider.py         # Testy pro RSS spider
├── test_api_spider.py         # Testy pro API spider
├── test_social_media_spider.py # Testy pro Reddit a X/Twitter API
└── README.md                  # Tento soubor
```

## Spuštění testů

### Spustit všechny testy
```bash
pytest -v testing/
```

### Spustit konkrétní test soubor
```bash
pytest -v testing/test_keywords.py
pytest -v testing/test_db_loader.py
pytest -v testing/test_rss_spider.py
pytest -v testing/test_social_media_spider.py
```

### Spustit konkrétní test
```bash
pytest -v testing/test_keywords.py::test_contains_relevant_keywords_positive
```

### Spustit s coverage report
```bash
pytest --cov=scraping --cov=database --cov=processing --cov-report=term-missing testing/
```

### Spustit s quick output
```bash
pytest -q testing/
```

## Test suite přehled

### 1. **test_keywords.py** — Filtrování klíčových slov
- ✅ `test_contains_relevant_keywords_positive` — Pozitivní test relevantního obsahu
- ✅ `test_contains_relevant_keywords_negative` — Negativní test nerelevantního obsahu
- ✅ `test_is_excluded_content` — Test vyloučených termínů

### 2. **test_db_loader.py** — Database layer
- ✅ `test_dbconnector_insert_and_query` — Insert a query zdroje (in-memory SQLite)

### 3. **test_nlp_analysis.py** — NLP pipeline
- ✅ `test_nlp_analysis_monkeypatched` — Test analyzátoru s mock Stanza/Transformers

### 4. **test_config_loader.py** — Konfigurace zdrojů
- ✅ `test_config_loader_loads_yaml` — Načtení YAML konfigurace
- ✅ `test_get_all_sources` — Vrácení všech zdrojů
- ✅ `test_get_enabled_sources` — Filtrování povolených zdrojů
- ✅ `test_get_source` — Načtení konkrétního zdroje
- ✅ `test_get_source_urls` — Export všech URL
- ✅ `test_get_scraping_settings` — Získání nastavení scrapingu
- ✅ `test_get_content_filters` — Získání filtrů obsahu
- ✅ `test_is_source_enabled` — Kontrola, zda je zdroj povolený
- ✅ `test_toggle_source` — Povolení/zakázání zdroje
- ✅ `test_add_custom_source` — Přidání vlastního zdroje
- ✅ `test_source_list_as_table` — Export jako tabulka

### 5. **test_rss_spider.py** — RSS spider
- ✅ `test_rss_spider_initialization` — Inicializace RSS spideru
- ✅ `test_rss_spider_filters_rss_sources` — Filtrování RSS zdrojů
- ✅ `test_rss_spider_parse_rss` — Parsování RSS feedu
- ✅ `test_rss_spider_filters_irrelevant_content` — Filtrování nerelevantního obsahu
- ✅ `test_rss_spider_handles_missing_fields` — Zpracování chybějících polí
- ✅ `test_single_rss_spider_specific_source` — SingleRSSSpider s konkrétním zdrojem
- ✅ `test_single_rss_spider_invalid_type` — Chyba na neinvalidním typu

### 6. **test_api_spider.py** — API spider
- ✅ `test_api_spider_initialization` — Inicializace API spideru
- ✅ `test_api_spider_filters_api_sources` — Filtrování API zdrojů
- ✅ `test_api_spider_parse_mediawiki_api` — Parsování MediaWiki API
- ✅ `test_api_spider_filters_irrelevant_content` — Filtrování nerelevantního obsahu
- ✅ `test_api_spider_handles_invalid_json` — Zpracování neplatného JSON
- ✅ `test_api_spider_query_method` — Parsování query metody
- ✅ `test_single_api_spider_specific_source` — SingleAPISpider s konkrétním zdrojem
- ✅ `test_single_api_spider_invalid_type` — Chyba na neinvalidním typu

### 7. **test_social_media_spider.py** — Sociální média (Reddit & X/Twitter)
- ✅ `test_reddit_spider_init` — Inicializace Reddit spideru s API klíči
- ✅ `test_reddit_spider_missing_credentials` — Chyba při chybějících credentials
- ✅ `test_reddit_spider_start_requests` — Generování počátečních requestů
- ✅ `test_reddit_parse_relevant_submission` — Parsování relevantního příspěvku
- ✅ `test_x_spider_init` — Inicializace X/Twitter spideru s bearer token
- ✅ `test_x_spider_missing_token` — Chyba při chybějícím tokenu
- ✅ `test_x_spider_get_headers` — Generování headers s bearer token
- ✅ `test_x_spider_start_requests` — Generování requestů z search queries
- ✅ `test_x_spider_parse_relevant_tweet` — Parsování relevantního tweetu
- ✅ `test_x_spider_filters_irrelevant_tweets` — Filtrování irelevantních tweetů
- ✅ `test_reddit_spider_loads_config` — Načtení konfiguraci z YAML
- ✅ `test_x_spider_loads_config` — Načtení konfiguraci z YAML

## Testování v CI/CD

Příklad GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      - name: Run tests
        run: pytest -v --cov=scraping --cov=database --cov=processing testing/
```

## Best practices

- Všechny testy používají **monkeypatching** pro izolaci
- **In-memory SQLite** pro DB testy (bez připojení na server)
- Testy jsou **nezávislé** — lze je spustit v libovolném pořadí
- Testy jsou **rychlé** — nehrají si se sítí ani soubory
- Testy mají **jasný název** — popisují co testují
- Testy jsou **čitelné** — jsou spíš jako dokumentace

## Rozšíření testů

Když přidáte nový modul, přidejte testy:

1. Vytvořit `testing/test_<module>.py`
2. Mockovat externí závislosti
3. Testovat happy path, edge cases a chyby
4. Spustit `pytest testing/test_<module>.py`

## Troubleshooting

**Testy se nespustí: "No module named pytest"**
```bash
pip install pytest
```

**ImportError v testech: "No module named scraping"**
```bash
cd /home/adam/Dokumenty/projects/project_infinit
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest testing/
```

**Monkeypatching nefunguje**
- Ujistěte se, že importujete správný modul (`import scraping.xxx`)
- Ujistěte se, že mockujete správný path (`monkeypatch.setattr('scraping.xxx.function', ...)`)

## Aktuální stav

- Total tests: **43+** (33 existující + 12 pro sociální média)
- Coverage: keywords, db, nlp, config, rss, api, sociální média
- All tests passing ✅
