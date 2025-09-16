# 📘 project_infinit – Analýza nových náboženských hnutí v ČR

Tento projekt slouží ke sběru, analýze a vizualizaci informací o nových náboženských hnutích a sektách v České republice.

## 🗂️ Struktura

```
project_infinit/
├── scraping/         # Web scraping (Scrapy spidery)
├── processing/       # NLP, čištění, transformace
├── database/         # SQLAlchemy schéma + připojení
├── export/csv/       # Výstupní CSV soubory
├── data/pdf/         # Vložené PDF dokumenty
├── data/xlsx/        # Excel soubory ke konverzi
├── config.py         # Konfigurace databáze
├── main.py           # Hlavní orchestrátor ETL pipeline
└── venv/             # Virtuální prostředí Pythonu
```

---

## 🚀 Spuštění krok za krokem

### 1. Klonování a vytvoření prostředí

```bash
git clone <repo-url>
cd project_infinit
python -m venv venv
./venv/Scripts/activate      # Windows
# nebo
source venv/bin/activate     # Linux/macOS
```

### 2. Instalace závislostí

```bash
pip install -r requirements.txt
python -m stanza.download cs
```

### 3. Nastavení `config.py`

Vytvoř soubor `config.py`:

```python
DB_URI = "postgresql+psycopg2://username:password@localhost/nsm_db"
```

### 4. Spuštění hlavního skriptu

```bash
python main.py
```

Tím se provede celý ETL pipeline:

* scraping článků a dat
* převod XLSX → CSV
* zpracování PDF (NLP)
* import do databáze

---

## 📦 Závislosti

* Python 3.10+
* `Scrapy`
* `SQLAlchemy`, `psycopg2`
* `pandas`, `openpyxl`
* `stanza` (pro NLP v češtině)
* `PyMuPDF` (pro extrakci textu z PDF)

---

## 📊 Výstupy

Výsledky najdeš ve složce `export/csv/` nebo přímo v PostgreSQL.
Data je možné vizualizovat pomocí Power BI.

---

## 📬 Rozšíření do budoucna

* nové weby (další spidery)
* podpora dalších formátů (TXT, XML)
* analýza trendů, shrnutí, klasifikace článků
* mapová vizualizace + časové řady

---

Verze: 1.0
Autor: 

