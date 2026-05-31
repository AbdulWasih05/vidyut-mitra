"""Smoke tests for output/language_detector.py."""
from __future__ import annotations

import pytest

from backend.output.language_detector import detect_language, toggle_language

pytestmark = pytest.mark.smoke


class TestDetectLanguage:
    def test_pure_english(self):
        assert detect_language("hello there") == "en"

    def test_pure_kannada(self):
        assert detect_language("ನಮಸ್ಕಾರ") == "kn"

    def test_mixed_any_kannada_char_wins(self):
        assert detect_language("hello ನಮಸ್ಕಾರ world") == "kn"

    def test_single_kannada_char_in_otherwise_english(self):
        assert detect_language("OK ಬ") == "kn"

    def test_empty_string(self):
        assert detect_language("") == "en"

    def test_none(self):
        assert detect_language(None) == "en"

    def test_digits_only(self):
        assert detect_language("12345") == "en"

    def test_emoji_only(self):
        assert detect_language("📸✅⚡") == "en"

    def test_punctuation_only(self):
        assert detect_language("...!?") == "en"

    def test_other_indic_script_not_kannada(self):
        # Devanagari (Hindi) is U+0900-U+097F, NOT in the Kannada block —
        # we deliberately don't auto-route Hindi-speakers to Kannada.
        assert detect_language("नमस्ते") == "en"


class TestToggleLanguage:
    def test_en_to_kn(self):
        assert toggle_language("en") == "kn"

    def test_kn_to_en(self):
        assert toggle_language("kn") == "en"

    def test_none_to_kn(self):
        assert toggle_language(None) == "kn"

    def test_unknown_value_falls_back_to_kn(self):
        # Defensive: if a corrupt value somehow lands in the DB, treat it
        # as "no preference yet" and route to Kannada.
        assert toggle_language("xx") == "kn"
