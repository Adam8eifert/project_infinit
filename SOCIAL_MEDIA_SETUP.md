# 🌐 Sociální Média Setup - Project Infinit

Průvodce nastavením API klíčů pro sběr dat z Redditu.

## 🔐 Bezpečnost API klíčů

**⚠️ KRITICKÉ:** Nikdy nepushujte `.env` soubor s reálnými API klíči do gitu!

### Pravidla pro správu klíčů:

1. ✅ Zkopíruj `.env.example` na `.env`
2. ✅ Vyplň své reálné klíče v `.env`
3. ✅ Přidej `.env` do `.gitignore` (již je)
4. ✅ Sdílej `.env.example` bez hodnot (pro ostatní vývojáře)
5. ❌ Nikdy nepushuj `.env` s klíči
6. ❌ Nikdy nesikeuj klíče v dokumentaci

### Jak nastavit v CI/CD:

V GitHub Actions nebo jiném CI systému nastavte secret variables bez `.env` souboru:

```yaml
env:
  REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
  REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
  REDDIT_USER_AGENT: ProjectInfinit/1.0

```

---

## 📱 Reddit API Setup

### Krok 1: Přístup na Reddit Developer Portal

1. Jděte na https://www.reddit.com/prefs/apps
2. Musíte být přihlášeni na svůj Reddit účet

### Krok 2: Vytvoření aplikace

1. Klikněte na **"Create an application"** tlačítko
2. Zvolte název aplikace (např. `ProjectInfinit`)
3. Vyberte **"script"** jako typ aplikace
4. Vyplňte **"redirect uri"** (např. `http://localhost:8080` nebo `http://127.0.0.1`)
5. Přijměte podmínky a klikněte **"Create app"**

### Krok 3: Kopírování klíčů

Po vytvoření aplikace uvidíte:

```
personal use script (client_id): [dlouhý řetězec]
secret: [dlouhý řetězec]
```

Zkopíruj tyto hodnoty do `.env`:

```bash
REDDIT_CLIENT_ID=xxxxxxxxxxxxxxxxxx
REDDIT_CLIENT_SECRET=yyyyyyyyyyyyyyyyyyyy
REDDIT_USER_AGENT=ProjectInfinit/1.0 (by your_reddit_username)
```

### Krok 4: Testování připojení

```bash
python3 -c "
import praw
reddit = praw.Reddit(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    user_agent='ProjectInfinit/1.0 (by your_username)'
)
print('✅ Reddit API připojeno')
print(f'Authenticated user: {reddit.user.me()}')
"
```

### Reddit API Limity

- **Rate limit**: 60 requestů za minutu
- **Limit na IP**: 1 request za 2 sekundy
- **Timeout**: Pokud překročíš limit, čekej 10 minut

Náš spider automaticky dodržuje tyto limity.

---

---

## 🔄 Spuštění Sociálních Médií Spiderů

### Spuštění všech spiderů (včetně sociálních médií)

```bash
python main.py
```

### Spuštění jen Reddit spideru

```bash
scrapy runspider scraping/social_media_spider.py
```

### Spuštění se debug logem

```bash
SCRAPY_LOGLEVEL=DEBUG scrapy runspider scraping/social_media_spider.py
```

---

## 🧪 Testování Social Media Spiderů

Všechny testy jsou mockované a nevyžadují skutečné API klíče:

```bash
# Spustit všechny testy
pytest -v testing/test_social_media_spider.py

# Spustit jen Reddit testy
pytest -v testing/test_social_media_spider.py::TestRedditSpider

# S coverage reportem
pytest --cov=scraping.social_media_spider testing/test_social_media_spider.py
```

---

## ⚙️ Konfigurace Sociálních Médií

Konfiguraci spravujete v `scraping/sources_config.yaml`:

### Reddit Konfigurace

```yaml
reddit:
  name: Reddit
  description: Czech subreddits about religious movements
  type: social_api
  api_method: search
  url: https://www.reddit.com
  
  # Povolené subreddity
  subreddits:
    - r/occult
    - r/spirituality
    - r/religion
    - r/cults
  
  # Hledané klíčové slova
  search_terms:
    - sekta
    - kult
    - "nové náboženské hnutí"
    - spirituální hnutí
  
  # Parametry API
  api_params:
    sort: new
    t: month
    limit: 50
  
  # API klíče (nahraď placeholdery)
  auth:
    client_id: ${REDDIT_CLIENT_ID}
    client_secret: ${REDDIT_CLIENT_SECRET}
    user_agent: ProjectInfinit/1.0
```

---

## 🐛 Troubleshooting

### Reddit

**Chyba: "Invalid Client ID"**
- Zkontrolujte, že máte správný `client_id` a `client_secret`
- Ujistěte se, že máte správný `user_agent`
- Znovu vygenerujte klíče na https://www.reddit.com/prefs/apps

**Chyba: "401 Unauthorized"**
- Zkontrolujte env proměnné:
  ```bash
  echo $REDDIT_CLIENT_ID
  echo $REDDIT_CLIENT_SECRET
  ```

**Příliš mnoho requetů (429)**
- Vyčkejte 10+ minut
- Spider má vestavěný retry mechanismus

### Obecné

**Chyba: "No module named praw"**
```bash
pip install -r requirements.txt
```

**`.env` soubor se nenačítá**
- Ujistěte se, že je `.env` v root adresáři projektu
- Ujistěte se, že není v `.gitignore` (měl by být!)
- Restartujte terminál po vytvoření `.env`

---

## 📊 Výstupy

Příspěvky jsou uloženy do CSV souboru:

```bash
export/csv/reddit_raw.csv
```

Struktura dat:

```csv
source_name,source_type,title,url,text,scraped_at,author,created,score/metrics
```

---

## 🔗 Užitečné Linky

- **Reddit Developer Docs**: https://www.reddit.com/dev/api/
- **PRAW Documentation**: https://praw.readthedocs.io/

---

# 📺 YouTube Data API v3 Setup

## Krok 1: Google Cloud Console

1. Jděte na https://console.cloud.google.com/
2. Vytvořte nový projekt nebo vyberte existující
3. Pojmenujte projekt (např. "NRM Research")

## Krok 2: Aktivace YouTube Data API

1. V konzoli přejděte na **"APIs & Services"** > **"Library"**
2. Vyhledejte **"YouTube Data API v3"**
3. Klikněte na **"Enable"**

## Krok 3: Vytvoření API klíče

1. Přejděte na **"APIs & Services"** > **"Credentials"**
2. Klikněte **"Create Credentials"** > **"API Key"**
3. Zkopírujte API klíč
4. (Doporučeno) Omezit klíč:
   - Klikněte **"Edit API key"**
   - V sekci **"API restrictions"** vyberte **"Restrict key"**
   - Zaškrtněte pouze **"YouTube Data API v3"**

## Konfigurace v `.env`

```bash
YOUTUBE_API_KEY="váš_youtube_api_klíč"
```

## Kvóty a limity

- **Denní kvóta**: 10,000 jednotek zdarma
- **Vyhledávání**: 100 jednotek/dotaz
- **Video details**: 1 jednotka/dotaz
- **Sledování kvóty**: Google Cloud Console > APIs & Services > Dashboard

**Tip**: Pokud potřebujete více kvóty, můžete požádat o navýšení přes formulář v konzoli.

---

# 📨 Telegram API Setup

## Krok 1: Registrace Telegram aplikace

1. Jděte na https://my.telegram.org/auth
2. Přihlaste se telefonním číslem (obdržete SMS kód)
3. Přejděte na **"API development tools"**
4. Vyplňte formulář:
   - **App title**: NRM Research
   - **Short name**: nrm_research
   - **Platform**: Other
5. Klikněte **"Create application"**
6. Zkopírujte **api_id** a **api_hash**

## Krok 2: První připojení

Při prvním spuštění Telegram spideru budete vyzváni k zadání:
- Telefonního čísla
- Ověřovacího kódu (přijde přes Telegram app)

To vytvoří `telegram_session.session` soubor pro budoucí připojení.

## Konfigurace v `.env`

```bash
TELEGRAM_API_ID="váš_api_id"
TELEGRAM_API_HASH="váš_api_hash"
TELEGRAM_PHONE="+420..."  # Váš telefon
```

## Bezpečnostní pravidla

- ⚠️ Přidejte `telegram_session.session*` do `.gitignore`
- ⚠️ Nikdy nesdílejte session soubory (obsahují přístupové tokeny)
- ✅ Rate limiting: ~1-2 požadavky/sekundu (API nemá oficiální limit, ale buďte opatrní)

---

# 🐘 Mastodon API Setup

Mastodon je decentralizovaná síť - potřebujete kredenciály pro každou instanci zvlášť.

## Metoda A: Přes webové rozhraní (doporučeno)

1. Přihlaste se na Mastodon instanci (např. https://mastodon.social)
2. Přejděte na **Settings** > **Development** > **New Application**
3. Vyplňte:
   - **Application name**: NRM Research
   - **Scopes**: Zaškrtněte `read:statuses`, `read:search`
4. Klikněte **"Submit"**
5. Zkopírujte **Access token**

## Metoda B: Programaticky

```python
from mastodon import Mastodon

# Registrace aplikace
Mastodon.create_app(
    'NRM Research Bot',
    api_base_url='https://mastodon.social',
    to_file='mastodon_clientcred.secret'
)

# Získání tokenu
mastodon = Mastodon(client_id='mastodon_clientcred.secret')
mastodon.log_in(
    'vas_email@example.com',
    'vase_heslo',
    to_file='mastodon_usercred.secret'
)
```

## Konfigurace v `.env`

```bash
MASTODON_ACCESS_TOKEN="váš_access_token"
MASTODON_API_BASE_URL="https://mastodon.social"
```

## České a relevantní instance

- https://mastodon.social (globální hlavní instance)
- https://mas.to (evropská instance)
- Hledejte české instance na https://instances.social/

## Rate limity

- Typicky **300 požadavků / 5 minut** (liší se podle instance)
- Sledujte `X-RateLimit-*` headery v odpovědích

---

# 📈 Google Trends Setup

## 🎉 Žádné API klíče potřeba!

Google Trends přes knihovnu `pytrends` funguje **bez autentizace**.

## Instalace

```bash
pip install pytrends
```

## Použití

```python
from pytrends.request import TrendReq

pytrends = TrendReq(hl='cs-CZ', tz=60)
```

## Limity

- **Rate limiting**: Přibližně 1 požadavek/sekundu
- Google může dočasně blokovat při příliš rychlých dotazech
- Implementujte pauzy mezi dotazy (v kódu už je `time.sleep(2)`)

## Tipy pro reliable sběr

- Neposílejte dotazy rychleji než 1/sekundu
- Při chybě "429 Too Many Requests" čekejte 15-30 minut
- Používejte time.sleep() mezi dávkami dotazů
- Monitorujte logy a přizpůsobte frekvenci

---

# 🧪 Testování Připojení

## Reddit Test

```bash
python -c "
from scraping.reddit_spider import RedditSpider
spider = RedditSpider()
print('Reddit OK:', spider.reddit.user.me())
"
```

## YouTube Test

```bash
python -c "
from scraping.youtube_spider import YouTubeSpider
spider = YouTubeSpider()
results = spider.search_videos('scientologie', max_results=1)
print('YouTube OK:', len(results), 'video found')
"
```

## Telegram Test

```bash
python scraping/telegram_spider.py
# Při prvním spuštění budete vyzváni k zadání telefonu a kódu
```

## Mastodon Test

```bash
python -c "
from scraping.mastodon_spider import MastodonSpider
spider = MastodonSpider()
posts = spider.search_hashtag('cult', limit=1)
print('Mastodon OK:', len(posts), 'post found')
"
```

## Google Trends Test

```bash
python -c "
from trends.google_trends_collector import GoogleTrendsCollector
collector = GoogleTrendsCollector()
data = collector.collect_trend_data('scientologie', timeframe='today 1-m')
print('Google Trends OK:', len(data), 'data points')
"
```

---

# ✅ Kompletní Checklist

## Před prvním spuštěním

- [ ] Reddit: API klíče v `.env`
- [ ] YouTube: API klíč v `.env` + API aktivováno v Google Cloud
- [ ] Telegram: API credentials v `.env` + první připojení dokončeno
- [ ] Mastodon: Access token v `.env`
- [ ] Google Trends: knihovna `pytrends` nainstalována
- [ ] `.env` soubor přidán do `.gitignore`
- [ ] Session soubory Telegramu v `.gitignore`
- [ ] Všechny balíčky nainstalovány: `pip install praw google-api-python-client telethon Mastodon.py pytrends python-dotenv`

## Testování

- [ ] Reddit test úspěšný
- [ ] YouTube test úspěšný
- [ ] Telegram test úspěšný (session vytvořen)
- [ ] Mastodon test úspěšný
- [ ] Google Trends test úspěšný

## Databáze

- [ ] Migrace 006 aplikována: `psql -f database/migrations/006_add_social_media_and_trends.sql`
- [ ] Tabulky vytvořeny: `social_media_posts`, `google_trends`

---

# 📚 Další Dokumentace

- **Hlavní README**: [readme.md](readme.md)
- **Databázové schéma**: [database/schema.sql](database/schema.sql)
- **GitHub Copilot instrukce**: [.github/copilot-instructions.md](.github/copilot-instructions.md)

---

**Last Updated**: 2026-03-18 (Extended with YouTube, Telegram, Mastodon, Google Trends)
**Verze**: 2.0
