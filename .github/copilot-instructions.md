## Quick orientation for AI code assistants

This repository is an ETL pipeline for collecting and analysing articles about new religious movements in the Czech Republic. Keep instructions short and code-focused—the humans want runnable changes and references to concrete files.

- Entry point: `main.py` — orchestrates the ETL flow: `create_db()` → `run_spiders()` (`scrapy runspider scraping/<spider>.py`) → `process_csv()` → `run_nlp()` → `load_scraped_csvs()`.
- Configuration: edit `config.py` and set `DB_URI` (Postgres). The app uses SQLAlchemy via `database/db_loader.py`.
- Outputs: scraped and intermediate CSV files live in `export/csv/`. Final storage is PostgreSQL (see `database/db_loader.py` models: Movement, Alias, Location, Source).

Important commands (copyable):

```bash
# create venv, install deps
python -m venv venv
source venv/bin/activatev
pip install -r requirements.txt

# stanza models (Czech) — recommended before running NLP-heavy code
python -m spacy download cs_core_news_md

# run the whole pipeline
python main.py

# run an individual spider
scrapy runspider scraping/sekty_cz_spider.py
```

Repository conventions and patterns to follow

- Spiders: each scraper is a single-file Scrapy spider under `scraping/`. They are invoked with `scrapy runspider scraping/<file>.py` (not via a Scrapy project). Use `export/csv/` for outputs and keep CSV columns consistent.
- CSV ingestion: `processing/import_csv_to_db.py` expects these required columns: `source_name, source_type, title, url, text, scraped_at`. Keep that schema when producing CSVs.
- DB models: `database/db_loader.py` uses SQLAlchemy declarative models. `Source.url` is unique — avoid inserting duplicates (CSV loader already catches IntegrityError).
- NLP: `processing/nlp_analysis.py` initializes Stanza pipeline for Czech (`tokenize,mwt,pos,lemma,ner`) and uses HuggingFace `transformers` sentiment pipeline for short inputs (first 512 chars).

Examples to reference when making edits

- Add a new spider: create `scraping/<name>_spider.py` and ensure the output CSV uses the required column set. Update `main.py`'s `spiders` list to orchestrate it.
- Fix CSV mapping: edit `processing/import_csv_to_db.py` — mapping to movement_id is done later; if you add mapping logic, keep transaction handling and commit/rollback as shown.
- Change DB schema: modify `database/db_loader.py` models and keep `DBConnector.create_tables()` semantics (call `Base.metadata.create_all(engine)`).

What to avoid / watchouts

- Do not hardcode DB credentials in commits. `config.py` is committed with an example; replace locally before running.
- Spacy/stanza downloads may be triggered in code (the code calls `stanza.download('cs')`) but prefer explicit setup in CI/dev environment to avoid slow first-run downloads.
- Transformers sentiment model is multilingual and used for short snippets — expect slow downloads and possible memory usage.

Where to look next

- High-level: `readme.md` (run instructions and overview)
- ETL orchestration: `main.py`
- DB & schema: `database/db_loader.py`
- CSV processing: `processing/import_csv_to_db.py`
- NLP: `processing/nlp_analysis.py`
- Spiders: `scraping/` directory

If you want me to expand this into CI steps, test commands (pytest), or add a small contributor checklist, say which you'd prefer and I’ll extend the file.
