# 📁 testing/test_movement_category_inference.py
# Tests for movement category inference and config-driven category mapping

from main import _infer_movement_category


def test_infer_psychospiritual_category():
    assert _infer_movement_category("Scientologická církev") == "psychospiritual"
    assert _infer_movement_category("Eckankar") == "psychospiritual"


def test_infer_eastern_category():
    assert _infer_movement_category("Hnutí Hare Kršna") == "eastern"
    assert _infer_movement_category("Sahadža jóga") == "eastern"


def test_infer_ufo_category():
    assert _infer_movement_category("Raeliáni") == "ufo"
    assert _infer_movement_category("Universe People") == "ufo"


def test_infer_esoteric_category():
    assert _infer_movement_category("Anthroposofická společnost") == "esoteric"
    assert _infer_movement_category("Teosofická společnost") == "esoteric"


def test_infer_christian_derived_category():
    assert _infer_movement_category("Církev Ježíše Krista Svatých posledních dnů") == "christian_derived"
    assert _infer_movement_category("Křesťanská věda") == "christian_derived"
