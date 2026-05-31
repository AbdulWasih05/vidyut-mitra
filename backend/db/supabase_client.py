"""Thin Supabase wrapper.

Small surface — the rest of the codebase calls four functions:
``get_or_create_user``, ``set_consent``, ``write_bill``, ``delete_user_cascade``.
Everything else is plumbing.

DPDPA guarantees enforced here (CLAUDE.md §3 Rule 2):
- ``write_bill`` refuses any attempt to persist ``bill_image``, ``bill_url``,
  or any field whose name suggests raw-image data, by raising ``ValueError``.
- ``delete_user_cascade`` is a HARD delete. The ``bills`` FK cascades; there
  is no soft-delete, no ``deleted_at`` column, no recovery.

Module-level ``init_client`` is lazy — we don't touch ``SUPABASE_URL`` /
``SUPABASE_KEY`` at import time so tests (and ``app.py --help``) can load the
module without a real Supabase project.
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, is_dataclass
from typing import Any, Optional

from dotenv import load_dotenv

from backend.analysis.models import BillExtraction

logger = logging.getLogger(__name__)

# Field names we refuse to persist — any of these in ``extraction`` or
# ``analysis`` triggers ValueError.
_FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "bill_image",
    "bill_image_bytes",
    "bill_image_url",
    "bill_url",
    "image",
    "image_bytes",
    "image_url",
    "raw_image",
    "media_url",
    "media_bytes",
    "photo",
    "photo_url",
})


# --- Lazy singleton ----------------------------------------------------------

_CLIENT: Optional[Any] = None


def init_client(force_reload: bool = False) -> Any:
    """Return a Supabase ``Client`` — lazily constructed + cached.

    Reads ``SUPABASE_URL`` and ``SUPABASE_KEY`` from env. Tests that need to
    bypass this should monkey-patch this module's ``_CLIENT`` global rather
    than calling ``init_client``.
    """
    global _CLIENT
    if _CLIENT is not None and not force_reload:
        return _CLIENT

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        # Script entry points may call this directly without app startup.
        # Load local .env once as a convenience, without overriding shell vars.
        load_dotenv(override=False)
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set. "
            "Copy .env.example -> .env and fill them in."
        )

    # Late import — supabase SDK pulls in postgrest, gotrue, etc. Keep it out
    # of test runs that don't actually need it.
    from supabase import create_client

    _CLIENT = create_client(url, key)
    return _CLIENT


# --- Helpers -----------------------------------------------------------------


def _assert_no_forbidden_fields(payload: dict[str, Any], context: str) -> None:
    """Raise ValueError if ``payload`` contains any image-related key.

    The check is flat — we don't recurse into nested dicts because the
    ``analysis`` blob can legitimately contain an "infographic_url" (Session
    6 will attach one) that is a rendered-output URL, not a raw bill URL.
    The forbidden list is specifically about raw consumer-provided images.
    """
    offenders = set(payload.keys()) & _FORBIDDEN_FIELDS
    if offenders:
        raise ValueError(
            f"Refusing to persist raw image data in {context}: "
            f"forbidden fields {sorted(offenders)} — see CLAUDE.md §3 Rule 2."
        )


def _extraction_to_db_dict(extraction: BillExtraction) -> dict[str, Any]:
    """Map BillExtraction -> the column subset ``bills`` table accepts."""
    d = asdict(extraction) if is_dataclass(extraction) else dict(extraction)

    # Map API contract's field name to the DB column name.
    if "subtotal_1_before_subsidy" in d:
        d["subtotal_1"] = d.pop("subtotal_1_before_subsidy")
    if "gruha_jyothi_subsidy_amount" in d:
        d["gj_subsidy_amount"] = d.pop("gruha_jyothi_subsidy_amount")
    if "is_gruha_jyothi_beneficiary" in d:
        d["is_gj_beneficiary"] = d.pop("is_gruha_jyothi_beneficiary")
    if "gjs_registration_date" in d:
        d["gj_registration_date"] = d.pop("gjs_registration_date")

    # Columns the ``bills`` schema doesn't have (is_mescom_bill is an
    # extraction-layer flag, not persisted; consumer_name is PII per Rule 2).
    for drop in (
        "is_mescom_bill",
        "consumer_name",
        "due_date",
        "arrears",
        "extraction_confidence",
    ):
        d.pop(drop, None)

    # Hold onto extraction_confidence as a column of its own — it's stored for
    # audit per tech spec §10.
    if is_dataclass(extraction):
        d["extraction_confidence"] = extraction.extraction_confidence

    # Belt-and-braces DPDPA check.
    _assert_no_forbidden_fields(d, "extraction dict")
    return d


# --- Public API --------------------------------------------------------------


def get_or_create_user(
    phone_number: str,
    *,
    client: Optional[Any] = None,
) -> dict[str, Any]:
    """Return the user row for ``phone_number``; create it if missing.

    Newly created rows have ``consent_given=false`` — that's the "AWAITING
    CONSENT" state in the FSM.
    """
    c = client or init_client()
    existing = (
        c.table("users")
        .select("*")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]

    inserted = (
        c.table("users")
        .insert({"phone_number": phone_number, "consent_given": False})
        .execute()
    )
    if not inserted.data:
        raise RuntimeError(f"failed to insert user for {phone_number!r}")
    return inserted.data[0]


def set_consent(
    phone_number: str,
    consent: bool,
    *,
    client: Optional[Any] = None,
) -> dict[str, Any]:
    """Flip ``consent_given`` for an existing user; create the row first if
    needed (so ``START`` from a never-contacted number works). Returns the
    updated row.
    """
    c = client or init_client()
    # Ensure the row exists first.
    get_or_create_user(phone_number, client=c)
    updated = (
        c.table("users")
        .update({"consent_given": consent})
        .eq("phone_number", phone_number)
        .execute()
    )
    if not updated.data:
        raise RuntimeError(f"failed to set consent for {phone_number!r}")
    return updated.data[0]


def set_account_id(
    phone_number: str,
    rr_number: str,
    *,
    client: Optional[Any] = None,
) -> dict[str, Any]:
    """Store the user's Account ID (RR Number) into their profile."""
    c = client or init_client()
    get_or_create_user(phone_number, client=c)
    updated = (
        c.table("users")
        .update({"rr_number": rr_number})
        .eq("phone_number", phone_number)
        .execute()
    )
    if not updated.data:
        raise RuntimeError(f"failed to set account id for {phone_number!r}")
    return updated.data[0]


def write_bill(
    user_id: str,
    extraction: BillExtraction,
    analysis: dict[str, Any],
    *,
    client: Optional[Any] = None,
    **forbidden_kwargs: Any,
) -> str:
    """Persist one analysed bill. Returns the inserted bill id.

    - Refuses any kwarg whose name is in the image-related forbidden list.
    - Refuses any forbidden key inside ``analysis``.
    - Never reads bytes from anywhere — only the extracted fields persist.
    """
    if forbidden_kwargs:
        _assert_no_forbidden_fields(forbidden_kwargs, "write_bill kwargs")

    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dict (JSONB payload)")
    _assert_no_forbidden_fields(analysis, "analysis blob")

    c = client or init_client()
    row = _extraction_to_db_dict(extraction)
    row["user_id"] = user_id
    row["analysis_result"] = analysis

    inserted = c.table("bills").insert(row).execute()
    if not inserted.data:
        raise RuntimeError("failed to insert bill row")
    return inserted.data[0]["id"]


def write_feedback(
    phone_number: str,
    feedback_text: Optional[str] = None,
    audio_url: Optional[str] = None,
    *,
    client: Optional[Any] = None,
) -> str:
    """Persist user feedback (text or voice)."""
    c = client or init_client()
    user = get_or_create_user(phone_number, client=c)

    payload = {
        "user_id": user["id"],
        "feedback_text": feedback_text,
        "audio_url": audio_url,
    }
    inserted = c.table("feedback").insert(payload).execute()
    if not inserted.data:
        raise RuntimeError("failed to insert feedback row")
    return inserted.data[0]["id"]


_VALID_LANGUAGES: frozenset[str] = frozenset({"en", "kn"})


def get_language_preference(
    phone_number: str,
    *,
    client: Optional[Any] = None,
) -> Optional[str]:
    """Return the persisted ``language_preference`` for a user, or ``None`` if
    the row doesn't exist or the column is unset."""
    c = client or init_client()
    existing = (
        c.table("users")
        .select("language_preference")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )
    if not existing.data:
        return None
    return existing.data[0].get("language_preference")


def set_language_preference(
    phone_number: str,
    language: str,
    *,
    client: Optional[Any] = None,
) -> dict[str, Any]:
    """Persist ``language_preference`` for a user; create the row first if
    needed (parallels ``set_consent``). Returns the updated row.

    Raises ``ValueError`` for any value outside ``{'en', 'kn'}`` to keep
    the DB CHECK constraint and the application invariant in lockstep.
    """
    if language not in _VALID_LANGUAGES:
        raise ValueError(
            f"language_preference must be one of {sorted(_VALID_LANGUAGES)}, "
            f"got {language!r}"
        )
    c = client or init_client()
    get_or_create_user(phone_number, client=c)
    updated = (
        c.table("users")
        .update({"language_preference": language})
        .eq("phone_number", phone_number)
        .execute()
    )
    if not updated.data:
        raise RuntimeError(f"failed to set language_preference for {phone_number!r}")
    return updated.data[0]


def delete_user_cascade(
    phone_number: str,
    *,
    client: Optional[Any] = None,
) -> tuple[bool, int]:
    """HARD delete the user row. Bills cascade. Returns ``(deleted_user,
    deleted_bill_count)``.

    Safe to call for never-consented users — the user row is still removed;
    ``deleted_bill_count`` is simply 0.
    """
    c = client or init_client()

    # Count bills before deleting so we can report how many cascaded out.
    user_row = (
        c.table("users")
        .select("id")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )
    if not user_row.data:
        return False, 0

    user_id = user_row.data[0]["id"]
    bills = (
        c.table("bills")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    bill_count = getattr(bills, "count", None) or len(bills.data or [])

    deleted = (
        c.table("users")
        .delete()
        .eq("phone_number", phone_number)
        .execute()
    )
    return bool(deleted.data), bill_count
