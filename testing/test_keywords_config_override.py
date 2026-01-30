import importlib
import io
from pathlib import Path
import yaml

from extracting import keywords as kw


def test_config_override(tmp_path, monkeypatch):
    # Read original config
    cfg_path = Path(kw.__file__).parent / "sources_config.yaml"
    original = cfg_path.read_text(encoding="utf8")

    try:
        # Write a minimal override
        override = {
            "keywords": {
                "required": ["UNIQUE_TEST_KEYWORD"],
                "exclude": ["UNIQUE_EXCLUDE"],
                "known_movements": {"new_religious_movements": ["Test Movement"]},
                "year_patterns": ["rok\s+(\d{4})"]
            }
        }
        cfg_path.write_text(yaml.safe_dump(override), encoding="utf8")

        importlib.reload(kw)

        assert "UNIQUE_TEST_KEYWORD" in kw.SEARCH_TERMS
        assert "UNIQUE_EXCLUDE" in kw.EXCLUDE_TERMS
        assert "Test Movement" in kw.ALL_KNOWN_MOVEMENTS
        assert any("rok" in p for p in kw.YEAR_PATTERNS)

    finally:
        # Restore original file and reload
        cfg_path.write_text(original, encoding="utf8")
        importlib.reload(kw)
