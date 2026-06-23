"""Smoke tests for app.py /whatsapp webhook routing.

Routes consent + extraction mocks; asserts the webhook:
- Intercepts STOP even for never-consented users.
- Blocks extraction for unconsented-user media.
- Acknowledges media from consented users (Session 5 will wire analysis).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app import create_app
from backend.consent.consent_manager import ConsentResponse, ConsentState

pytestmark = pytest.mark.smoke


@pytest.fixture
def client():
    # Bypass the env-var gate so tests don't need real Supabase / Twilio keys.
    app = create_app(validate_env=False)
    app.config["TESTING"] = True
    return app.test_client()


# =============================================================================
# Helpers
# =============================================================================


def _stub_response(text: str, state: ConsentState = ConsentState.CONSENTED, allow: bool = True):
    return ConsentResponse(state=state, message=text, allow_processing=allow)


def _post(client, body: str = "", num_media: int = 0):
    form = {
        "From": "whatsapp:+919876543210",
        "Body": body,
        "NumMedia": str(num_media),
    }
    if num_media:
        form["MediaUrl0"] = "https://api.twilio.com/.../ME123"
    return client.post("/whatsapp", data=form)


# =============================================================================
# Health
# =============================================================================


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    j = r.get_json()
    assert j["status"] == "ok"
    assert "version" in j


# =============================================================================
# STOP — intercepted before consent check, even for never-consented users
# =============================================================================


def test_stop_works_for_never_consented(client):
    with patch("backend.app.handle_stop_command", return_value=_stub_response(
        "Understood — no data was ever processed.",
        state=ConsentState.NEVER_CONTACTED, allow=False,
    )) as stop_mock, \
        patch("backend.app.check_consent") as consent_mock:
        r = _post(client, body="STOP")
    assert r.status_code == 200
    assert b"no data was ever processed" in r.data
    stop_mock.assert_called_once()
    # Consent check should never even run — STOP is unconditional.
    consent_mock.assert_not_called()


def test_stop_lowercase_also_works(client):
    with patch("backend.app.handle_stop_command", return_value=_stub_response(
        "Understood — no data was ever processed.",
        state=ConsentState.NEVER_CONTACTED, allow=False,
    )) as stop_mock:
        _post(client, body="stop")
    stop_mock.assert_called_once()


# =============================================================================
# START — transitions user to CONSENTED
# =============================================================================


def test_start_triggers_consent_handler(client):
    with patch("backend.app.handle_start_command", return_value=_stub_response(
        "✅ Thank you! You're all set.", state=ConsentState.CONSENTED, allow=True,
    )) as start_mock:
        r = _post(client, body="START")
    assert r.status_code == 200
    assert b"Thank you" in r.data
    start_mock.assert_called_once()


# =============================================================================
# Consent gate — unconsented user sending media gets rejected, no extraction
# =============================================================================


def test_unconsented_user_with_media_does_not_trigger_extraction(client):
    # Explicitly confirm that no extraction module is invoked. If app.py ever
    # grows a wiring bug that leaks image bytes to Gemini pre-consent, this
    # test catches it.
    with patch("backend.app.check_consent", return_value=ConsentState.AWAITING_CONSENT), \
         patch("backend.app.unconsented_media_response", return_value=_stub_response(
             "I need your consent before analyzing bills. Please reply START.",
             state=ConsentState.AWAITING_CONSENT, allow=False,
         )) as media_resp_mock, \
         patch("backend.extraction.pipeline.run_extraction") as run_mock, \
         patch("backend.extraction.gemini_client.extract_bill") as extract_mock:
        r = _post(client, body="", num_media=1)
    assert r.status_code == 200
    assert b"consent" in r.data
    media_resp_mock.assert_called_once()
    run_mock.assert_not_called()
    extract_mock.assert_not_called()


def test_unconsented_text_triggers_first_contact(client):
    with patch("backend.app.check_consent", return_value=ConsentState.NEVER_CONTACTED), \
         patch("backend.app.first_contact_response", return_value=_stub_response(
             "Welcome! Reply START to continue.",
             state=ConsentState.AWAITING_CONSENT, allow=False,
         )) as fc_mock:
        r = _post(client, body="hello")
    assert r.status_code == 200
    assert b"Welcome" in r.data
    fc_mock.assert_called_once()


# =============================================================================
# Consented user
# =============================================================================


def test_consented_user_with_media_gets_analyzing_ack(client):
    """Webhook returns TwiML ack immediately; the real response lands
    asynchronously via the Twilio REST API (Session 5)."""
    with patch("backend.app.check_consent", return_value=ConsentState.CONSENTED), \
         patch("backend.app._process_bill_with_error_isolation") as worker:
        r = _post(client, body="", num_media=1)
    assert r.status_code == 200
    assert b"Analyzing" in r.data or b"analyz" in r.data.lower()
    # The async worker is called (in a thread) with the right arguments.
    # We can't directly assert it ran — the thread is daemon. But we can
    # assert the webhook handler referenced the function by patching it
    # at module level; a daemon thread would have called it.
    # (Threading is hard to assert deterministically; this test documents
    # the intent. The next test exercises the sync path directly.)


def test_process_bill_and_dispatch_happy_path():
    """Exercise the sync processor directly — mock all external deps."""
    from backend.app import process_bill_and_dispatch

    # Build a real extraction + analysis for Nikhil.
    from backend.analysis.models import BillExtraction, ExtractionStatus
    nikhil = BillExtraction(
        is_mescom_bill=True, tariff_category="LT-1",
        billing_period_end="2026-03-15", billing_period_days=30,
        sanctioned_load_kw=3.0, units_consumed=210,
        subtotal_1_before_subsidy=1943.22, net_bill_amount=1943.22,
        is_gruha_jyothi_beneficiary=False,
    )

    class _FakeResult:
        status = ExtractionStatus.OK
        extraction = nikhil

    sent_messages = []

    def _fake_send_text(to_phone, body, **_):
        sent_messages.append((to_phone, body))
        return "SM123"

    class _FakeSupabase:
        def get_or_create_user(self, phone, **_):
            return {"id": "user-1", "phone_number": phone}
        def write_bill(self, **_):
            return "bill-1"

    # Patch the whole chain.
    with patch("backend.extraction.twilio_media.fetch_twilio_media", return_value=b"\x89PNG..."), \
         patch("backend.extraction.pipeline.run_extraction", return_value=_FakeResult()), \
         patch("backend.output.twilio_dispatcher.send_text", side_effect=_fake_send_text), \
         patch("backend.db.supabase_client.init_client", return_value=None), \
         patch("backend.db.supabase_client.get_or_create_user", return_value={"id": "user-1"}), \
         patch("backend.db.supabase_client.write_bill", return_value="bill-1") as write_bill_mock:
        msg = process_bill_and_dispatch(
            from_number="whatsapp:+919876543210",
            media_url="https://api.twilio.com/.../ME123",
        )

    # Responses > 1600 chars split across multiple WhatsApp messages.
    assert len(sent_messages) >= 1
    assert all(m[0] == "whatsapp:+919876543210" for m in sent_messages)
    concatenated = "\n".join(m[1] for m in sent_messages)
    assert "Fixed Charge Alert" in concatenated
    assert "1,740" in concatenated
    # Supabase write happens AFTER dispatch — user gets their answer even
    # if DB is down.
    write_bill_mock.assert_called_once()
    assert msg == "\n".join(m[1] for m in sent_messages) or msg == sent_messages[0][1]


def test_process_bill_and_dispatch_pre_april_bill():
    """Pre-April-2025 extraction gets the decline message, no analysis."""
    from backend.app import process_bill_and_dispatch
    from backend.analysis.models import ExtractionStatus

    class _FakeResult:
        status = ExtractionStatus.PRE_APRIL_2025
        extraction = None

    sent = []
    with patch("backend.extraction.twilio_media.fetch_twilio_media", return_value=b"img"), \
         patch("backend.extraction.pipeline.run_extraction", return_value=_FakeResult()), \
         patch("backend.output.twilio_dispatcher.send_text",
               side_effect=lambda to, body, **_: sent.append(body) or "SM"), \
         patch("backend.db.supabase_client.init_client", return_value=None), \
         patch("backend.db.supabase_client.write_bill") as write_mock:
        process_bill_and_dispatch("whatsapp:+919876543210", "https://x")

    assert len(sent) == 1
    assert "before April 2025" in sent[0]
    # No DB write — analysis never ran.
    write_mock.assert_not_called()


def test_process_bill_and_dispatch_not_mescom():
    from backend.app import process_bill_and_dispatch
    from backend.analysis.models import ExtractionStatus

    class _FakeResult:
        status = ExtractionStatus.NOT_MESCOM
        extraction = None

    sent = []
    with patch("backend.extraction.twilio_media.fetch_twilio_media", return_value=b"img"), \
         patch("backend.extraction.pipeline.run_extraction", return_value=_FakeResult()), \
         patch("backend.output.twilio_dispatcher.send_text",
               side_effect=lambda to, body, **_: sent.append(body) or "SM"), \
         patch("backend.db.supabase_client.write_bill") as write_mock:
        process_bill_and_dispatch("whatsapp:+919876543210", "https://x")

    assert "couldn't read" in sent[0].lower() or "MESCOM" in sent[0]
    write_mock.assert_not_called()


def test_process_bill_and_dispatch_gemini_exception_isolated():
    """Any exception leads to gemini_error_response — user never gets nothing."""
    from backend.app import process_bill_and_dispatch

    sent = []
    with patch("backend.extraction.twilio_media.fetch_twilio_media", return_value=b"img"), \
         patch("backend.extraction.pipeline.run_extraction",
               side_effect=RuntimeError("something weird")), \
         patch("backend.output.twilio_dispatcher.send_text",
               side_effect=lambda to, body, **_: sent.append(body) or "SM"):
        process_bill_and_dispatch("whatsapp:+919876543210", "https://x")

    assert "try again" in sent[0].lower()


def test_consented_user_with_text_gets_photo_prompt(client):
    with patch("backend.app.check_consent", return_value=ConsentState.CONSENTED):
        r = _post(client, body="hey")
    assert r.status_code == 200
    assert b"photo" in r.data.lower() or b"bill" in r.data.lower()


# =============================================================================
# Hardening — missing From field
# =============================================================================


def test_missing_sender_returns_400(client):
    r = client.post("/whatsapp", data={"Body": "hello"})
    assert r.status_code == 400
