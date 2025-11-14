# 📘 Project Infinit - Analysis of New Religious Movements in the Czech Republic

An ETL pipeline for collecting, analyzing, and visualizing information about new religious movements and sects in the Czech Republic. Features ethical web scraping, NLP analysis, and structured data storage.

[🇨🇿 Česká verze níže](#-projekt-infinit---analýza-nových-náboženských-hnutí-v-čr)

## 🌟 Features

- Ethical web scraping with rate limiting and robots.txt respect
- Automated data collection from multiple sources:
  - News websites and aggregators
  - Academic resources (Dingir.cz)
  - Wikipedia API
  - Specialized websites about religious movements
- Natural Language Processing:
  - Czech language support via Stanza
  - Named Entity Recognition for organizations and locations
  - Movement classification and relationship analysis
- Structured data storage in PostgreSQL
- Export capabilities for further analysis

## 🔧 Technology Stack

- **Python 3.10+** - Core programming language
- **Scrapy** - Web scraping framework
- **Stanza** - NLP toolkit for Czech language
- **SQLAlchemy** - Database ORM
- **PostgreSQL** - Data storage
- **Apache Airflow** - ETL orchestration (optional)

---

# 🇨🇿 Projekt Infinit - Analýza nových náboženských hnutí v ČR

ETL pipeline pro sběr, analýzu a vizualizaci informací o nových náboženských hnutích a sektách v České republice. Zahrnuje etický web scraping, NLP analýzu a strukturované ukládání dat.

## 🗂️ Project Structure

```bash
project_infinit/
├── scraping/           # Web scrapers and settings
│   ├── spider_settings.py     # Ethical scraping config
│   ├── keywords.py           # Centralized keyword management
│   └── *_spider.py          # Individual source scrapers
├── processing/         # Data processing scripts
│   ├── nlp_analysis.py      # NLP pipeline
│   ├── data_cleaning.py     # Data validation
│   └── import_csv_to_db.py  # Database ingestion
├── database/          # Database layer
│   ├── db_loader.py         # SQLAlchemy models
│   └── schema.sql          # Database schema
├── dags/              # Airflow DAGs (optional)
├── export/            # Output files
│   └── csv/                 # Scraped/processed data
├── data/              # Input data
│   ├── pdf/                 # PDF documents
│   └── xlsx/               # Excel files
├── config.py          # Configuration
└── main.py            # Main ETL orchestrator
```

---

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
git clone https://github.com/Adam8eifert/project_infinit.git
cd project_infinit
python -m venv venv

# Windows
./venv/Scripts/activate

# Linux/macOS
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt

# Download Czech language model for Stanza
python -m stanza.download cs
```

### 3. Configure Database

Create `config.py`:

```python
DB_URI = "postgresql+psycopg2://username:password@localhost/nsm_db"
```

### 4. Run Pipeline

```bash
# Run complete ETL pipeline
python main.py

# Or run individual spiders
scrapy runspider scraping/sekty_cz_spider.py
```

## 🔄 Pipeline Steps

1. **Data Collection**
   - Scrape articles from configured RSS feeds and APIs
   - Collect posts from Reddit and X (Twitter)
   - Extract text from PDFs
   - Convert XLSX files to CSV

2. **Processing**
   - Clean and validate data
   - Perform NLP analysis
   - Extract entities and relationships

3. **Storage**
   - Import to SQLite database
   - Generate CSV exports
   - Update analysis results

### Data Sources

The pipeline collects data from multiple sources configured in `scraping/sources_config.yaml`:

| Type | Source | Method | Status |
|------|--------|--------|--------|
| RSS | Sekty.tv | Feed parser | ✅ Active |
| RSS | Sekty.cz | Feed parser | ✅ Active |
| RSS | Info Dingir | Feed parser | ✅ Active |
| RSS | Pastorace | Feed parser | ✅ Active |
| RSS | Medium/Seznam | Feed parser | ✅ Active |
| API | Wikipedia | MediaWiki API | ✅ Active |
| API | SOCCAS | REST API | ✅ Active |
| Social API | Reddit | Official API (PRAW) | ✅ Configured |
| Social API | X/Twitter | API v2 | ✅ Configured |
| Web | Google News | Web scraping | ⏸️ Legacy |

### Setting Up Social Media Sources

To enable Reddit and X (Twitter) data collection:

1. **Create `.env` file**
   ```bash
   cp .env.example .env
   ```

2. **Reddit API Setup**
   - Go to https://www.reddit.com/prefs/apps
   - Create a "script" application
   - Copy `client_id` and `client_secret` to `.env`:
     ```
     REDDIT_CLIENT_ID=your_client_id
     REDDIT_CLIENT_SECRET=your_client_secret
     REDDIT_USER_AGENT=ProjectInfinit/1.0 (by your_username)
     ```

3. **X/Twitter API Setup**
   - Register at https://developer.twitter.com/
   - Create an app with API v2 access
   - Copy Bearer Token to `.env`:
     ```
     X_BEARER_TOKEN=your_bearer_token
     ```

4. **Run Social Media Spiders**
   ```bash
   # Run all spiders including social media
   python main.py
   
   # Or run specific social media spider
   scrapy runspider scraping/social_media_spider.py
   ```

## 🇨🇿 Rychlý start

### 1. Klonování a příprava prostředí

```bash
git clone https://github.com/Adam8eifert/project_infinit.git
cd project_infinit
python -m venv venv

# Windows
./venv/Scripts/activate

# Linux/macOS
source venv/bin/activate
```

### 2. Instalace závislostí

```bash
pip install -r requirements.txt

# Stažení českého jazykového modelu pro Stanza
python -m stanza.download cs
```

### 3. Konfigurace databáze

Databáze se automaticky vytvoří při prvním spuštění. Používáme SQLite (data/project_infinit.db).

```python
# config.py (standardně)
DB_URI = "sqlite:///data/project_infinit.db"
```

### 4. Konfigurace sociálních médií

Chcete-li sbírat data z Redditu a X (Twitter):

1. **Vytvoření `.env` souboru**
   ```bash
   cp .env.example .env
   ```

2. **Reddit API Setup**
   - Jděte na https://www.reddit.com/prefs/apps
   - Vytvořte "script" aplikaci
   - Zkopírujte `client_id` a `client_secret` do `.env`:
     ```
     REDDIT_CLIENT_ID=váš_client_id
     REDDIT_CLIENT_SECRET=váš_client_secret
     REDDIT_USER_AGENT=ProjectInfinit/1.0 (od vašeho_uživatele)
     ```

3. **X/Twitter API Setup**
   - Zaregistrujte se na https://developer.twitter.com/
   - Vytvořte aplikaci s API v2 přístupem
   - Zkopírujte Bearer Token do `.env`:
     ```
     X_BEARER_TOKEN=váš_bearer_token
     ```

### 5. Spuštění

```bash
# Spuštění celého ETL pipeline
python main.py

# Nebo spuštění jednotlivých spiderů
scrapy runspider scraping/sekty_cz_spider.py
```

## 🔄 Kroky zpracování

1. **Sběr dat**
   - Scraping článků z nastavených zdrojů
   - Extrakce textu z PDF
   - Konverze XLSX souborů do CSV

2. **Zpracování**
   - Čištění a validace dat
   - NLP analýza
   - Extrakce entit a vztahů

3. **Ukládání**
   - Import do PostgreSQL databáze
   - Generování CSV exportů
   - Aktualizace výsledků analýzy

---

## 📦 Dependencies

### Core
- Python 3.10+
- Scrapy 2.11+
- SQLAlchemy 2.0+
- psycopg2-binary
- pandas
- stanza

### Processing
- openpyxl (Excel processing)
- PyMuPDF (PDF extraction)
- numpy
- scikit-learn

### Optional
- apache-airflow (DAG orchestration)
- jupyter (analysis notebooks)
- powerbi-client (visualization)

## 📊 Outputs

- Structured data in PostgreSQL
- CSV exports in `export/csv/`
- Power BI dashboards
- Analysis reports

## 🛡️ Ethical Guidelines

- Respect robots.txt
- Rate limiting
- Proper user agent identification
- Data minimization
- Source attribution
- Privacy consideration

## 📬 Future Development

- [ ] Additional source spiders
- [ ] Expanded format support
- [ ] Advanced NLP features
- [ ] Trend analysis
- [ ] Geographic visualization
- [ ] Timeline analysis
- [ ] API development

## 📦 Závislosti

### Základní
- Python 3.10+
- Scrapy 2.11+
- SQLAlchemy 2.0+
- psycopg2-binary
- pandas
- stanza

### Zpracování
- openpyxl (Excel)
- PyMuPDF (PDF)
- numpy
- scikit-learn

### Volitelné
- apache-airflow (DAG orchestrace)
- jupyter (analytické notebooky)
- powerbi-client (vizualizace)

## 📊 Výstupy

- Strukturovaná data v PostgreSQL
- CSV exporty v `export/csv/`
- Power BI dashboardy
- Analytické reporty

## �️ Etické zásady

- Respektování robots.txt
- Omezení rychlosti
- Správná identifikace user agenta
- Minimalizace dat
- Atribuce zdrojů
- Ohled na soukromí

## 📬 Budoucí vývoj

- [ ] Další zdrojové spidery
- [ ] Rozšířená podpora formátů
- [ ] Pokročilé NLP funkce
- [ ] Analýza trendů
- [ ] Geografická vizualizace
- [ ] Časová analýza
- [ ] Vývoj API

---

Version: 2.0
Author: Adam Šeifert
License: MIT
Last updated: 2025-11-08

