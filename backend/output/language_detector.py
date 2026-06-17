"""Language detection + toggling for English / Kannada.

Pure functions, no I/O. Used by the webhook to choose response language
when no explicit preference has been persisted yet.

Detection rule: any character in the Kannada Unicode block U+0C80–U+0CFF
flips the verdict to 'kn'. Everything else (Latin, digits, emoji,
punctuation, empty, None) is 'en'. This is deliberately permissive on the
Kannada side — a single Kannada character in a mixed message is enough
to assume the user reads Kannada.
"""
from __future__ import annotations

from typing import Optional

LANG_EN = "en"
LANG_KN = "kn"

_KANNADA_BLOCK_START = 0x0C80
_KANNADA_BLOCK_END = 0x0CFF


def detect_language(text: Optional[str]) -> str:
    """Return ``'kn'`` if ``text`` contains any Kannada char, else ``'en'``."""
    if not text:
        return LANG_EN
    for ch in text:
        if _KANNADA_BLOCK_START <= ord(ch) <= _KANNADA_BLOCK_END:
            return LANG_KN
    return LANG_EN


def toggle_language(current: Optional[str]) -> str:
    """Flip ``'en'`` ↔ ``'kn'``. ``None`` (no preference yet) becomes ``'kn'``
    so the LANG command always lands the user in Kannada on first use."""
    if current == LANG_EN:
        return LANG_KN
    return LANG_EN if current == LANG_KN else LANG_KN
