# 🌐 Sociální Média Setup - Project Infinit

Průvodce nastavením API klíčů pro sběr dat z Redditu a X (Twitter).

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
  X_BEARER_TOKEN: ${{ secrets.X_BEARER_TOKEN }}
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

## 🐦 X (Twitter) API v2 Setup

### Krok 1: Developer Account Setup

1. Jděte na https://developer.twitter.com/
2. Klikněte **"Sign up"** nebo **"Sign in"**
3. Vyplňte formulář s detaily o vašem projektu
4. Proveďte ověření e-mailu

### Krok 2: Vytvoření aplikace

1. V Developer Portal jděte na **"Apps"**
2. Klikněte **"Create an app"**
3. Zvolte název aplikace (např. `ProjectInfinit`)
4. Vyberte **"Development"** prostředí
5. Vyplňte popis (např. "Sbírání tweetů o náboženských hnutích")
6. Klikněte **"Create"**

### Krok 3: Povolení API v2

1. Jděte na záložku **"Keys and tokens"**
2. Ujistěte se, že máte API v2 přístup
3. Pod **"Bearer Token"** klikněte **"Generate"**
4. Zkopíruj Bearer Token do `.env`:

```bash
X_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAAAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Krok 4: Testování připojení

```bash
python3 -c "
import requests

headers = {
    'Authorization': 'Bearer YOUR_BEARER_TOKEN',
    'User-Agent': 'ProjectInfinit/1.0'
}

response = requests.get(
    'https://api.twitter.com/2/tweets/search/recent?query=test&max_results=10',
    headers=headers
)

if response.status_code == 200:
    print('✅ X/Twitter API připojeno')
else:
    print(f'❌ Chyba: {response.status_code}')
    print(response.json())
"
```

### X API v2 Limity

- **Free tier**: 300 tweetů za 15 minut (900s window)
- **Rate limit**: Viz `rate_limit_reset: 900` v `sources_config.yaml`
- **Timeout**: Po dosažení limitu čeká spider 15 minut

Náš spider automaticky dodržuje tyto limity.

---

## 🔄 Spuštění Sociálních Médií Spiderů

### Spuštění všech spiderů (včetně sociálních médií)

```bash
python main.py
```

### Spuštění jen Reddit spideru

```bash
scrapy runspider scraping/social_media_spider.py -a spider_type=reddit
```

### Spuštění jen X spideru

```bash
scrapy runspider scraping/social_media_spider.py -a spider_type=x_twitter
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

# Spustit jen X testy
pytest -v testing/test_social_media_spider.py::TestXTwitterSpider

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

### X/Twitter Konfigurace

```yaml
x_twitter:
  name: X (Twitter)
  description: Tweets about Czech religious movements
  type: social_api
  api_method: search_tweets
  url: https://api.twitter.com/2
  
  # Hledané dotazy (všechny s českým jazykem filtrem)
  search_queries:
    - "sekta lang:cs"
    - "kult lang:cs"
    - "nové náboženské hnutí lang:cs"
    - "spirituální hnutí lang:cs"
  
  # Parametry API
  api_params:
    max_results: 100
    tweet_fields: created_at,public_metrics,author_id
    expansions: author_id
    user_fields: username,created_at
  
  # Bezpečnostní nastavení
  rate_limit_reset: 900  # 15 minut
  
  # API klíč
  auth:
    bearer_token: ${X_BEARER_TOKEN}
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

### X/Twitter

**Chyba: "Unauthorized Bearer Token"**
- Zkontrolujte, že Bearer Token není příliš starý
- Regenerujte token na https://developer.twitter.com/

**Chyba: "The `query` parameter value [xyz] is invalid"**
- Zkontrolujte search queries v `sources_config.yaml`
- České znaky musí být správně zakódovány

**Chyba: "Too Many Requests (429)"**
- Vyčkejte 15 minut (rate limit window)
- Spider má vestavěný rate limit handler

### Obecné

**Chyba: "No module named praw" nebo "No module named tweepy"**
```bash
pip install -r requirements.txt
```

**`.env` soubor se nenačítá**
- Ujistěte se, že je `.env` v root adresáři projektu
- Ujistěte se, že není v `.gitignore` (měl by být!)
- Restartujte terminál po vytvoření `.env`

---

## 📊 Výstupy

Příspěvky a tweety jsou uloženy do CSV souborů:

```bash
export/csv/reddit_raw.csv
export/csv/x_twitter_raw.csv
```

Struktura dat:

```csv
source_name,source_type,title,url,text,scraped_at,author,created,score/metrics
```

---

## 🔗 Užitečné Linky

- **Reddit Developer Docs**: https://www.reddit.com/dev/api/
- **PRAW Documentation**: https://praw.readthedocs.io/
- **X/Twitter API v2 Docs**: https://developer.twitter.com/en/docs/twitter-api
- **HTTP Status Codes**: https://developer.twitter.com/en/docs/twitter-api/errors/messages

---

**Last Updated**: 2025-01-08
**Verze**: 1.0
