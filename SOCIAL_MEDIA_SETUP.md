# Social Media Setup

Tento projekt aktuálně používá v hlavní pipeline pouze Reddit sběr přes `extracting/social_media_spider.py`.

## Co je aktuálně podporováno

- Reddit (volitelně, přes API klíče v `.env`)

## Co už se nepoužívá

- X/Twitter integrace je odstraněna.
- Legacy standalone social skripty ve `scraping/` jsou ponechané jako placeholdery pro budoucí vývoj (aktuálně se nespouští v `main.py`).

## Reddit API konfigurace

1. Vytvoř `.env` soubor podle `.env.example`.
2. Nastav hodnoty:

```bash
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=project_infinit/1.0
```

1. V `extracting/sources_config.yaml` zapni zdroj `reddit` (`enabled: true`).

## Spuštění

### Samostatné spuštění Reddit spideru

```bash
scrapy runspider extracting/social_media_spider.py
```

### Spuštění celé pipeline

```bash
python main.py
```

## Výstup

Reddit data se zapisují do:

- `export/csv/reddit_raw.csv`

## Troubleshooting

### Chyba autentizace Reddit API

- ověř `REDDIT_CLIENT_ID` a `REDDIT_CLIENT_SECRET`,
- zkontroluj, že app na Redditu je typu `script`,
- zkontroluj, že se načítá správný `.env` soubor.

### Reddit spider nic nenačetl

- ověř `enabled: true` u `reddit` v `extracting/sources_config.yaml`,
- spusť spider s detailnějším logem:

```bash
SCRAPY_LOGLEVEL=DEBUG scrapy runspider extracting/social_media_spider.py
```
