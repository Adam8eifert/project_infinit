# 📁 testing/test_source_level_filtering.py
# Test source-level require_movement_id filtering

import pytest
from pathlib import Path
from processing.import_csv_to_db import CSVtoDatabaseLoader


class TestSourceLevelFiltering:
    """Test require_movement_id filtering from sources_config.yaml"""

    def test_source_requires_movement_id_for_mainstream_sources(self):
        """Test that mainstream sources are detected as requiring movement_id"""
        loader = CSVtoDatabaseLoader()
        
        # Test mainstream sources that should require movement_id
        mainstream_sources = [
            Path("export/csv/blesk_rss_raw.csv"),
            Path("export/csv/forum24_rss_raw.csv"),
            Path("export/csv/ct24_domaci_rss_raw.csv"),
            Path("export/csv/irozhlas_rss_raw.csv"),
            Path("export/csv/seznam_zpravy_rss_raw.csv"),
            Path("export/csv/idnes_domaci_rss_raw.csv"),
            Path("export/csv/aktualne_rss_raw.csv"),
            Path("export/csv/denik_cz_rss_raw.csv"),
            Path("export/csv/denik_alarm_rss_raw.csv"),
        ]
        
        for source_path in mainstream_sources:
            requires = loader._source_requires_movement_id(source_path)
            assert requires, f"{source_path.name} should require movement_id"

    def test_source_does_not_require_movement_id_for_specialist_sources(self):
        """Test that specialist sources don't require movement_id"""
        loader = CSVtoDatabaseLoader()
        
        # Test specialist sources that should NOT require movement_id
        specialist_sources = [
            Path("export/csv/sekty_tv_rss_raw.csv"),
            Path("export/csv/info_dingir_rss_raw.csv"),
            Path("export/csv/pastorace_rss_raw.csv"),
        ]
        
        for source_path in specialist_sources:
            requires = loader._source_requires_movement_id(source_path)
            assert not requires, f"{source_path.name} should NOT require movement_id"

    def test_source_requires_movement_id_handles_unknown_sources(self):
        """Test that unknown sources default to not requiring movement_id"""
        loader = CSVtoDatabaseLoader()
        
        unknown_sources = [
            Path("export/csv/unknown_source_raw.csv"),
            Path("export/csv/fake_news_raw.csv"),
        ]
        
        for source_path in unknown_sources:
            requires = loader._source_requires_movement_id(source_path)
            assert not requires, f"{source_path.name} should default to not requiring movement_id"

    def test_is_article_relevant_respects_require_movement_id(self):
        """Test that _is_article_relevant filters based on require_movement_id"""
        loader = CSVtoDatabaseLoader()
        
        # Article without movement_id
        article_no_movement = {
            "title": "Test válka na Ukrajině pokračuje",
            "content": "Zprávy z fronty...",
            "movement_id": None,
            "source_type": "rss",
        }
        
        # Test with mainstream source (requires movement_id)
        mainstream_path = Path("export/csv/blesk_rss_raw.csv")
        is_relevant = loader._is_article_relevant(article_no_movement, mainstream_path)
        assert not is_relevant, "Article without movement should be rejected from mainstream source"
        
        # Test with specialist source (doesn't require movement_id)
        specialist_path = Path("export/csv/sekty_tv_rss_raw.csv")
        is_relevant = loader._is_article_relevant(article_no_movement, specialist_path)
        # This should pass relevance check based on keywords if they match
        # (exact result depends on keyword matching)

    def test_is_article_relevant_allows_articles_with_movement_id(self):
        """Test that articles with movement_id are always accepted"""
        loader = CSVtoDatabaseLoader()
        
        # Article with movement_id
        article_with_movement = {
            "title": "Scientologie otevřela nové centrum",
            "content": "Církev scientologie...",
            "movement_id": 42,
            "source_type": "rss",
        }
        
        # Test with both mainstream and specialist sources
        for csv_path in [
            Path("export/csv/blesk_rss_raw.csv"),
            Path("export/csv/sekty_tv_rss_raw.csv"),
        ]:
            is_relevant = loader._is_article_relevant(article_with_movement, csv_path)
            assert is_relevant, f"Article with movement_id should be accepted from {csv_path.name}"
