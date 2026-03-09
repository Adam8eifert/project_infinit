# Project Infinit

ETL pipeline pro sběr a analýzu článků o nových náboženských hnutích v ČR.

Projekt aktuálně používá Scrapy spidery v adresáři `extracting/`, ukládá data do CSV a následně je importuje do PostgreSQL přes SQLAlchemy.

## Co pipeline dělá

- sbírá data z RSS, API a webových zdrojů,
- importuje články do databáze,
- odfiltruje nerelevantní obsah,
- dopočítá sentiment a risk skóre,
- extrahuje entity (hnutí, osoby, lokace),
- vypíše souhrnné statistiky.

Vstupní bod je `main.py`.

## Aktuální orchestrátor

- Airflow je z projektu odstraněn.
- Orchestrace běží přes `python main.py`.
- Pro CI/CD je připravený směr na GitHub Actions.

## Aktivní sběrače

Pipeline spouští tyto spidery:

- `extracting/rss_spider.py`
- `extracting/api_spider.py`
- `extracting/sekty_tv_spider.py`
- `extracting/idnes_archive_spider.py`
- `extracting/social_media_spider.py` (Reddit)
- `extracting/medium_seznam_spider.py`
- `extracting/google_spider.py`

## Co bylo odstraněno jako nepoužívané

- Airflow konfigurace a DAGy,
- X/Twitter integrace.

Legacy skripty v `scraping/` a `trends/` jsou nyní ponechané jako placeholdery pro budoucí vývoj, ale nejsou součástí hlavní ETL orchestrace.

## Instalace

```bash
mamba create -n project_infinit -y --file environment.yml
mamba activate project_infinit
```

## Konfigurace

1. Nastav `DB_URI` v `config.py`.
2. Pro Reddit (volitelné) vytvoř `.env` podle `.env.example`.

## Spuštění

### Celá pipeline

```bash
python main.py
```

### Jednotlivé spidery

```bash
scrapy runspider extracting/rss_spider.py
scrapy runspider extracting/api_spider.py
scrapy runspider extracting/social_media_spider.py
```

## CSV schéma

CSV import očekává minimálně sloupce:

- `source_name`
- `source_type`
- `title`
- `url`
- `text`
- `scraped_at`

Importér: `processing/import_csv_to_db.py`.

## Testy

```bash
python -m pytest testing/ -q
```

## Struktura projektu

```text
project_infinit/
├── extracting/              # aktivní spidery a konfigurace zdrojů
├── processing/              # import, NLP, entity processing
├── database/                # SQLAlchemy modely, migrace, SQL skripty
├── testing/                 # testy
├── export/csv/              # výstupní CSV
├── academic_data/           # PDF/DOC/DOCX pro akademické zdroje
├── main.py                  # orchestrace ETL
├── config.py                # konfigurace DB
└── environment.yml          # definice prostředí
```

## Poznámky

- `Article.url` je unikátní, duplikáty se při importu ošetřují.
- Některé RSS zdroje jsou v `extracting/sources_config.yaml` záměrně disabled (404, malformed XML, prázdné feedy).
- Pokud chceš přidat nový zdroj, přidej ho do `extracting/sources_config.yaml` a drž se stejného CSV schématu.
