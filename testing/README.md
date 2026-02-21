# Testing Guide for Project Infinit

Complete test suite for the Project Infinit. All tests use pytest and monkeypatching for testing without external dependencies.

## Installing testing dependencies

```bash
pip install pytest pytest-cov pytest-mock
```

## Test structure

```text
testing/
├── test_keywords.py           # Tests for keyword filtering
├── test_db_loader.py          # Tests for database layer (in-memory SQLite)
├── test_nlp_analysis.py       # Tests for NLP wrapper (mock Stanza/Transformers)
├── test_config_loader.py      # Tests for YAML config loader
├── test_rss_spider.py         # Tests for RSS spider
├── test_api_spider.py         # Tests for API spider
├── test_social_media_spider.py # Tests for Reddit and X/Twitter API
└── README.md                  # This file
```

## Running tests

### Run all tests

```bash
pytest -v testing/
```

### Run specific test file

```bash
pytest -v testing/test_keywords.py
pytest -v testing/test_db_loader.py
pytest -v testing/test_rss_spider.py
pytest -v testing/test_social_media_spider.py
```

### Run specific test

```bash
pytest -v testing/test_keywords.py::test_contains_relevant_keywords_positive
```

### Run with coverage report

```bash
pytest --cov=scraping --cov=database --cov=processing --cov-report=term-missing testing/
```

### Run with quick output

```bash
pytest -q testing/
```

## Test suite overview

### 1. ### 1. **test_keywords.py** — Keyword filtering

- ✅ `test_contains_relevant_keywords_positive` — Positive test for relevant content
- ✅ `test_contains_relevant_keywords_negative` — Negative test for irrelevant content
- ✅ `test_is_excluded_content` — Test for excluded terms

### 2. ### 2. **test_db_loader.py** — Database layer

- ✅ `test_dbconnector_insert_and_query` — Insert and query sources (in-memory SQLite)

### 3. ### 3. **test_nlp_analysis.py** — NLP pipeline

- ✅ `test_nlp_analysis_monkeypatched` — Test analyzer with mock Stanza/Transformers

### 4. **test_config_loader.py** — Source configuration

- ✅ `test_config_loader_loads_yaml` — Load YAML configuration
- ✅ `test_get_all_sources` — Return all sources
- ✅ `test_get_enabled_sources` — Filter enabled sources
- ✅ `test_get_source` — Load specific source
- ✅ `test_get_source_urls` — Export all URLs
- ✅ `test_get_scraping_settings` — Get scraping settings
- ✅ `test_get_content_filters` — Get content filters
- ✅ `test_is_source_enabled` — Check if source is enabled
- ✅ `test_toggle_source` — Enable/disable source
- ✅ `test_add_custom_source` — Add custom source
- ✅ `test_source_list_as_table` — Export as table

### 5. **test_rss_spider.py** — RSS spider

- ✅ `test_rss_spider_initialization` — RSS spider initialization
- ✅ `test_rss_spider_filters_rss_sources` — Filter RSS sources
- ✅ `test_rss_spider_parse_rss` — Parse RSS feed
- ✅ `test_rss_spider_filters_irrelevant_content` — Filter irrelevant content
- ✅ `test_rss_spider_handles_missing_fields` — Handle missing fields
- ✅ `test_single_rss_spider_specific_source` — SingleRSSSpider with specific source
- ✅ `test_single_rss_spider_invalid_type` — Error on invalid type

### 6. **test_api_spider.py** — API spider

- ✅ `test_api_spider_initialization` — API spider initialization
- ✅ `test_api_spider_filters_api_sources` — Filter API sources
- ✅ `test_api_spider_parse_mediawiki_api` — Parse MediaWiki API
- ✅ `test_api_spider_filters_irrelevant_content` — Filter irrelevant content
- ✅ `test_api_spider_handles_invalid_json` — Handle invalid JSON
- ✅ `test_api_spider_query_method` — Parse query method
- ✅ `test_single_api_spider_specific_source` — SingleAPISpider with specific source
- ✅ `test_single_api_spider_invalid_type` — Error on invalid type

### 7. **test_social_media_spider.py** — Social media (Reddit & X/Twitter)

- ✅ `test_reddit_spider_init` — Reddit spider initialization with API keys
- ✅ `test_reddit_spider_missing_credentials` — Error on missing credentials
- ✅ `test_reddit_spider_start_requests` — Generate initial requests
- ✅ `test_reddit_parse_relevant_submission` — Parse relevant submission
- ✅ `test_x_spider_init` — X/Twitter spider initialization with bearer token
- ✅ `test_x_spider_missing_token` — Error on missing token
- ✅ `test_x_spider_get_headers` — Generate headers with bearer token
- ✅ `test_x_spider_start_requests` — Generate requests from search queries
- ✅ `test_x_spider_parse_relevant_tweet` — Parse relevant tweet
- ✅ `test_x_spider_filters_irrelevant_tweets` — Filter irrelevant tweets
- ✅ `test_reddit_spider_loads_config` — Load configuration from YAML
- ✅ `test_x_spider_loads_config` — Load configuration from YAML

## Testing in CI/CD

Example GitHub Actions workflow (`.github/workflows/test.yml`):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      - name: Run tests
        run: pytest -v --cov=scraping --cov=database --cov=processing testing/
```

## Best practices

- All tests use **monkeypatching** for isolation
- **In-memory SQLite** for DB tests (no server connection)
- Tests are **independent** — can be run in any order
- Tests are **fast** — don't play with network or files
- Tests have **clear names** — describe what they test
- Tests are **readable** — serve as documentation

## Extending tests

When adding a new module, add tests:

1. Create `testing/test_<module>.py`
2. Mock external dependencies
3. Test happy path, edge cases and errors
4. Run `pytest testing/test_<module>.py`

## Troubleshooting

### Tests won't run: "No module named pytest"

```bash
pip install pytest
```

### ImportError in tests: "No module named scraping"

```bash
cd /home/adam/Dokumenty/projects/project_infinit
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest testing/
```

### Monkeypatching doesn't work

- Make sure you import the correct module (`import scraping.xxx`)
- Make sure you mock the correct path (`monkeypatch.setattr('scraping.xxx.function', ...)`)

## Current status

- Total tests: **43+** (33 existing + 12 for social media)
- Coverage: keywords, db, nlp, config, rss, api, social media
- All tests passing ✅
