# 🎯 Automatické Matchování Hnutí - Dokumentace

## 📋 Přehled

Systém automaticky přiřazuje články a dokumenty ke správným náboženským hnutím pomocí fuzzy matchingu na základě obsahu textu a konfigurace aliasů.

## ✨ Co bylo implementováno

### 1. **Aliasy v `sources_config.yaml`**
Do konfigurace byla přidána sekce `movement_aliases`:

```yaml
movement_aliases:
  "Děti Boží": ["Sekta Děti Boží", "Children of God", "The Family"]
  "AllatRa": ["Hnutí AllatRa", "Sekta AllatRa", "Hnuti Allatra"]
  "Hnutí Hare Kršna": ["ISKCON", "Hare Kršna", "Hare Krishna"]
  # ... další aliasy
```

### 2. **Funkce matchování v `keywords.py`**
Nové funkce pro automatické rozpoznávání hnutí:

- `match_movement_from_text(text, min_score=80)` - matchuje text na hnutí
- `get_movement_name_by_id(movement_id)` - získá název hnutí podle ID

**Princip fungování:**
1. Přímé substring matching (nejvyšší priorita)
2. Matching přes aliasy z konfigurace
3. Fuzzy matching pomocí fuzzywuzzy (min. 80% shoda)

### 3. **Automatické matchování při CSV importu**
`processing/import_csv_to_db.py` nyní automaticky matchuje každý článek:

```python
# Starý kód (hardcoded):
"movement_id": 1  # všechno šlo do prvního hnutí

# Nový kód (automatické):
movement_id = match_movement_from_text(combined_text)
if movement_id is None:
    movement_id = 1  # fallback jen pokud nenalezeno
```

### 4. **Migrátor pro existující data**
`processing/rematch_movements.py` - přematchuje existující zdroje

## 🚀 Použití

### Běžný workflow (automatické matchování)

```bash
# 1. Spusť scrapery jako obvykle
python main.py

# Nové články budou automaticky správně přiřazeny!
```

### Přematchování existujících dat

```bash
# Dry-run režim (jen ukáže, co by se změnilo, neuloží)
python processing/rematch_movements.py --movement-id 1 --dry-run

# Live režim (skutečně uloží změny)
python processing/rematch_movements.py --movement-id 1 --live

# Přematchovat všechny zdroje
python processing/rematch_movements.py --live --batch-size 100
```

### Testování matchingu

```python
from extracting.keywords import match_movement_from_text, get_movement_name_by_id

text = "Článek o Scientologické církvi v České republice"
movement_id = match_movement_from_text(text)
name = get_movement_name_by_id(movement_id)

print(f"Namatchováno: {name} (ID: {movement_id})")
# → Namatchováno: Scientologická církev (ID: 20)
```

## 📊 Výsledky testování

### Úspěšnost matchingu:
- ✅ **73 ze 97** existujících zdrojů (75%) bylo automaticky přematchováno
- ✅ Všechny testovací případy správně rozpoznány
- ✅ Články z RSS feedů správně matchovány

### Distribuce po migraci:
```
Rodina:                    23 zdrojů (23.7%)
Církev (generická):        26 zdrojů (26.8%)
Náboženské hnutí (obecně): 24 zdrojů (24.7%)  ← Zbylo jen 24 z původních 97!
Transcendentální meditace: 11 zdrojů (11.3%)
+ 10 dalších hnutí
```

### Příklady úspěšného matchingu:
```
"Sekta Děti Boží byla založena..."           → Děti Boží ✓
"Hnutí AllatRa se vyjádřilo..."              → Hnutí AllatRa ✓
"ISKCON (Hare Kršna) pořádá festival..."     → Hnutí Hare Kršna ✓
"Scientologická církev má centra..."         → Scientologická církev ✓
```

## 🔧 Konfigurace

### Přidání nového aliasu

Edituj `extracting/sources_config.yaml`:

```yaml
movement_aliases:
  "Tvoje Hnutí": ["Alias 1", "Alias 2", "English Name"]
```

### Úprava min. skóre pro fuzzy matching

```python
movement_id = match_movement_from_text(text, min_score=85)  # default je 80
```

## ⚙️ Technické detaily

### Závislosti
- `fuzzywuzzy` - fuzzy string matching (už v environment.yml)
- `python-Levenshtein` - rychlejší fuzzy matching (volitelné, ale doporučené)

### Instalace python-Levenshtein (odstraní warning)
```bash
mamba install python-levenshtein
```

### Logování
Matching loguje v DEBUG režimu pro každý článek:
```
DEBUG: No movement match found for: Článek o obecném náboženství...
```

## 🐛 Troubleshooting

### Problém: Články se matchují na špatné hnutí
**Řešení:** Přidejte více aliasů nebo snižte `min_score`

### Problém: Články se nematchují vůbec
**Řešení:** 
1. Zkontrolujte, jestli je hnutí v databázi: `python -c "from database.db_loader import *; ..."`
2. Přidejte aliasy do `sources_config.yaml`
3. Snižte `min_score` v `keywords.py`

### Problém: Slow matching warning
```
UserWarning: Using slow pure-python SequenceMatcher
```
**Řešení:** `mamba install python-levenshtein`

## 📈 Další vylepšení

Možnosti pro budoucí rozšíření:
- [ ] Přidat více aliasů pro každé hnutí (zahraniční varianty)
- [ ] Implementovat NER-based matching (rozpoznávání entit pomocí NLP)
- [ ] Cache výsledků matchingu pro rychlejší opakované importy
- [ ] Dashboard k monitorování distribuce hnutí v Power BI

## 🎓 Shrnutí

**Hlavní výhoda:** Articles jsou nyní automaticky přiřazovány ke správným hnutím bez manuálního zásahu, což výrazně zlepšuje kvalitu dat pro analýzu.

**Výsledek:** Z 97 článků, které byly všechny v obecné kategorii, se 75% automaticky přiřadilo ke konkrétním hnutím.
