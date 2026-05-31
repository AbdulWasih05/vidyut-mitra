"""Live Google Cloud TTS integration test.

Skipped by default. Run with ``pytest -v -m integration tests/test_tts_live.py``
after ``GOOGLE_APPLICATION_CREDENTIALS`` is set to a valid service-account
JSON path and the TTS API is enabled on that project.
"""
from __future__ import annotations

import os

import pytest

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

pytestmark = pytest.mark.integration


def _require_creds():
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        pytest.skip("GOOGLE_APPLICATION_CREDENTIALS not set")


def test_kannada_synthesis_returns_audio_bytes():
    _require_creds()
    from backend.output.kannada_tts import synthesize_kannada
    bytes_ = synthesize_kannada(
        "ನಮಸ್ಕಾರ. ನಿಮ್ಮ ಬಿಲ್ 1943 ರೂಪಾಯಿ."
    )
    assert isinstance(bytes_, bytes)
    # OGG Opus voice note ≥ ~10 KB for a ~3-second phrase.
    assert len(bytes_) >= 10_000, f"audio suspiciously small: {len(bytes_)} bytes"
    # OGG container signature: 4f 67 67 53 ("OggS").
    assert bytes_[:4] == b"OggS" or bytes_[:4] == b"\x4fggS"
