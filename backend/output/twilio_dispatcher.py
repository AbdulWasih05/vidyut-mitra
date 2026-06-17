"""Twilio WhatsApp outbound dispatcher — skeleton for Session 4.

Only ``send_text`` is wired. Voice notes (Session 6 — Google Cloud TTS) and
infographics (Session 6 — Pillow template overlay) land later.

Rate limit: Twilio sandbox is 1 message/second. We sleep BEFORE each send so
successive calls queue cleanly in the same invocation; PRD §2.3 uses three
sequential sends (text + voice + infographic) so the gap matters.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

TWILIO_RATE_LIMIT_SECONDS = 1.0


_CLIENT: Optional[Any] = None


def init_client(force_reload: bool = False) -> Any:
    """Late-import the Twilio SDK and cache a client."""
    global _CLIENT
    if _CLIENT is not None and not force_reload:
        return _CLIENT

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise RuntimeError(
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set. "
            "Copy .env.example -> .env and fill them in."
        )

    from twilio.rest import Client
    _CLIENT = Client(sid, token)
    return _CLIENT


def _twilio_number() -> str:
    n = os.environ.get("TWILIO_WHATSAPP_NUMBER")
    if not n:
        raise RuntimeError("TWILIO_WHATSAPP_NUMBER must be set (e.g. whatsapp:+14155238886).")
    return n


def send_text(
    to_phone: str,
    body: str,
    *,
    client: Optional[Any] = None,
    rate_limit: bool = True,
) -> str:
    """Send a WhatsApp text to ``to_phone``. Returns the Twilio message SID.

    ``to_phone`` must be the full WhatsApp-prefixed number, e.g.
    ``whatsapp:+919876543210``.
    """
    if rate_limit:
        time.sleep(TWILIO_RATE_LIMIT_SECONDS)

    c = client or init_client()
    message = c.messages.create(
        from_=_twilio_number(),
        to=to_phone,
        body=body,
    )
    logger.info("twilio sent sid=%s to=%s bytes=%d", message.sid, to_phone, len(body))
    return message.sid


# --- Media dispatch (Session 6) ---------------------------------------------


def _public_media_url(filename: str) -> str:
    """Build the ``PUBLIC_BASE_URL/media/<filename>`` URL Twilio will fetch.

    ``PUBLIC_BASE_URL`` is the ngrok (or production Railway) URL; it must
    already route to our Flask ``/media/<filename>`` endpoint.
    """
    base = os.environ.get("PUBLIC_BASE_URL")
    if not base:
        raise RuntimeError(
            "PUBLIC_BASE_URL not set — cannot serve media to Twilio. "
            "Set it to your ngrok URL (e.g. https://abcd.ngrok-free.app)."
        )
    return f"{base.rstrip('/')}/media/{filename}"


def send_voice_note(
    to_phone: str,
    audio_path: str,
    *,
    client: Optional[Any] = None,
    rate_limit: bool = True,
    cleanup: bool = True,
) -> str:
    """Ship an OGG Opus voice note via Twilio WhatsApp.

    ``audio_path`` is a filesystem path under ``vidyutmitra_media`` (produced
    by ``output.kannada_tts.synthesize_to_temp_file``). We extract the
    filename, build the public URL, and pass it to Twilio.

    NOTE: Twilio's CDN fetches the media URL asynchronously, several seconds
    after ``messages.create`` returns. Pass ``cleanup=False`` from production
    call paths and rely on the periodic sweeper in ``app._start_media_sweeper``
    to reap the temp file — unlinking here races the fetch and yields 404s.
    ``cleanup=True`` is retained for tests that don't use the real CDN.
    """
    import os as _os

    if rate_limit:
        time.sleep(TWILIO_RATE_LIMIT_SECONDS)

    filename = _os.path.basename(audio_path)
    media_url = _public_media_url(filename)

    try:
        c = client or init_client()
        message = c.messages.create(
            from_=_twilio_number(),
            to=to_phone,
            media_url=[media_url],
        )
        logger.info(
            "twilio voice sid=%s to=%s url=%s", message.sid, to_phone, media_url
        )
        return message.sid
    finally:
        if cleanup:
            try:
                _os.unlink(audio_path)
            except OSError:
                # Temp dir is ephemeral anyway; swallow rather than propagate.
                pass


def send_image(
    to_phone: str,
    image_path: str,
    *,
    client: Optional[Any] = None,
    rate_limit: bool = True,
    cleanup: bool = True,
) -> str:
    """Ship a PNG infographic via Twilio WhatsApp. Same pattern as voice."""
    import os as _os

    if rate_limit:
        time.sleep(TWILIO_RATE_LIMIT_SECONDS)

    filename = _os.path.basename(image_path)
    media_url = _public_media_url(filename)

    try:
        c = client or init_client()
        message = c.messages.create(
            from_=_twilio_number(),
            to=to_phone,
            media_url=[media_url],
        )
        logger.info(
            "twilio image sid=%s to=%s url=%s", message.sid, to_phone, media_url
        )
        return message.sid
    finally:
        if cleanup:
            try:
                _os.unlink(image_path)
            except OSError:
                pass
