"""Smoke tests for consent/consent_manager.py.

Reuses FakeSupabaseClient from backend.tests.test_supabase. Verifies all state
transitions enumerated in tech spec §9.3 and PRD §2.4.
"""
from __future__ import annotations

import pytest

from backend.consent.consent_manager import (
    ALREADY_CONSENTED_TEMPLATE,
    FIRST_CONTACT_TEMPLATE,
    LANG_SET_TO_EN_TEMPLATE,
    LANG_SET_TO_KN_TEMPLATE,
    START_ACK_TEMPLATE,
    STOP_CONSENTED_TEMPLATE,
    STOP_NEVER_CONSENTED_TEMPLATE,
    ConsentState,
    check_consent,
    first_contact_response,
    get_language_preference,
    handle_language_toggle,
    handle_start_command,
    handle_stop_command,
    unconsented_media_response,
)
from backend.db import supabase_client

from backend.tests.test_supabase import FakeSupabaseClient, nikhil_extraction  # noqa: F401

pytestmark = pytest.mark.smoke


@pytest.fixture
def fake_client() -> FakeSupabaseClient:
    return FakeSupabaseClient()


PHONE = "+919876543210"


# =============================================================================
# State machine — never_contacted → awaiting_consent → consented
# =============================================================================


class TestStateMachine:
    def test_never_contacted_state(self, fake_client):
        assert check_consent(PHONE, client=fake_client) is ConsentState.NEVER_CONTACTED

    def test_first_contact_creates_awaiting_row(self, fake_client):
        resp = first_contact_response(PHONE, client=fake_client)
        assert resp.state is ConsentState.AWAITING_CONSENT
        assert resp.message == FIRST_CONTACT_TEMPLATE
        assert resp.allow_processing is False
        # Row is created with consent_given=false.
        assert check_consent(PHONE, client=fake_client) is ConsentState.AWAITING_CONSENT

    def test_start_transitions_to_consented(self, fake_client):
        resp = handle_start_command(PHONE, client=fake_client)
        assert resp.state is ConsentState.CONSENTED
        assert resp.message == START_ACK_TEMPLATE
        assert resp.allow_processing is True
        assert check_consent(PHONE, client=fake_client) is ConsentState.CONSENTED

    def test_start_is_idempotent_on_already_consented(self, fake_client):
        handle_start_command(PHONE, client=fake_client)
        second = handle_start_command(PHONE, client=fake_client)
        assert second.state is ConsentState.CONSENTED
        assert second.message == ALREADY_CONSENTED_TEMPLATE
        assert second.allow_processing is True
        # Still exactly one row — no duplicate inserts.
        assert len(fake_client.users) == 1

    def test_first_contact_then_start(self, fake_client):
        first_contact_response(PHONE, client=fake_client)
        assert check_consent(PHONE, client=fake_client) is ConsentState.AWAITING_CONSENT
        handle_start_command(PHONE, client=fake_client)
        assert check_consent(PHONE, client=fake_client) is ConsentState.CONSENTED


# =============================================================================
# STOP command — two message variants per PRD §2.4
# =============================================================================


class TestStop:
    def test_stop_on_consented_user_hard_deletes(self, fake_client):
        handle_start_command(PHONE, client=fake_client)
        assert len(fake_client.users) == 1
        resp = handle_stop_command(PHONE, client=fake_client)
        assert resp.state is ConsentState.NEVER_CONTACTED
        assert resp.allow_processing is False
        assert "permanently deleted" in resp.message
        # Hard delete — no row remains.
        assert fake_client.users == []

    def test_stop_on_never_consented_returns_no_data_variant(self, fake_client):
        resp = handle_stop_command(PHONE, client=fake_client)
        assert resp.state is ConsentState.NEVER_CONTACTED
        assert resp.message == STOP_NEVER_CONSENTED_TEMPLATE
        # No DB mutation for never-contacted user.
        assert fake_client.users == []

    def test_stop_on_awaiting_consent_returns_no_data_variant(self, fake_client):
        first_contact_response(PHONE, client=fake_client)
        assert len(fake_client.users) == 1
        resp = handle_stop_command(PHONE, client=fake_client)
        assert resp.message == STOP_NEVER_CONSENTED_TEMPLATE
        assert fake_client.users == []  # placeholder row still purged.

    def test_stop_reports_bill_count_after_cascade(self, fake_client, nikhil_extraction):
        handle_start_command(PHONE, client=fake_client)
        user = supabase_client.get_or_create_user(PHONE, client=fake_client)
        for _ in range(2):
            supabase_client.write_bill(
                user_id=user["id"],
                extraction=nikhil_extraction,
                analysis={},
                client=fake_client,
            )
        resp = handle_stop_command(PHONE, client=fake_client)
        assert "2 bill records removed" in resp.message


# =============================================================================
# Unconsented media path — the tight prompt, no processing allowed
# =============================================================================


class TestUnconsentedMedia:
    def test_unconsented_media_response_does_not_touch_db(self, fake_client):
        resp = unconsented_media_response()
        assert resp.state is ConsentState.AWAITING_CONSENT
        assert resp.allow_processing is False
        assert "START" in resp.message or "start" in resp.message.lower()
        # Fake client was never used — pure function, no DB touch.
        assert fake_client.users == []


# =============================================================================
# Template sanity — every template includes Kannada text per PRD §2.1
# =============================================================================


class TestTemplateCoverage:
    def test_first_contact_has_kannada(self):
        # At least one character in the Kannada Unicode block (U+0C80–U+0CFF).
        assert any("\u0c80" <= ch <= "\u0cff" for ch in FIRST_CONTACT_TEMPLATE)

    def test_start_ack_has_kannada(self):
        assert any("\u0c80" <= ch <= "\u0cff" for ch in START_ACK_TEMPLATE)

    def test_stop_consented_has_kannada(self):
        # Use the .format result to ensure no placeholder breakage.
        msg = STOP_CONSENTED_TEMPLATE.format(bill_count=3, s="s")
        assert any("\u0c80" <= ch <= "\u0cff" for ch in msg)

    def test_stop_never_consented_has_kannada(self):
        assert any("\u0c80" <= ch <= "\u0cff" for ch in STOP_NEVER_CONSENTED_TEMPLATE)


# =============================================================================
# LANG toggle + first-contact language detection
# =============================================================================


class TestLanguageToggle:
    def test_lang_on_never_contacted_routes_to_first_contact(self, fake_client):
        resp = handle_language_toggle(PHONE, client=fake_client)
        assert resp.state is ConsentState.AWAITING_CONSENT
        assert resp.message == FIRST_CONTACT_TEMPLATE
        # Row exists now so a follow-up STOP can delete it.
        assert len(fake_client.users) == 1

    def test_lang_after_consent_flips_none_to_kn(self, fake_client):
        first_contact_response(PHONE, client=fake_client)
        handle_start_command(PHONE, client=fake_client)
        resp = handle_language_toggle(PHONE, client=fake_client)
        assert resp.message == LANG_SET_TO_KN_TEMPLATE
        assert get_language_preference(PHONE, client=fake_client) == "kn"

    def test_lang_flips_kn_to_en(self, fake_client):
        first_contact_response(PHONE, client=fake_client)
        handle_start_command(PHONE, client=fake_client)
        # First toggle: None -> kn
        handle_language_toggle(PHONE, client=fake_client)
        # Second toggle: kn -> en
        resp = handle_language_toggle(PHONE, client=fake_client)
        assert resp.message == LANG_SET_TO_EN_TEMPLATE
        assert get_language_preference(PHONE, client=fake_client) == "en"

    def test_lang_keeps_consent_state(self, fake_client):
        first_contact_response(PHONE, client=fake_client)
        handle_start_command(PHONE, client=fake_client)
        handle_language_toggle(PHONE, client=fake_client)
        # User should still be CONSENTED after a LANG toggle.
        assert check_consent(PHONE, client=fake_client) is ConsentState.CONSENTED

    def test_lang_confirmation_includes_footer(self):
        for tmpl in (LANG_SET_TO_EN_TEMPLATE, LANG_SET_TO_KN_TEMPLATE):
            assert "LANG" in tmpl
            assert "STOP" in tmpl


class TestFirstContactDetection:
    def test_kannada_message_persists_kn_preference(self, fake_client):
        first_contact_response(PHONE, "\u0ca8\u0cae\u0cb8\u0ccd\u0c95\u0cbe\u0cb0", client=fake_client)
        assert get_language_preference(PHONE, client=fake_client) == "kn"

    def test_english_message_persists_en_preference(self, fake_client):
        first_contact_response(PHONE, "hi there", client=fake_client)
        assert get_language_preference(PHONE, client=fake_client) == "en"

    def test_empty_body_does_not_set_preference(self, fake_client):
        first_contact_response(PHONE, "", client=fake_client)
        assert get_language_preference(PHONE, client=fake_client) is None

    def test_default_arg_does_not_set_preference(self, fake_client):
        # Backward-compatible call site (no message_body) should not write.
        first_contact_response(PHONE, client=fake_client)
        assert get_language_preference(PHONE, client=fake_client) is None

    def test_stop_clears_in_memory_language(self, fake_client):
        # Force a Supabase failure to exercise in-memory fallback, then STOP.
        from backend.consent import consent_manager as cm
        cm._LOCAL_LANGUAGE[PHONE] = "kn"
        handle_stop_command(PHONE, client=fake_client)
        assert PHONE not in cm._LOCAL_LANGUAGE
