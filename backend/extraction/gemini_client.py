"""Gemini 2.5 Flash client for MESCOM bill extraction.

Contract:
- ``extract_bill(image_bytes, issues=None) -> dict`` issues the Gemini call and
  returns the parsed JSON response. If ``issues`` is provided, uses the retry
  prompt enumerating those issues instead of the first-attempt prompt.
- ``extract_with_fallback(image_bytes, phone_number)`` wraps ``extract_bill``
  and falls back to a cached extraction from ``demo_fallbacks.json`` when
  Gemini raises ``GeminiError`` or ``TimeoutError`` AND the phone number is in
  the fallbacks dict.

DPDPA (CLAUDE.md §3 Rule 2): image bytes live in a local ``bytes`` variable
only for the duration of the Gemini call. No ``open(..., 'wb')`` exists in
this module. The bytes reference goes out of scope once this function returns.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from backend.extraction.prompts import EXTRACTION_PROMPT, build_retry_prompt

logger = logging.getLogger(__name__)

# --- Gemini config (tech spec §4.1) -----------------------------------------
MODEL_NAME = "gemini-2.5-flash"
TEMPERATURE_FIRST = 0.1
TEMPERATURE_RETRY = 0.05
MAX_OUTPUT_TOKENS = 8192  # 2.5 Flash consumes budget on internal thinking; 2048 truncates
RESPONSE_MIME_TYPE = "application/json"

# --- Fallbacks path ---------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_FALLBACKS_PATH = _BACKEND_ROOT / "demo_fallbacks.json"


def _load_dotenv_if_available() -> None:
    """Load .env values when python-dotenv is installed.

    REPL and direct module usage do not pass through app.create_app(), so we
    load dotenv here as a best-effort before reading GEMINI_API_KEY.
    """
    try:
        from dotenv import load_dotenv

        # Load from repo root explicitly so script execution works regardless
        # of current working directory.
        load_dotenv(_REPO_ROOT / ".env", override=False)
        load_dotenv(_REPO_ROOT / ".env.local", override=False)
    except ImportError:
        pass


class GeminiError(Exception):
    """Raised on any Gemini API failure (network, parse, rate limit, auth)."""


def _load_demo_fallbacks() -> dict[str, Any]:
    """Load demo fallbacks JSON; return empty dict if missing / unreadable."""
    if not DEMO_FALLBACKS_PATH.exists():
        return {}
    try:
        with DEMO_FALLBACKS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not load demo_fallbacks.json: %s", e)
        return {}


def _build_model(temperature: float):
    """Late-import google.generativeai so tests can mock without needing the
    library installed, and so the module imports even without GEMINI_API_KEY.
    """
    import google.generativeai as genai  # local import keeps test mocking simple

    _load_dotenv_if_available()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GeminiError(
            "GEMINI_API_KEY not set. Copy .env.example → .env and fill it in."
        )

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "response_mime_type": RESPONSE_MIME_TYPE,
        },
    )


def _parse_response_text(text: str) -> dict[str, Any]:
    """Parse Gemini's JSON text. With ``response_mime_type=application/json``
    the text should be raw JSON with no markdown fences; we still strip
    defensively in case a future model leaks them.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # Remove opening ``` or ```json and closing ```
        lines = stripped.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as e:
        logger.error("Gemini returned unparseable JSON: %s\n--- raw ---\n%s", e, text)
        raise GeminiError(f"unparseable JSON from Gemini: {e}") from e


def extract_bill(
    image_bytes: bytes,
    issues: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Issue the Gemini call and return the parsed JSON response.

    If ``issues`` is provided, uses the retry prompt (tech spec §4.4) with a
    tighter temperature. Otherwise uses the first-attempt extraction prompt.
    """
    temperature = TEMPERATURE_RETRY if issues else TEMPERATURE_FIRST
    prompt = build_retry_prompt(issues) if issues else EXTRACTION_PROMPT

    model = _build_model(temperature)

    # Gemini accepts image bytes via a {"mime_type","data"} blob. JPEG is the
    # overwhelming default for WhatsApp photos; the content server on Twilio
    # reports a real MIME type — for v1 we trust the image is JPEG/PNG and
    # tag it as image/jpeg (Gemini auto-detects regardless).
    image_part = {"mime_type": "image/jpeg", "data": image_bytes}

    try:
        response = model.generate_content([prompt, image_part])
    except Exception as e:  # noqa: BLE001 — convert any SDK error to GeminiError
        # google.api_core.exceptions.__str__ has segfaulted on malformed
        # protobufs — never call str() / repr() on the exception. But e.args[0]
        # is a plain string (the human-readable message) and is safe to read.
        # That's where Gemini puts the "Quota exceeded for ... per minute / day"
        # text we need to identify which limit fired.
        safe_msg = ""
        args = getattr(e, "args", None)
        if args and isinstance(args[0], str):
            safe_msg = args[0][:300]
        if safe_msg:
            logger.warning("Gemini SDK error detail: %s", safe_msg)
        raise GeminiError(
            f"Gemini API call failed: {type(e).__module__}.{type(e).__name__}"
        ) from e

    text = getattr(response, "text", None)
    if not text:
        raise GeminiError("Gemini returned empty response")

    return _parse_response_text(text)


def extract_with_fallback(
    image_bytes: bytes,
    phone_number: Optional[str],
) -> dict[str, Any]:
    """Wrap ``extract_bill`` with the demo-fallback ladder (CLAUDE.md §8 Path 2).

    If Gemini raises ``GeminiError`` or ``TimeoutError`` AND the phone number
    matches an entry in ``demo_fallbacks.json``, return the cached extraction.
    Otherwise the original exception propagates.
    """
    try:
        return extract_bill(image_bytes)
    except (GeminiError, TimeoutError) as e:
        logger.warning("Gemini failed: %s. Attempting demo fallback.", e)
        fallbacks = _load_demo_fallbacks()
        entry = fallbacks.get(phone_number) if phone_number else None
        if entry and isinstance(entry, dict) and "extraction" in entry:
            logger.info(
                "Using cached extraction for phone=%s persona=%s",
                phone_number,
                entry.get("persona", "unknown"),
            )
            return entry["extraction"]
        raise
