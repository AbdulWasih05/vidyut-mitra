"""Shared pytest fixtures + environment-independent test infrastructure.

Notably: we stub ``google.cloud.texttospeech`` in ``sys.modules`` when the
real SDK isn't installed on the dev machine, so TTS unit tests can still
run with a mocked client. Production Flask boot imports the real SDK via
``requirements.txt``.
"""
from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock


def _stub_google_texttospeech_if_missing() -> None:
    """Inject a lightweight stub into ``sys.modules`` when the real Google
    TTS SDK isn't installed (e.g. in a trimmed CI image).

    Real installs take precedence — we only inject when the import genuinely
    fails. That way tests that pass a mock ``client`` still exercise
    ``synthesize_kannada`` without needing gRPC / grpcio wheels locally.
    """
    try:
        from google.cloud import texttospeech  # noqa: F401
        return
    except ImportError:
        pass

    # Build a stand-in module with just the types/enums the code touches.
    fake = MagicMock(name="google.cloud.texttospeech (stub)")
    fake.AudioEncoding = SimpleNamespace(
        OGG_OPUS="OGG_OPUS",
        MP3="MP3",
        LINEAR16="LINEAR16",
    )
    fake.SynthesisInput = lambda text=None: SimpleNamespace(text=text)
    fake.VoiceSelectionParams = lambda language_code=None, name=None: SimpleNamespace(
        language_code=language_code, name=name,
    )
    fake.AudioConfig = lambda audio_encoding=None, sample_rate_hertz=None: SimpleNamespace(
        audio_encoding=audio_encoding, sample_rate_hertz=sample_rate_hertz,
    )
    fake.TextToSpeechClient = MagicMock

    # google + google.cloud packages themselves may not exist — inject both.
    google_pkg = sys.modules.setdefault("google", MagicMock(name="google (stub)"))
    cloud_pkg = sys.modules.setdefault(
        "google.cloud", MagicMock(name="google.cloud (stub)"),
    )
    # Attribute access on packages matters for some `from X.Y import Z` forms.
    setattr(google_pkg, "cloud", cloud_pkg)
    setattr(cloud_pkg, "texttospeech", fake)
    sys.modules["google.cloud.texttospeech"] = fake


_stub_google_texttospeech_if_missing()
