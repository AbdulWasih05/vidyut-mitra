"""Fetch MMS/WhatsApp media bytes from Twilio's CDN.

Used by ``app.py`` when a consented user sends a bill photo. Twilio returns
``MediaUrl0`` pointing at ``api.twilio.com/.../MExxxxx``; the content requires
HTTP Basic auth with the account SID + auth token.

DPDPA guarantee (CLAUDE.md §3 Rule 2): the bytes returned by this function
live only in a Python ``bytes`` variable on the call stack. There is no
``open(..., 'wb')`` call here and never will be.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10


class TwilioMediaError(Exception):
    """Raised on any HTTP failure fetching Twilio media."""


def fetch_twilio_media(
    media_url: str,
    *,
    account_sid: Optional[str] = None,
    auth_token: Optional[str] = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> bytes:
    """Download the media at ``media_url`` as bytes and return them.

    Auth credentials default to env vars ``TWILIO_ACCOUNT_SID`` /
    ``TWILIO_AUTH_TOKEN`` if not passed explicitly.
    """
    sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID")
    token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise TwilioMediaError(
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set to fetch "
            "Twilio media. Copy .env.example -> .env and fill them in."
        )

    try:
        resp = requests.get(media_url, auth=(sid, token), timeout=timeout)
    except requests.RequestException as e:
        raise TwilioMediaError(f"network error fetching Twilio media: {type(e).__name__}") from e

    if resp.status_code >= 400:
        raise TwilioMediaError(
            f"Twilio returned HTTP {resp.status_code} for media_url"
        )

    logger.info(
        "twilio media fetched bytes=%d content_type=%s",
        len(resp.content),
        resp.headers.get("Content-Type", "?"),
    )
    return resp.content
