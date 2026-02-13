# 📘 Project Infinit - Analysis of New Religious Movements in the Czech Republic

An ETL pipeline for collecting, analyzing, and visualizing information about new religious movements in the Czech Republic. Features ethical web scraping, NLP analysis, and structured data storage.

[🇨🇿 Česká verze níže](#-projekt-infinit---analýza-nových-náboženských-hnutí-v-čr)

## 🌟 Features

- Ethical web scraping with rate limiting and robots.txt respect
- Automated data collection from multiple sources:
  - RSS feeds from specialized websites
  - REST APIs (Wikipedia, SOCCAS)
  - Social media APIs (Reddit, X/Twitter)
  - Web scraping for news aggregators
- Natural Language Processing:
  - **Multilingual support**: Czech (Stanza) and English (Stanza) with automatic language detection
  - Named Entity Recognition via Hugging Face Transformers (WikiNeural, BioBERT)
  - Sentiment analysis via multilingual BERT models (nlptown/bert-base-multilingual)
  - Movement classification and relationship analysis
  - Academic document processing (PDF, DOC, DOCX text extraction)
- Structured data storage in PostgreSQL/SQLite
- Export capabilities for further analysis and Power BI integration
- Comprehensive testing suite with pytest
- Type-safe code with Pylance/Pyright integration

## 🔧 Technology Stack

- **Python 3.10+** - Core programming language
- **Scrapy 2.13+** - Web scraping framework with custom settings
- **Stanza 1.11+** - Czech and English NLP (tokenization, POS, lemma, NER)
- **langdetect** - Automatic language detection (Czech/English)
- **Hugging Face Transformers** - Advanced NLP models for NER and multilingual sentiment
- **SQLAlchemy 2.0+** - Database ORM with PostgreSQL/SQLite support
- **PRAW 7.8+** - Reddit API client
- **Tweepy 4.14+** - X (Twitter) API client
- **PyMuPDF 1.23+** - PDF text extraction
- **python-docx 1.1+** - Word document (.doc/.docx) processing
- **pandas 2.3+** - Data manipulation and CSV processing
- **pytest** - Testing framework with mocking
- **PyYAML** - Configuration management

## 🗂️ Project Structure

```text
project_infinit/
├── extracting/              # Web scrapers and configurations
│   ├── sources_config.yaml    # Centralized source configuration
│   ├── spider_settings.py     # Ethical scraping settings
│   ├── keywords.py           # Keyword filtering utilities
│   ├── config_loader.py      # YAML configuration loader
│   ├── rss_spider.py        # Universal RSS feed scraper
│   ├── api_spider.py        # Universal API scraper
│   ├── social_media_spider.py # Social media API scraper
│   ├── google_spider.py     # Google News scraper
│   ├── medium_seznam_spider.py # Medium/Seznam scraper
│   └── __pycache__/         # Python bytecode
├── processing/            # Data processing and analysis
│   ├── nlp_analysis.py       # NLP pipeline with Czech support
│   ├── import_csv_to_db.py   # CSV database ingestion utilities
│   ├── import_pdf_to_db.py   # PDF processing and ingestion
│   └── __pycache__/         # Python bytecode
├── database/              # Database layer
│   ├── db_loader.py          # SQLAlchemy models and connections
│   ├── models/              # Database models
│   │   ├── source.py        # Source model
│   │   ├── movement.py      # Movement model
│   │   ├── alias.py         # Alias model
│   │   ├── location.py      # Location model
│   │   ├── source_quality.py # Source quality model
│   │   ├── geographic_analysis.py # Geographic analysis model
│   │   ├── temporal_analysis.py # Temporal analysis model
│   │   └── __init__.py      # Models init
│   ├── schema.sql           # Database schema
│   ├── views.sql            # Database views
│   ├── deduplicate_sources.py # Source deduplication utilities
│   ├── ANALYTICS_README.md  # Analytics documentation
│   ├── migrate_analytics.py # Analytics migration script
│   ├── migrations/          # Database migrations
│   └── __pycache__/         # Python bytecode
├── testing/               # Test suite
│   ├── test_*.py           # Unit tests for all modules
│   ├── README.md           # Testing documentation
│   └── __pycache__/         # Python bytecode
├── export/                # Output files and exports
│   ├── csv/               # Scraped and processed CSV data
│   └── to_powerbi.py      # Power BI export utilities
├── data/                  # Input data directory
├── academic_data/         # Academic documents (PDF, DOC, DOCX)
├── nnh-db/                # Docker database setup
│   ├── docker             # Docker files
│   └── docker-compose.yml # Docker Compose configuration
├── .github/               # GitHub configuration
│   └── copilot-instructions.md # AI assistant instructions
├── config.py              # Database and app configuration
├── main.py                # Main ETL orchestrator
├── requirements.txt       # Python dependencies
├── environment.yml        # Conda environment
├── pyrightconfig.json    # Pyright type checking config
├── LICENSE                # Project license
├── SOCIAL_MEDIA_SETUP.md  # Social media API setup guide
├── import_log.txt         # CSV import log
├── pdf_import_log.txt     # PDF import log
└── readme.md             # This file
```

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
git clone https://github.com/Adam8eifert/project_infinit.git
cd project_infinit

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup NLP Models and Dependencies

```bash
# Using Mamba (recommended) for better dependency resolution
mamba create -n project_infinit -y --file environment.yml
mamba activate project_infinit

# Or using pip (fallback)
pip install -r requirements.txt

# Stanza will auto-download Czech and English models on first use
```

### 3. Configure Database

The project supports both PostgreSQL and SQLite.

```python
# config.py (default configuration)
DB_URI = "sqlite:///data/project_infinit.db"
```

For PostgreSQL:

```python
DB_URI = "postgresql+psycopg2://username:password@localhost/nsm_db"
```

### 4. Configure Social Media APIs (Optional)

To enable Reddit and X (Twitter) data collection:

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys (see .env.example for instructions)
```

### 5. Run the Pipeline

```bash
# Run complete ETL pipeline
python main.py

# Or run individual components
scrapy runspider extracting/rss_spider.py
scrapy runspider extracting/api_spider.py
scrapy runspider extracting/social_media_spider.py
```

## 🔄 ETL Pipeline Steps

1. **Data Collection** (`run_spiders()`)
   - RSS feeds from 12+ specialized and mainstream sources
   - REST APIs (Wikipedia, SOCCAS Encyclopedia)
   - Social media posts from Reddit and X/Twitter
   - Web scraping for news aggregators (Google News, Medium, Seznam)
   - Academic documents (PDF, DOC, DOCX from `academic_data/`)

2. **CSV Import** (`process_csv()`)
   - Load scraped CSV files from `export/csv/`
   - Deduplicate by URL and content hash (SHA256)
   - Import validated sources to database

3. **Academic Document Processing** (`process_academic_documents()`)
   - Extract text from PDF (PyMuPDF), DOC/DOCX (python-docx)
   - Convert legacy .doc to .docx via LibreOffice
   - Validate content (min 50 words + religious keywords)
   - Match documents to known movements
   - Import to database with metadata

4. **Entity Extraction** (`process_entities()`)
   - NER: Extract persons, organizations, locations from content
   - Create Alias records for movement name variations
   - Create Location records for geographic references
   - Match entities to movement database

5. **NLP Analysis** (`run_nlp()`)
   - **Language detection**: Automatically identify Czech/English
   - **Sentiment analysis**: Score emotional tone (positive/negative/neutral)
   - **Lemmatization & POS tagging**: Via Stanza pipelines
   - Generate sentiment logs and analysis reports

6. **Data Storage & Export** (`load_scraped_csvs()`)
   - Persist all processed data to PostgreSQL/SQLite
   - Generate CSV exports for Power BI
   - Create comprehensive audit logs

## 📊 Data Sources

The pipeline collects data from multiple sources configured in `extracting/sources_config.yaml`:

| Type       | Source                      | Method        | Status        | Description                  |
| ---------- | --------------------------- | ------------- | ------------- | ---------------------------- |
| RSS        | Sekty.TV                    | Feed Parser   | ✅ Active     | Specialized sect information |
| RSS        | Sekty.cz                    | Feed Parser   | ✅ Active     | Religious movement news      |
| RSS        | Dingir.cz                   | Feed Parser   | ✅ Active     | Academic religious studies   |
| RSS        | Pastorální péče             | Feed Parser   | ✅ Active     | Pastoral care resources      |
| RSS        | Seznam Zprávy               | Feed Parser   | ✅ Active     | Czech news portal            |
| RSS        | Český rozhlas (iRozhlas.cz) | Feed Parser   | ✅ Active     | Public radio news            |
| RSS        | Aktuálně.cz                 | Feed Parser   | ✅ Active     | Czech news website           |
| RSS        | Forum24.cz                  | Feed Parser   | ✅ Active     | Discussion forum             |
| RSS        | Deník Alarm                 | Feed Parser   | ✅ Active     | Investigative journalism     |
| RSS        | Blesk.cz                    | Feed Parser   | ✅ Active     | Tabloid news                 |
| Web        | Medium.seznam.cz            | Scrapy        | ✅ Active     | Blog articles                |
| API        | Sociologický ústav AVČR     | MediaWiki API | ✅ Active     | Academic research database   |
| API        | Wikipedia (Czech)           | MediaWiki API | ✅ Active     | Encyclopedia articles        |
| Search API | Google News                 | Custom API    | ⏸️ Legacy     | News aggregation             |
| Social API | Reddit                      | PRAW          | ✅ Configured | Community discussions        |
| Social API | X (Twitter)                 | Tweepy        | ✅ Configured | Social media posts           |

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run all tests
pytest testing/

# Run specific test
pytest testing/test_nlp_analysis.py -v
```

## 📦 Dependencies

### Core Requirements

- Python 3.10+
- Scrapy 2.13+ (web scraping)
- SQLAlchemy 2.0+ (database ORM)
- Stanza 1.11+ (Czech/English NLP)
- langdetect (automatic language detection)
- transformers 4.52+ (BERT sentiment, multilingual models)
- pandas 2.3+ (data manipulation)

### API Clients

- praw 7.8+ (Reddit)
- tweepy 4.14+ (X/Twitter)
- requests 2.31+
- feedparser 6.0+

### Data Processing & NLP

- PyMuPDF 1.23+ (PDF text extraction)
- python-docx 1.1+ (Word documents: .doc, .docx; auto-conversion .doc → .docx)
- openpyxl (Excel spreadsheet handling)
- fuzzywuzzy 0.18+ (fuzzy text matching for entity resolution)
- python-dotenv 1.0+ (environment variable management)
- numpy (numerical operations for NLP)

### Development

- pytest (testing)
- pyright (type checking)

## 📊 Outputs

- **Database**: Structured data in PostgreSQL/SQLite with relationships
- **CSV Exports**: Processed data in `export/csv/` directory
- **Power BI**: Direct integration via `export/to_powerbi.py`
- **Analysis Reports**: NLP insights and entity relationships
- **Logs**: Comprehensive logging in `import_log.txt`

## 🛡️ Ethical Guidelines

- ✅ Respect robots.txt and rate limits
- ✅ Proper user agent identification
- ✅ Data minimization and privacy protection
- ✅ Source attribution and transparency
- ✅ Academic and research-focused data collection
- ✅ No personal data collection without consent

## 🔧 Development

### Code Quality

- Type hints throughout codebase
- Pylance/Pyright type checking
- Comprehensive test coverage
- Ethical scraping practices
- Modular architecture

### Adding New Sources

1. Add configuration to `extracting/sources_config.yaml`
2. Implement spider in `extracting/` directory
3. Add tests in `testing/` directory
4. Update main.py orchestration

### Database Schema

The database uses SQLAlchemy ORM with the following main entities:

- **Source**: Articles, posts, and documents
- **Movement**: Religious movements and sects
- **Alias**: Alternative names for movements
- **Location**: Geographic references

## 📬 Future Development

- [ ] Enhanced NLP models for Czech language
- [ ] Real-time social media monitoring
- [ ] Advanced entity relationship analysis
- [ ] Geographic visualization of movements
- [ ] Trend analysis and time series
- [ ] REST API for data access
- [ ] Web dashboard interface
- [ ] Multi-language support expansion

---

## 🇨🇿 Projekt Infinit - Analýza nových náboženských hnutí v ČR

ETL pipeline pro sběr, analýzu a vizualizaci informací o nových náboženských hnutích v České republice. Zahrnuje etický web scraping, NLP analýzu a strukturované ukládání dat.

## 🌟 Funkce

- Etický web scraping s omezením rychlosti a respektováním robots.txt
- Automatizovaný sběr dat z více zdrojů:
  - RSS feedy ze specializovaných webů
  - REST API (Wikipedia, SOCCAS)
  - Sociální média API (Reddit, X/Twitter)
  - Web scraping pro news agregátory
- Zpracování přirozeného jazyka:
  - Podpora češtiny přes spaCy
  - Rozpoznávání entit přes Hugging Face Transformers
  - Analýza sentimentu přes multijazyčné BERT modely
  - Klasifikace hnutí a analýza vztahů
- Strukturované ukládání dat v PostgreSQL/SQLite
- Exportní možnosti pro další analýzu a Power BI integraci
- Komplexní testovací sada s pytest
- Type-safe kód s Pylance/Pyright integrací

## 🔧 Technologický stack

- **Python 3.10+** - Základní programovací jazyk
- **Scrapy** - Framework pro web scraping s vlastními nastaveními
- **spaCy** - NLP toolkit pro zpracování češtiny
- **Hugging Face Transformers** - Pokročilé NLP modely pro NER a sentiment
- **SQLAlchemy** - Database ORM s podporou PostgreSQL/SQLite
- **PRAW** - Reddit API klient
- **Tweepy** - X (Twitter) API klient
- **pandas** - Manipulace s daty a CSV zpracování
- **pytest** - Testovací framework s mocking
- **PyYAML** - Správa konfigurace

## 🗂️ Struktura projektu

```text
project_infinit/
├── extracting/              # Web scrapery a konfigurace
│   ├── sources_config.yaml    # Centralizovaná konfigurace zdrojů
│   ├── spider_settings.py     # Etická scraping nastavení
│   ├── keywords.py           # Utility pro filtrování klíčových slov
│   ├── config_loader.py      # Načítání YAML konfigurace
│   ├── rss_spider.py        # Univezální RSS feed scraper
│   ├── api_spider.py        # Univezální API scraper
│   ├── social_media_spider.py # Social media API scraper
│   ├── google_spider.py     # Google News scraper
│   ├── medium_seznam_spider.py # Medium/Seznam scraper
│   └── __pycache__/         # Python bytecode
├── processing/            # Zpracování a analýza dat
│   ├── nlp_analysis.py       # NLP pipeline s podporou češtiny
│   └── import_csv_to_db.py   # Utility pro import do databáze
├── database/              # Databázová vrstva
│   ├── db_loader.py          # SQLAlchemy modely a připojení
│   ├── models/              # Databázové modely
│   │   ├── source.py        # Model zdrojů
│   │   ├── movement.py      # Model hnutí
│   │   ├── alias.py         # Model aliasů
│   │   └── location.py      # Model lokací
│   └── schema.sql           # Databázové schéma
├── testing/               # Testovací sada
│   ├── test_*.py           # Unit testy pro všechny moduly
│   └── README.md           # Dokumentace testování
├── export/                # Výstupní soubory a exporty
│   ├── csv/               # Scraped a zpracovaná CSV data
│   └── to_powerbi.py      # Utility pro Power BI export
├── data/                  # Vstupní data
│   ├── pdf/               # PDF dokumenty pro zpracování
│   └── xlsx/              # Excel soubory pro konverzi
├── dags/                  # Apache Airflow DAGs (volitelné)
├── .github/               # GitHub konfigurace
├── config.py              # Konfigurace databáze a aplikace
├── main.py                # Hlavní ETL orchestrátor
├── requirements.txt       # Python závislosti
├── environment.yml        # Conda prostředí
├── pyrightconfig.json    # Konfigurace Pyright type checking
└── readme.md             # Tento soubor
```

## 🇨🇿 Rychlý start (CZ)

### 1. Klonování a příprava prostředí

```bash
git clone https://github.com/adamseifert/project_infinit.git
cd project_infinit

# Vytvoření Mamba environment (doporučeno)
mamba create -n project_infinit -y --file environment.yml
mamba activate project_infinit

# Nebo pip (fallback)
pip install -r requirements.txt
```

### 2. Nastavení NLP a závislostí

Stanza automaticky stáhne české a anglické modely při prvním spuštění:

```bash
# Žádné další kroky nejsou nutné – NLP se inicializuje při main.py
```

### 3. Konfigurace databáze

```python
# config.py (výchozí SQLite)
DB_URI = "sqlite:///data/project_infinit.db"

# Pro PostgreSQL:
DB_URI = "postgresql+psycopg2://user:password@localhost/project_infinit"
```

### 4. Spuštění pipeline

```bash
# Kompletní ETL pipeline
python main.py

# Jednotlivé komponenty
scrapy runspider extracting/rss_spider.py
python -c "from main import process_academic_documents; process_academic_documents()"
```

## 🇨🇿 Mám shluk přehleda🔄 Kroky ETL Pipeline (CZ)

1. **Sběr dat** (`run_spiders()`)
   - RSS feedy z 12+ specializaį a mainstream zdrojů
   - REST API (Wikipedia, SOCCAS Encyklopedie)
   - Sociální média (Reddit, X/Twitter)
   - Web scraping (Google News, Medium, Seznam)
   - Akademické dokumenty (PDF, DOC, DOCX z `academic_data/`)

2. **Import CSV** (`process_csv()`)
   - Načtení scraped CSV souborů z `export/csv/`
   - Deduplicita po URL a obsahu (SHA256)
   - Import validních zdrojů do databáze

3. **Zpracování akademických dokumentů** (`process_academic_documents()`)
   - Extrakce textu z PDF (PyMuPDF), DOC/DOCX (python-docx)
   - Konverze legacy .doc na .docx přes LibreOffice
   - Validace obsahu (min 50 slov + nábožská klíčová slova)
   - Matchání dokumentů na známá hnutí
   - Import do databáze s metadaty

4. **Extrakce entit** (`process_entities()`)
   - NER: Extrakce osob, organizačí, míst z obsahu
   - Vytvoření Alias záznamů pro varianty názvů hnutí
   - Vytvoření Location záznamů pro geografické odkazy
   - Matchání entit na databázi hnutí

5. **NLP analýza** (`run_nlp()`)
   - **Detekce jazyka**: Automatická identifikace českých/anglických textů
   - **Analýza sentimentu**: Skórání emocionálního tónu (kladné/záporné/neutrální)
   - **Lemmatizace & POS tagging**: Přes Stanza pipeline
   - Generání sentiment logů a zpravy analýzy

6. **Ukládání & Export** (`load_scraped_csvs()`)
   - Uchování všech zpracovaných dat v PostgreSQL/SQLite
   - Generání CSV exportů pro Power BI
   - Vytvoření komplexních audit logů
   - Vytváření analytických reportů

## 📊 Zdroje dat

Pipeline sbírá data z více zdrojů nakonfigurovaných v `extracting/sources_config.yaml`:

| Typ          | Zdroj                       | Metoda        | Status             | Popis                              |
| ------------ | --------------------------- | ------------- | ------------------ | ---------------------------------- |
| RSS          | Sekty.TV                    | Feed Parser   | ✅ Aktivní         | Specializované informace o sektách |
| RSS          | Sekty.cz                    | Feed Parser   | ✅ Aktivní         | Novinky o náboženských hnutích     |
| RSS          | Dingir.cz                   | Feed Parser   | ✅ Aktivní         | Akademické náboženské studie       |
| RSS          | Pastorální péče             | Feed Parser   | ✅ Aktivní         | Pastorační péče                    |
| RSS          | Seznam Zprávy               | Feed Parser   | ✅ Aktivní         | Český zpravodajský portál          |
| RSS          | Český rozhlas (iRozhlas.cz) | Feed Parser   | ✅ Aktivní         | Veřejnoprávní rozhlasové noviny    |
| RSS          | Aktuálně.cz                 | Feed Parser   | ✅ Aktivní         | České zpravodajské stránky         |
| RSS          | Forum24.cz                  | Feed Parser   | ✅ Aktivní         | Diskuzní fórum                     |
| RSS          | Deník Alarm                 | Feed Parser   | ✅ Aktivní         | Investigativní žurnalistika        |
| RSS          | Blesk.cz                    | Feed Parser   | ✅ Aktivní         | Bulvární noviny                    |
| Web          | Medium.seznam.cz            | Scrapy        | ✅ Aktivní         | Blogové články                     |
| API          | Sociologický ústav AVČR     | MediaWiki API | ✅ Aktivní         | Akademická výzkumná databáze       |
| API          | Wikipedia (Czech)           | MediaWiki API | ✅ Aktivní         | Encyklopedické články              |
| Search API   | Google News                 | Custom API    | ⏸️ Legacy          | Agregace novinek                   |
| Sociální API | Reddit                      | PRAW          | ✅ Nakonfigurováno | Komunitní diskuze                  |
| Sociální API | X (Twitter)                 | Tweepy        | ✅ Nakonfigurováno | Příspěvky na sociálních sítích     |

## 🧪 Testování

Spuštění komplexní testovací sady:

```bash
# Instalace testovacích závislostí
pip install pytest pytest-mock

# Spuštění všech testů
pytest testing/

# Spuštění specifického testu
pytest testing/test_nlp_analysis.py -v
```

## 📦 Závislosti

### Základní požadavky

- Python 3.10+
- Scrapy 2.13+
- SQLAlchemy 2.0+
- spaCy 3.7+
- transformers 4.52+
- pandas 2.3+

### API klienti

- praw 7.8+ (Reddit)
- tweepy 4.14+ (X/Twitter)
- requests 2.31+
- feedparser 6.0+

### Zpracování dat

- PyMuPDF 1.23+ (PDF)
- openpyxl (Excel)
- fuzzywuzzy 0.18+ (porovnávání textu)
- python-dotenv 1.0+ (prostředí)

### Vývoj

- pytest (testování)
- pyright (type checking)

## 📊 Výstupy

- **Databáze**: Strukturovaná data v PostgreSQL/SQLite s vztahy
- **CSV exporty**: Zpracovaná data v adresáři `export/csv/`
- **Power BI**: Přímá integrace přes `export/to_powerbi.py`
- **Analytické reporty**: NLP insights a entity vztahy
- **Logy**: Komplexní logování v `import_log.txt`

## 🛡️ Etické zásady

- ✅ Respektování robots.txt a rate limitů
- ✅ Správná identifikace user agenta
- ✅ Minimalizace dat a ochrana soukromí
- ✅ Atribuce zdrojů a transparentnost
- ✅ Akademické a výzkumné zaměření sběru dat
- ✅ Žádný sběr osobních dat bez souhlasu

## 🔧 Vývoj

### Kvalita kódu

- Type hinty v celém kódu
- Pylance/Pyright type checking
- Komplexní testové pokrytí
- Etické scraping praktiky
- Modulární architektura

### Přidání nových zdrojů

1. Přidání konfigurace do `extracting/sources_config.yaml`
2. Implementace spideru v adresáři `extracting/`
3. Přidání testů v adresáři `testing/`
4. Aktualizace main.py orchestrace

### Databázové schéma

Databáze používá SQLAlchemy ORM s následujícími hlavními entitami:

- **Source**: Články, příspěvky a dokumenty
- **Movement**: Náboženská hnutí a sekty
- **Alias**: Alternativní názvy pro hnutí
- **Location**: Geografické reference

## 📬 Budoucí vývoj

- [ ] Vylepšené NLP modely pro češtinu
- [ ] Monitorování sociálních médií v reálném čase
- [ ] Pokročilá analýza vztahů entit
- [ ] Geografická vizualizace hnutí
- [ ] Analýza trendů a časové řady
- [ ] REST API pro přístup k datům
- [ ] Web dashboard interface
- [ ] Rozšíření podpory více jazyků

---

Version: 2.1
Author: Adam Šeifert
License: MIT
Last updated: 2025-12-18

### Setting Up Social Media Sources

To enable Reddit and X (Twitter) data collection:

1. **Create `.env` file**

   ```bash
   cp .env.example .env
   ```

2. **Reddit API Setup**
   - Go to <https://www.reddit.com/prefs/apps>
   - Create a "script" application
   - Copy `client_id` and `client_secret` to `.env`:

     ```bash
     REDDIT_CLIENT_ID=your_client_id
     REDDIT_CLIENT_SECRET=your_client_secret
     REDDIT_USER_AGENT=ProjectInfinit/1.0 (by your_username)
     ```

3. **X/Twitter API Setup**
   - Register at <https://developer.twitter.com/>
   - Create an app with API v2 access
   - Copy Bearer Token to `.env`:

     ```bash
     X_BEARER_TOKEN=your_bearer_token
     ```

---

## Output Summary

- **Structured data:** PostgreSQL database
- **Processed files:** CSV exports in `export/csv/`
- **Dashboards:** Power BI visualization-ready
- **Reports:** Analysis results and statistics

---

**Version:** 2.1 | **Author:** Adam Seifert | **License:** MIT | **Updated:** 2025-02-13
