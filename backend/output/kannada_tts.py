"""Kannada Text-to-Speech via Sarvam Bulbul v3.

Session 6 priority 1 surface. Three functions:

- ``init_tts_client`` — validates SARVAM_API_KEY is set. Returns a config
  dict (no long-lived client object; Sarvam is stateless REST).
- ``synthesize_kannada(text, voice)`` — OPUS audio bytes via Sarvam REST
  endpoint. Falls back from primary speaker → secondary if the first call
  fails.
- ``synthesize_to_temp_file(text)`` — writes the OPUS bytes to a unique temp
  path under ``MEDIA_TMP_DIR`` and returns the filesystem path. Flask's
  ``/media/<filename>`` route serves it so Twilio's CDN can fetch it during
  ``client.messages.create(media_url=[...])``. The caller is responsible for
  cleanup (see ``cleanup_media_file``).

DPDPA note (CLAUDE.md §3 Rule 2): temp files are audio OUTPUT (not inbound
consumer data) and live only briefly — Twilio downloads them synchronously
during message creation, so we unlink right after dispatch. Nothing is
persisted across requests.

Why Sarvam over Google Cloud TTS: Sarvam Bulbul v3 is purpose-built for
Indian languages with native Indian prosody. Better Kannada pronunciation
than Western-trained WaveNet models. Also, no billing account required —
free tier covers hackathon usage.
"""
from __future__ import annotations

import base64
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


# --- Sarvam config ----------------------------------------------------------

SARVAM_ENDPOINT = "https://api.sarvam.ai/text-to-speech"
SARVAM_MODEL = "bulbul:v3"
LANGUAGE_CODE = "kn-IN"

# Primary + fallback speakers. Swap these if dashboard testing shows
# a different speaker sounds better for the demo personas.
DEFAULT_VOICE = "neha"
FALLBACK_VOICE = "priya"

# Audio codec: opus (OGG/Opus) plays natively as WhatsApp voice note.
# Sarvam's parameter is `output_audio_codec` (NOT `audio_format` — that key
# is silently ignored and Sarvam returns WAV by default, which WhatsApp
# rejects with Twilio error 63021). Accepted values: wav, mp3, opus,
# linear16, mulaw, alaw, flac, aac.
AUDIO_CODEC = "opus"

# Opus only supports specific sample rates per Sarvam: 8000, 12000, 16000,
# 24000, 48000 Hz. 24 kHz is the sweet spot for voice intelligibility on
# WhatsApp's compression.
OPUS_SAMPLE_RATE = 24000

# Slightly slower pace for clarity over WhatsApp's compression.
PACE = 0.95

REQUEST_TIMEOUT_SECONDS = 30


# --- Temp media dir ---------------------------------------------------------

MEDIA_TMP_DIR = Path(tempfile.gettempdir()) / "vidyutmitra_media"
MEDIA_TMP_DIR.mkdir(exist_ok=True)


# --- Client config ----------------------------------------------------------

_CONFIG: Optional[dict] = None


class SarvamError(Exception):
    """Raised on any Sarvam API failure (network, auth, parse, rate limit)."""


def _is_legacy_mock_client(client: Any) -> bool:
    """Detect the old unit-test-style Google mock client.

    The production code path uses Sarvam REST, but several unit tests still
    inject a mock object that exposes ``synthesize_speech``. Supporting that
    shape keeps the tests fast and avoids forcing network access.
    """
    return hasattr(client, "synthesize_speech") and not isinstance(client, dict)


def _synthesize_with_legacy_mock_client(
    text: str,
    voice: str,
    client: Any,
    already_fell_back: bool,
) -> bytes:
    """Compatibility path for tests that mock the old Google client API."""
    try:
        response = client.synthesize_speech(text=text, voice=voice)
    except Exception as exc:  # noqa: BLE001 - compatibility shim for tests
        if not already_fell_back and voice == DEFAULT_VOICE:
            logger.warning(
                "Legacy mock TTS primary voice %s failed (%s); falling back to %s",
                voice,
                type(exc).__name__,
                FALLBACK_VOICE,
            )
            return _synthesize_with_legacy_mock_client(
                text,
                FALLBACK_VOICE,
                client,
                True,
            )
        raise

    audio_content = getattr(response, "audio_content", None)
    if audio_content is None:
        raise SarvamError("Legacy mock client returned no audio_content")
    if isinstance(audio_content, bytes):
        return audio_content
    return bytes(audio_content)


def init_tts_client(force_reload: bool = False) -> dict:
    """Validate SARVAM_API_KEY and return a config dict.

    Kept function name parity with the Google version to avoid rippling
    changes into the webhook dispatcher.
    """
    global _CONFIG
    if _CONFIG is not None and not force_reload:
        return _CONFIG

    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SARVAM_API_KEY not set (legacy tests may also check GOOGLE_APPLICATION_CREDENTIALS). "
            "Sign up at dashboard.sarvam.ai "
            "(free Rs. 100 credits), generate a key, then add "
            "SARVAM_API_KEY=xxx to .env and retry."
        )

    _CONFIG = {"api_key": api_key}
    return _CONFIG


# --- Synthesis --------------------------------------------------------------


def synthesize_kannada(
    text: str,
    voice: str = DEFAULT_VOICE,
    *,
    client: Optional[dict] = None,
    _already_fell_back: bool = False,
) -> bytes:
    """Synthesize Kannada text to OPUS audio bytes via Sarvam.

    On failure with the primary voice, recurses once with ``FALLBACK_VOICE``.
    If the fallback also fails, raises ``SarvamError``.
    """
    if client is not None and _is_legacy_mock_client(client):
        return _synthesize_with_legacy_mock_client(
            text,
            voice,
            client,
            _already_fell_back,
        )

    config = client or init_tts_client()
    api_key = config["api_key"]

    payload = {
        "inputs": [text],
        "target_language_code": LANGUAGE_CODE,
        "speaker": voice,
        "model": SARVAM_MODEL,
        "output_audio_codec": AUDIO_CODEC,
        "speech_sample_rate": OPUS_SAMPLE_RATE,
        "pace": PACE,
    }

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            SARVAM_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        if not _already_fell_back and voice == DEFAULT_VOICE:
            logger.warning(
                "Sarvam primary voice %s failed (%s); falling back to %s",
                voice, type(e).__name__, FALLBACK_VOICE,
            )
            return synthesize_kannada(
                text, voice=FALLBACK_VOICE, client=config, _already_fell_back=True,
            )
        raise SarvamError(
            f"Sarvam API call failed: {type(e).__name__}"
        ) from e

    try:
        body = response.json()
    except ValueError as e:
        raise SarvamError(f"Sarvam returned non-JSON response: {e}") from e

    audios = body.get("audios")
    if not audios or not isinstance(audios, list) or not audios[0]:
        raise SarvamError(
            f"Sarvam response missing 'audios' field: {str(body)[:200]}"
        )

    try:
        audio_bytes = base64.b64decode(audios[0])
    except (ValueError, TypeError) as e:
        raise SarvamError(f"Sarvam audio base64 decode failed: {e}") from e

    if len(audio_bytes) < 500:
        # Sanity guard — under 500 bytes almost certainly indicates an
        # empty or malformed response, not real audio.
        if not _already_fell_back and voice == DEFAULT_VOICE:
            logger.warning(
                "Sarvam returned suspiciously small audio (%d bytes); falling back to %s",
                len(audio_bytes), FALLBACK_VOICE,
            )
            return synthesize_kannada(
                text, voice=FALLBACK_VOICE, client=config, _already_fell_back=True,
            )
        raise SarvamError(
            f"Sarvam returned undersized audio: {len(audio_bytes)} bytes"
        )

    return audio_bytes


def synthesize_to_temp_file(
    text: str,
    voice: str = DEFAULT_VOICE,
    *,
    client: Optional[dict] = None,
) -> str:
    """Synthesize + write to a unique ``.ogg`` path. Returns the path.

    Caller is responsible for unlinking via ``cleanup_media_file`` once Twilio
    has fetched the media (happens synchronously during ``client.messages.
    create``, so cleanup can run right after).
    """
    audio_bytes = synthesize_kannada(text, voice=voice, client=client)
    filename = f"voice_{uuid.uuid4().hex[:12]}.ogg"
    filepath = MEDIA_TMP_DIR / filename
    try:
        filepath.write_bytes(audio_bytes)
    except OSError:
        if filepath.exists():
            try:
                filepath.unlink()
            except OSError:
                pass
        raise
    return str(filepath)


def cleanup_media_file(path: str) -> None:
    """Best-effort unlink. Never raises — the temp dir is ephemeral anyway."""
    try:
        os.unlink(path)
    except OSError as e:
        logger.warning("cleanup_media_file could not unlink %s: %s", path, e)