# 🗄️ Database Migration Guide - New Schema

## Overview

Databáze byla kompletně přepracována s novým schématem pro lepší normalizaci a flexibilitu. Stará struktura (Source, Location, Movement s canonical_name) byla nahrazena zjednodušeným schématem s hvězdicovitou topologií.

## New Schema Architecture

```text
┌─────────────────┐
│    Articles     │  ←─ Centrální tabulka (obsah článků)
├─────────────────┤
│ id, title,      │
│ content, source,│
│ url, sentiment_ │
│ score, risk_    │
│ score, etc.     │
└────┬────────────┘
     │
     ├──M:N──→ Movements   (Hnutí/sekty)
     ├──M:N──→ Persons     (Osobnosti)
     └──M:N──→ Locations   (Místa)
```

## Database Tables

### 1. **articles** (Hlavní tabulka)

```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source VARCHAR(255),
    url VARCHAR(500) UNIQUE,
    sentiment_score NUMERIC(4,3),      -- -1 to 1
    sentiment_label sentiment_label_enum,  -- positive|neutral|negative
    risk_score NUMERIC(4,3),           -- 0 to 1
    risk_level risk_level_enum,         -- low|medium|high
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Poznámky:**
- `url` je UNIQUE pro zabránění duplikátům
- `sentiment_score` a `risk_score` se vyplňují během NLP analýzy
- Timestamps se automaticky vytvářejí

### 2. **movements** (Hnutí/sekty)
```sql
CREATE TABLE movements (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    alias VARCHAR(255),           -- Alternativní název
    category VARCHAR(100)          -- Typ hnutí
);
```

### 3. **persons** (Osobnosti)
```sql
CREATE TABLE persons (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    alias VARCHAR(255)            -- Alternativní jméno
);
```

### 4. **locations** (Místa)
```sql
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    country VARCHAR(100)          -- Země
);
```

### 5-7. **M:N Association Tables**
```sql
-- Linkování mezi Articles a Movements
CREATE TABLE article_movements (
    article_id INT REFERENCES articles(id) ON DELETE CASCADE,
    movement_id INT REFERENCES movements(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, movement_id)
);

-- Linkování mezi Articles a Persons
CREATE TABLE article_persons (
    article_id INT REFERENCES articles(id) ON DELETE CASCADE,
    person_id INT REFERENCES persons(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, person_id)
);

-- Linkování mezi Articles a Locations
CREATE TABLE article_locations (
    article_id INT REFERENCES articles(id) ON DELETE CASCADE,
    location_id INT REFERENCES locations(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, location_id)
);
```

## ENUM Types

```sql
CREATE TYPE sentiment_label_enum AS ENUM ('positive', 'neutral', 'negative');
CREATE TYPE risk_level_enum AS ENUM ('low', 'medium', 'high');
```

## Python API

### Quick Start

```python
from database.db_loader import DBConnector, Article
from processing.nlp_analysis import CzechTextAnalyzer

# Initialize
db = DBConnector()
db.create_tables()  # Vytvoří všechny tabulky

# Přidání hnutí
movement = db.add_movement('Fa-lun Kung', alias='Falun Gong', category='Asian spiritual')
movement_id = movement.id

# Přidání osobnosti
person = db.add_person('Jan Novak')
person_id = person.id

# Přidání lokace
location = db.add_location('Praha', country='Česká republika')
location_id = location.id

# Přidání článku
session = db.get_session()
article = Article(
    title='Nový článek',
    content='Obsah článku...',
    source='RSS',
    url='https://example.com/article'
)
session.add(article)
session.commit()
article_id = article.id
session.close()

# Linkování
db.link_article_movement(article_id, movement_id)
db.link_article_person(article_id, person_id)
db.link_article_location(article_id, location_id)

# NLP analýza
analyzer = CzechTextAnalyzer()
sentiment = analyzer.analyze_sentiment(text)
# Returns: {'score': float(-1 to 1), 'label': 'positive'|'neutral'|'negative'}

risk_score = analyzer.calculate_risk_score(text)
risk_level = analyzer.get_risk_level(risk_score)
# Returns: 'low'|'medium'|'high'

entities = analyzer.extract_named_entities(text)
# Returns: {'movements': [...], 'persons': [...], 'locations': [...]}
```

## ETL Pipeline

Nový `main.py` orchestruje celou pipeline:

```bash
python main.py
```

**Kroky:**
1. **create_db()** - Vytvoří databázové tabulky
2. **run_spiders()** - Spustí všechny web scrapery (RSS, API, sociální média)
3. **import_csv_data()** - Naimportuje CSV soubory do `articles` tabulky
4. **analyze_sentiment_and_risk()** - Spustí NLP analýzu sentiment/risk
5. **extract_entities()** - Extrahuje a linkuje hnutí, osobnosti, místa

## Migration from Old Database

### Postup:

1. **Smazat starou databázi** (vytvořenou v předchozí iteraci)
```bash
docker compose down -v  # Smaže všechny Docker volumes
```

2. **Spustit PostgreSQL znovu**
```bash
cd nnh-db
docker compose up -d
```

3. **Vytvořit nové tabulky**
```bash
python -c "from database.db_loader import DBConnector; DBConnector().create_tables()"
```

4. **Spustit novou pipeline**
```bash
python main.py
```

## Key Differences from Old Schema

| Aspekt | Staré schéma | Nové schéma |
|--------|-------------|-----------|
| Obsah | Source (s JSON) | Article (s normalizací) |
| Hnutí | Movement (canonical_name, description) | Movement (name, alias, category) |
| Lokace | Vložená v Source | Samostatná tabulka s M:N |
| Entity linking | Ruční mapování | Fuzzy matching + NER |
| Sentiment | Uloženo v Source | Normalizováno (-1 to 1) |
| Risk | Nebylo | risk_score + risk_level |

## Database Statistics

```python
db = DBConnector()
print(f"Articles: {db.get_article_count()}")
print(f"Movements: {db.get_movement_count()}")
print(f"Persons: {db.get_person_count()}")
print(f"Locations: {db.get_location_count()}")
```

## Testing

```bash
# Test imports
python -c "from database.db_loader import DBConnector; DBConnector().create_tables()"

# Test complete pipeline
python main.py

# Interactive testing
python
>>> from database.db_loader import DBConnector
>>> db = DBConnector()
>>> db.get_article_count()
0
```

## Troubleshooting

**Problem**: "FATAL: password authentication failed"
- **Fix**: Zkontroluj `config.py` nebo environment variables `DB_URI`

**Problem**: "Table already exists"
- **Fix**: To je OK - tabulky se při `create_tables()` nebudou duplikovat

**Problem**: "Foreign key constraint violated"
- **Fix**: Ujisti se, že movimento/osoba/lokace existují před linkováním

## Performance Tips

1. **Batch inserts** - Používej `db.bulk_insert_articles()` pro velké objemy
2. **Indexing** - Vytváří se automaticky na `url`, `name`, foreign keys
3. **Session management** - Zavírej session po práci: `session.close()`

## Next Steps

- Konfigurace NLP pipeline pro lepší entity extraction
- Přidání filtrů a analytických dotazů
- Integrace s PowerBI pro reporting
- Optimalizace fuzzy matchingu pro specifické kategorie
