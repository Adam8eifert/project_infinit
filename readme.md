# 📘 Project Infinit - Analysis of New Religious Movements in the Czech Republic

An ETL pipeline for collecting, analyzing, and visualizing information about new religious movements in the Czech Republic. Features ethical web scraping, NLP analysis, fuzzy entity matching, and structured data storage.

**License:** GNU General Public License v3.0 (GPLv3)

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
  - **Fuzzy entity matching**: 70% similarity threshold with 4-tier matching (direct name → direct alias → fuzzy name → fuzzy alias)
  - Movement classification and relationship analysis
  - Academic document processing (PDF, DOC, DOCX text extraction)
  - **139 known religious movements** with alias matching
- Structured data storage in PostgreSQL/SQLite
- Export capabilities for further analysis and Power BI integration
- Comprehensive testing suite with pytest
- Type-safe code with Pylance/Pyright integration

## 🔧 Technology Stack

### Core Technologies

- **Python 3.10+** - Core programming language
- **Mamba/Conda** - Package and environment management
- **PostgreSQL** - Primary database (with SQLite support)

### Web Scraping

- **Scrapy 2.14+** - Web scraping framework with ethical settings
- **Scrapy-Playwright 0.0.46+** - JavaScript-rendered page scraping (iDNES archiv)
- **Feedparser 6.0+** - RSS/Atom feed parsing
- **Requests 2.31+** - HTTP library

### Natural Language Processing

- **Stanza 1.8+** - Czech language NLP pipeline (tokenization, POS, NER, lemmatization)
- **Hugging Face Transformers 4.52+** - Advanced NLP models for sentiment analysis
- **spaCy 3.7+** (legacy) - Alternative NLP toolkit

### Data Processing

- **SQLAlchemy 2.0+** - Database ORM with PostgreSQL/SQLite support
- **pandas 2.3+** - Data manipulation and CSV processing
- **PyMuPDF (fitz) 1.23+** - PDF text extraction
- **python-docx 1.1+** - Word document processing (.doc, .docx)
- **FuzzyWuzzy 0.18+** - Fuzzy string matching for entity resolution

### API Clients (Dependencies)

- **PRAW 7.8+** - Reddit API client
- **Tweepy 4.14+** - X (Twitter) API client

### Development & Testing

- **pytest** - Testing framework with mocking
- **Pyright/Pylance** - Type checking and IDE support
- **PyYAML** - Configuration management
- **python-dotenv 1.0+** - Environment variable management

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
│   ├── manual_csv.py         # Manual CSV processing utilities
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
│   ├── DEDUPLICATION_README.md # Deduplication documentation
│   ├── migrate_analytics.py # Analytics migration script
│   ├── migrations/          # Database migrations
│   └── __pycache__/         # Python bytecode
├── testing/               # Test suite
│   ├── test_*.py           # Unit tests for all modules
│   ├── conftest.py         # Pytest configuration
│   ├── README.md           # Testing documentation
│   └── __pycache__/         # Python bytecode
├── export/                # Output files and exports
│   ├── csv/               # Scraped and processed CSV data
│   └── to_powerbi.py      # Power BI export utilities
├── data/                  # Application data directory
├── academic_data/         # Academic documents (PDF, DOC, DOCX)
│   └── README.md          # Academic data documentation
├── csv_manual/            # Manual CSV imports
│   └── README.md          # Manual CSV documentation
├── nnh-db/                # Docker database setup
│   ├── docker             # Docker files
│   └── docker-compose.yml # Docker Compose configuration
├── .github/               # GitHub configuration
│   └── copilot-instructions.md # AI assistant instructions
├── config.py              # Database and app configuration
├── config_loader.py       # Configuration loader utility
├── csv_utils.py           # CSV utility functions
├── main.py                # Main ETL orchestrator
├── seed_movements.py      # Seed movements and aliases utility
├── environment.yml        # Conda/Mamba environment
├── pyrightconfig.json    # Pyright type checking config
├── .gitignore             # Git ignore patterns
├── LICENSE                # Project license
├── SOCIAL_MEDIA_SETUP.md  # Social media API setup guide
└── readme.md             # This file
```

## 🚀 Quick Start

### 1. Clone and Setup Environment

#### Option A: Using Mamba/Conda (Recommended)

```bash
git clone https://github.com/Adam8eifert/project_infinit.git
cd project_infinit

# Create Conda environment from environment.yml
mamba create -n project_infinit -y --file environment.yml
# or with conda:
# conda env create -f environment.yml

# Activate environment
mamba activate project_infinit
# or: conda activate project_infinit
```

**Note:** This project uses Conda/Mamba exclusively. Traditional pip/venv setup is not supported due to complex dependencies (Playwright, Stanza models, etc.).

### 2. Setup NLP Models and Dependencies

```bash
# Download Stanza Czech model (primary NLP pipeline)
python -c "import stanza; stanza.download('cs')"

# Optional: Download spaCy Czech model (legacy support)
python -m spacy download cs_core_news_md
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
| RSS        | iDNES.cz - Domácí           | Feed Parser   | ✅ Active     | Czech mainstream news        |
| RSS        | Český rozhlas (iRozhlas.cz) | Feed Parser   | ✅ Active     | Public radio news            |
| RSS        | Aktuálně.cz                 | Feed Parser   | ✅ Active     | Czech news website           |
| RSS        | Forum24.cz                  | Feed Parser   | ✅ Active     | Discussion forum             |
| RSS        | Deník Alarm                 | Feed Parser   | ✅ Active     | Investigative journalism     |
| RSS        | Blesk.cz                    | Feed Parser   | ✅ Active     | Tabloid news                 |
| Web        | iDNES archiv (Playwright)   | Scrapy        | 🚧 Blocked    | Sekty-kulty-mesiáši section  |
| Web        | Medium.seznam.cz            | Scrapy        | ✅ Active     | Blog articles                |
| API        | Sociologický ústav AVČR     | MediaWiki API | ✅ Active     | Academic research database   |
| API        | Wikipedia (Czech)           | MediaWiki API | ✅ Active     | Encyclopedia articles        |
| Search API | Google News                 | Custom API    | ⏸️ Legacy     | News aggregation             |
| Social API | Reddit                      | PRAW          | ✅ Configured | Community discussions        |
| Social API | X (Twitter)                 | Tweepy        | ✅ Configured | Social media posts           |

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test dependencies are in environment.yml
mamba activate project_infinit

# Run all tests
pytest testing/

# Run specific test
pytest testing/test_nlp_analysis.py -v

# Test fuzzy matching (70% threshold)
pytest testing/test_keywords.py -v
```

## 📦 Dependencies

### Core Requirements

- Python 3.10.19+
- Scrapy 2.14+
- SQLAlchemy 2.0+
- Stanza 1.8+ (primary NLP)
- Hugging Face Transformers 4.52+
- pandas 2.3+

### NLP & Text Processing

- stanza 1.8+ (Primary: Czech/English NLP - tokenization, POS, NER, lemmatization)
- transformers 4.52+ (sentiment analysis: multilingual BERT)
- langdetect (automatic language detection)
- FuzzyWuzzy + Levenshtein (70% threshold fuzzy matching for 139 movements)
- spaCy 3.7+ (optional legacy support)

### API Clients

- praw 7.8+ (Reddit)
- tweepy 4.14+ (X/Twitter)
- requests 2.31+
- feedparser 6.0+

### Data Processing & NLP

- PyMuPDF (fitz) 1.23+ (PDF text extraction)
- python-docx 1.1+ (Word documents: .doc, .docx)
- openpyxl (Excel)
- fuzzywuzzy 0.18+ (fuzzy string matching)
- python-Levenshtein (fast string matching)
- python-dotenv 1.0+ (environment variables)

### Database

- psycopg2-binary 2.9+ (PostgreSQL adapter)
- SQLAlchemy 2.0+

### Development

- pytest 8.0+ (testing)
- pytest-mock (test mocking)
- pyright (type checking)
- pylance (IDE support)

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
  - **Fuzzy matching entit**: Prahová hodnota 70% s 4-úrovňovým matchováním
  - Klasifikace hnutí a analýza vztahů
  - **139 známých náboženských hnutí** s aliasovým matchováním
- Strukturované ukládání dat v PostgreSQL/SQLite
- Exportní možnosti pro další analýzu a Power BI integraci
- Komplexní testovací sada s pytest
- Type-safe kód s Pylance/Pyright integrací

## 🔧 Technologický stack

### Základní technologie (detail)

- **Python 3.10+** - Základní programovací jazyk
- **Mamba/Conda** - Správa balíčků a prostředí
- **PostgreSQL** - Primární databáze (s podporou SQLite)

### Web Scraping (CZ)

- **Scrapy 2.14+** - Framework pro web scraping s etickými nastaveními
- **Scrapy-Playwright 0.0.46+** - Scraping stránek s JavaScriptem (iDNES archiv)
- **Feedparser 6.0+** - Parsování RSS/Atom feedů
- **Requests 2.31+** - HTTP knihovna

### Zpracování přirozeného jazyka

- **Stanza 1.8+** - České NLP pipeline (tokenizace, POS, NER, lemmatizace)
- **Hugging Face Transformers 4.52+** - Pokročilé NLP modely pro analýzu sentimentu
- **spaCy 3.7+** (legacy) - Alternativní NLP toolkit

### Zpracování dat

- **SQLAlchemy 2.0+** - Database ORM s podporou PostgreSQL/SQLite
- **pandas 2.3+** - Manipulace s daty a CSV zpracování
- **PyMuPDF (fitz) 1.23+** - Extrakce textu z PDF
- **python-docx 1.1+** - Zpracování Word dokumentů (.doc, .docx)
- **FuzzyWuzzy 0.18+ + Levenshtein** - Fuzzy porovnávání řetězců (70% threshold pro 139 hnutí)

### API klienti (detail)

- **PRAW 7.8+** - Reddit API klient
- **Tweepy 4.14+** - X (Twitter) API klient

### Vývoj a testování

- **pytest** - Testovací framework s mocking
- **Pyright/Pylance** - Type checking a IDE podpora
- **PyYAML** - Správa konfigurace
- **python-dotenv 1.0+** - Správa environment proměnných

## 🗂️ Struktura projektu

```text
project_infinit/
├── extracting/              # Web scrapery a konfigurace
│   ├── sources_config.yaml    # Centralizovaná konfigurace zdrojů
│   ├── spider_settings.py     # Etická scraping nastavení
│   ├── keywords.py           # Utility pro filtrování klíčových slov
│   ├── config_loader.py      # Načítání YAML konfigurace
│   ├── rss_spider.py        # Univerzální RSS feed scraper
│   ├── api_spider.py        # Univerzální API scraper
│   ├── social_media_spider.py # Social media API scraper
│   ├── google_spider.py     # Google News scraper
│   ├── medium_seznam_spider.py # Medium/Seznam scraper
│   └── __pycache__/         # Python bytecode
├── processing/            # Zpracování a analýza dat
│   ├── nlp_analysis.py       # NLP pipeline s podporou češtiny
│   ├── import_csv_to_db.py   # Utility pro import CSV do databáze
│   ├── import_pdf_to_db.py   # Zpracování a import PDF
│   ├── manual_csv.py         # Manuální zpracování CSV
│   └── __pycache__/         # Python bytecode
├── database/              # Databázová vrstva
│   ├── db_loader.py          # SQLAlchemy modely a připojení
│   ├── models/              # Databázové modely
│   │   ├── source.py        # Model zdrojů
│   │   ├── movement.py      # Model hnutí
│   │   ├── alias.py         # Model aliasů
│   │   └── location.py      # Model lokací
│   ├── schema.sql           # Databázové schéma
│   ├── views.sql            # Databázové views
│   ├── migrations/          # Databázové migrace
│   └── __pycache__/         # Python bytecode
├── testing/               # Testovací sada
│   ├── test_*.py           # Unit testy pro všechny moduly
│   ├── conftest.py         # Pytest konfigurace
│   └── README.md           # Dokumentace testování
├── export/                # Výstupní soubory a exporty
│   ├── csv/               # Scraped a zpracovaná CSV data
│   └── to_powerbi.py      # Utility pro Power BI export
├── data/                  # Aplikační data
├── academic_data/         # Akademické dokumenty (PDF, DOC, DOCX)
│   └── README.md          # Dokumentace akademických dat
├── csv_manual/            # Manuální CSV importy
│   └── README.md          # Dokumentace manuálních CSV
├── nnh-db/                # Docker databázové nastavení
├── .github/               # GitHub konfigurace
├── config.py              # Konfigurace databáze a aplikace
├── main.py                # Hlavní ETL orchestrátor
├── seed_movements.py      # Utility pro seed hnutí a aliasů
├── environment.yml        # Conda/Mamba prostředí
├── pyrightconfig.json    # Konfigurace Pyright type checking
└── readme.md             # Tento soubor
```

## 🇨🇿 Rychlý start (CZ)

### 1a. Klonování a příprava prostředí (CZ)

#### Možnost A: Použití Mamba/Conda (Doporučeno)

```bash
git clone https://github.com/Adam8eifert/project_infinit.git
cd project_infinit

# Vytvoření Conda prostředí z environment.yml
mamba create -n project_infinit -y --file environment.yml
# nebo s conda:
# conda env create -f environment.yml

# Aktivace prostředí
mamba activate project_infinit
# nebo: conda activate project_infinit
```

**Poznámka:** Projekt využívá výhradně Conda/Mamba. Tradiční pip/venv setup není podporován kvůli komplexním závislostem (Playwright, Stanza modely, atd.).

### 2. Nastavení NLP a závislostí

Stanza automaticky stáhne české a anglické modely při prvním spuštění:

```bash
# Stažení Stanza českého modelu (primární NLP pipeline)
python -c "import stanza; stanza.download('cs')"

# Volitelné: Stažení spaCy českého modelu (legacy podpora)
python -m spacy download cs_core_news_md
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

## 🇨🇿 Technologický stack a architektura (CZ)

### Základní technologie

- **Python 3.10+** – Hlavní jazyk
- **Stanza 1.11+** – Multijazykový NLP (čeština + angličtina) s automatickou detencí jazyka
- **langdetect** – Automatická detekce jazyka zdrojů
- **Transformers (HuggingFace)** – Multilingual BERT pro sentiment analýzu
- **SQLAlchemy 2.0+** – ORM pro PostgreSQL/SQLite
- **Scrapy 2.13+** – Framework pro web scraping (5 spiderů)
- **PyMuPDF 1.23+** – Extrakce textu z PDF dokumentů
- **python-docx 1.1+** – Čtení DOC/DOCX souborů

### Konfigurace

Veškerá konfigurace je centralizována v `extracting/sources_config.yaml`:

- Definice zdrojů (RSS, API, webscraping)
- NLP klíčová slova a vzory
- Known movements (75+ českých NRM)
- Rate limiting a nastavení scraperu

Načítání konfigurace probíhá přes `extracting/keywords.py` wrapper se automatickou validací.

## 🇨🇿 Kroky ETL Pipeline (CZ)

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
| RSS          | iDNES.cz - Domácí           | Feed Parser   | ✅ Aktivní         | Hlavní české zprávy                |
| RSS          | Český rozhlas (iRozhlas.cz) | Feed Parser   | ✅ Aktivní         | Veřejnoprávní rozhlasové noviny    |
| RSS          | Aktuálně.cz                 | Feed Parser   | ✅ Aktivní         | České zpravodajské stránky         |
| RSS          | Forum24.cz                  | Feed Parser   | ✅ Aktivní         | Diskuzní fórum                     |
| RSS          | Deník Alarm                 | Feed Parser   | ✅ Aktivní         | Investigativní žurnalistika        |
| RSS          | Blesk.cz                    | Feed Parser   | ✅ Aktivní         | Bulvární noviny                    |
| Web          | iDNES archiv (Playwright)   | Scrapy        | 🚧 Blokováno      | Sekce Sekty-kulty-mesiáši          |
| Web          | Medium.seznam.cz            | Scrapy        | ✅ Aktivní         | Blogové články                     |
| API          | Sociologický ústav AVČR     | MediaWiki API | ✅ Aktivní         | Akademická výzkumná databáze       |
| API          | Wikipedia (Czech)           | MediaWiki API | ✅ Aktivní         | Encyklopedické články              |
| Search API   | Google News                 | Custom API    | ⏸️ Legacy          | Agregace novinek                   |
| Sociální API | Reddit                      | PRAW          | ✅ Nakonfigurováno | Komunitní diskuze                  |
| Sociální API | X (Twitter)                 | Tweepy        | ✅ Nakonfigurováno | Příspěvky na sociálních sítích     |

## 🧪 Testování

Spuštění komplexní testovací sady:

```bash
# Testovací závislosti jsou v environment.yml
mamba activate project_infinit

# Spuštění všech testů
pytest testing/

# Spuštění specifického testu
pytest testing/test_nlp_analysis.py -v

# Test fuzzy matchingu (70% threshold)
pytest testing/test_keywords.py -v
```

## 📦 Závislosti

### Základní požadavky

- Python 3.10.19+
- Scrapy 2.14+
- SQLAlchemy 2.0+
- Stanza 1.8+ (primární NLP)
- Hugging Face Transformers 4.52+
- pandas 2.3+

### NLP & Zpracování textu

- stanza 1.8+ (české NLP: tokenizace, POS, NER, lemmatizace)
- transformers 4.52+ (analýza sentimentu: WikiNeuralNER)
- spaCy 3.7+ (legacy podpora)

### API klienti (minimální)

- praw 7.8+ (Reddit)
- tweepy 4.14+ (X/Twitter)
- requests 2.31+
- feedparser 6.0+

### Zpracování dat (detail)

- PyMuPDF (fitz) 1.23+ (extrakce textu z PDF)
- python-docx 1.1+ (Word dokumenty: .doc, .docx)
- openpyxl (Excel)
- fuzzywuzzy 0.18+ (fuzzy porovnávání řetězců)
- python-Levenshtein (rychlé porovnávání řetězců)
- python-dotenv 1.0+ (environment proměnné)

### Databáze

- psycopg2-binary 2.9+ (PostgreSQL adapter)
- SQLAlchemy 2.0+

### Vývoj

- pytest 8.0+ (testování)
- pytest-mock (test mocking)
- pyright (type checking)
- pylance (IDE podpora)

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

**Version:** 2.3 | **Author:** Adam Seifert | **License:** GNU General Public License v3.0 | **Updated:** 2026-02-25
