"""Live webhook integration tests — require a real Supabase project.

Skipped by default. Run with ``pytest -v -m integration`` after setting
``SUPABASE_URL`` and ``SUPABASE_KEY`` in ``.env`` and applying
``db/schema.sql`` via ``scripts/init_supabase.py`` (Session 4 addendum — not
built yet, run the SQL manually in the Supabase SQL editor for now).

These tests mutate the real ``users`` / ``bills`` tables. Use a dedicated
hackathon Supabase project, not a production one.
"""
from __future__ import annotations

import os
import uuid

import pytest

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

pytestmark = pytest.mark.integration


def _require_supabase() -> None:
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")):
        pytest.skip(
            "SUPABASE_URL / SUPABASE_KEY not set. Live webhook tests cannot "
            "run without a real Supabase project."
        )


@pytest.fixture
def scratch_phone() -> str:
    """A throwaway phone number that won't collide with any real demo user."""
    suffix = uuid.uuid4().hex[:8]
    return f"whatsapp:+91999{suffix[:7]}"


@pytest.fixture
def webhook_client():
    from backend.app import create_app
    app = create_app(validate_env=False)
    app.config["TESTING"] = True
    return app.test_client()


def _post(client, phone: str, body: str = "", num_media: int = 0):
    form = {"From": phone, "Body": body, "NumMedia": str(num_media)}
    if num_media:
        form["MediaUrl0"] = "https://api.twilio.com/.../ME_scratch"
    return client.post("/whatsapp", data=form)


def test_start_sets_consent_in_supabase(webhook_client, scratch_phone):
    _require_supabase()
    from backend.consent.consent_manager import ConsentState, check_consent
    from backend.db import supabase_client

    try:
        r = _post(webhook_client, scratch_phone, body="START")
        assert r.status_code == 200
        assert check_consent(scratch_phone) is ConsentState.CONSENTED
    finally:
        # Teardown — never leave test rows behind.
        supabase_client.delete_user_cascade(scratch_phone)


def test_stop_hard_deletes_user(webhook_client, scratch_phone):
    _require_supabase()
    from backend.consent.consent_manager import ConsentState, check_consent
    from backend.db import supabase_client

    try:
        _post(webhook_client, scratch_phone, body="START")
        assert check_consent(scratch_phone) is ConsentState.CONSENTED
        r = _post(webhook_client, scratch_phone, body="STOP")
        assert r.status_code == 200
        assert check_consent(scratch_phone) is ConsentState.NEVER_CONTACTED
    finally:
        supabase_client.delete_user_cascade(scratch_phone)


def test_stop_on_never_consented_returns_no_data_variant(webhook_client, scratch_phone):
    _require_supabase()
    from backend.consent.consent_manager import ConsentState, check_consent

    r = _post(webhook_client, scratch_phone, body="STOP")
    assert r.status_code == 200
    assert b"no data was ever processed" in r.data
    assert check_consent(scratch_phone) is ConsentState.NEVER_CONTACTED
