"""Smoke tests for Session 5.5 two-turn follow-up flow.

Three surfaces under test:
- ``output.last_bill_cache`` — set/get round-trip, 30-min TTL, clear.
- ``output.response_composer`` follow-up composers — personalised content.
- ``app.py /whatsapp`` routing — keyword dispatch, limit enforcement,
  STOP cache-clear, successful-analysis cache-populate.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA
from backend.output import last_bill_cache
from backend.output.response_composer import (
    compose_cliff_followup,
    compose_fixed_followup,
    compose_followup_limit_reached_response,
    compose_no_recent_bill_response,
    compose_solar_followup,
    compose_subsidy_followup,
)

pytestmark = pytest.mark.smoke


# =============================================================================
# Fixture builders
# =============================================================================


def _extraction_for(persona) -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-03-15",
        billing_period_days=persona.billing_period_days,
        sanctioned_load_kw=persona.sanctioned_load_kw,
        units_consumed=persona.units_consumed,
        subtotal_1_before_subsidy=persona.expected_subtotal_1,
        net_bill_amount=persona.expected_net_bill,
        is_gruha_jyothi_beneficiary=persona.is_gj_beneficiary,
        historical_avg_baseline=persona.gj_historical_avg_units,
        entitlement_units=persona.gj_entitlement_units,
        gruha_jyothi_subsidy_amount=(
            persona.expected_subtotal_1 if persona.is_gj_beneficiary else None
        ),
        gjs_registration_date="2023-08-26" if persona.is_gj_beneficiary else None,
    )


def _rehena_extraction() -> BillExtraction:
    """170-unit GJ bill — crossed entitlement (Level 1 soft step)."""
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2025-12-06",
        billing_period_days=30,
        sanctioned_load_kw=1.0,
        units_consumed=170,
        energy_charges=986.0, fixed_charges=145.0, pg_surcharge=61.2,
        electricity_tax=88.74, fppca=62.9, other_charges=0.0,
        subtotal_1_before_subsidy=1343.84,
        is_gruha_jyothi_beneficiary=True,
        gjs_registration_date="2023-06-22",
        historical_avg_baseline=111.0, entitlement_units=123.0,
        gruha_jyothi_subsidy_amount=1012.4,
        net_bill_amount=331.44,
    )


def _koppala_extraction() -> BillExtraction:
    """390-unit GJ bill — crossed 200, Level 2 hard cliff."""
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-04-10",
        billing_period_days=31,
        sanctioned_load_kw=2.0,
        units_consumed=390,
        subtotal_1_before_subsidy=3044.18,
        net_bill_amount=3044.18,
        is_gruha_jyothi_beneficiary=True,
        historical_avg_baseline=57.0,
        entitlement_units=63.0,
        gruha_jyothi_subsidy_amount=0.0,
        gjs_registration_date="2023-07-25",
    )


@pytest.fixture(autouse=True)
def _reset_cache():
    """Every test starts with an empty cache."""
    last_bill_cache._reset_for_tests()
    yield
    last_bill_cache._reset_for_tests()


# =============================================================================
# last_bill_cache — set/get, TTL, increment, clear
# =============================================================================


PHONE = "whatsapp:+919876543210"


class TestCache:
    def test_get_returns_none_for_unknown_phone(self):
        assert last_bill_cache.get_last_bill(PHONE) is None

    def test_set_then_get_round_trips(self):
        ext = _extraction_for(NIKHIL)
        analysis = analyze_bill(ext)
        last_bill_cache.set_last_bill(PHONE, analysis, ext)
        got = last_bill_cache.get_last_bill(PHONE)
        assert got is not None
        assert got["follow_up_count"] == 0
        assert got["extraction"].units_consumed == 210
        assert got["analysis"].chosen_template == "non_gj"

    def test_increment_follow_up(self):
        ext = _extraction_for(NIKHIL)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        assert last_bill_cache.increment_follow_up(PHONE) == 1
        assert last_bill_cache.increment_follow_up(PHONE) == 2
        assert last_bill_cache.get_last_bill(PHONE)["follow_up_count"] == 2

    def test_increment_on_unknown_phone_returns_zero(self):
        assert last_bill_cache.increment_follow_up(PHONE) == 0

    def test_clear_bill_removes_entry(self):
        ext = _extraction_for(NIKHIL)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        last_bill_cache.clear_bill(PHONE)
        assert last_bill_cache.get_last_bill(PHONE) is None

    def test_clear_bill_is_idempotent_on_unknown(self):
        # Should not raise.
        last_bill_cache.clear_bill("whatsapp:+919999999999")

    def test_get_returns_none_after_ttl(self):
        ext = _extraction_for(NIKHIL)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        # Fast-forward 31 minutes.
        future = datetime.now(timezone.utc) + timedelta(minutes=31)
        with patch.object(last_bill_cache, "_now", return_value=future):
            assert last_bill_cache.get_last_bill(PHONE) is None

    def test_set_overwrites_prior_entry(self):
        ext1 = _extraction_for(NIKHIL)
        ext2 = _rehena_extraction()
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext1), ext1)
        last_bill_cache.increment_follow_up(PHONE)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext2), ext2)
        got = last_bill_cache.get_last_bill(PHONE)
        assert got["extraction"].units_consumed == 170
        assert got["follow_up_count"] == 0   # reset on new bill


# =============================================================================
# Composer content — personas render correctly
# =============================================================================


class TestSolarFollowupComposer:
    def test_nikhil_renders_briefing_values(self):
        ext = _extraction_for(NIKHIL)
        msg = compose_solar_followup(ext, analyze_bill(ext))
        assert "45 months" in msg
        assert "87,000" in msg              # net cost
        assert "1,65,000" in msg or "165,000" in msg   # pre-subsidy cost
        assert "Rs. 78,000" in msg          # PMSG subsidy
        assert "pmsuryaghar.gov.in" in msg
        assert "srtpv.mesco.in" in msg

    def test_nikhil_contains_monthly_benefit_breakdown(self):
        ext = _extraction_for(NIKHIL)
        msg = compose_solar_followup(ext, analyze_bill(ext))
        assert "Rs. 1,930" in msg           # monthly benefit
        assert "Grid bill eliminated" in msg
        assert "Export credit" in msg


class TestFixedFollowupComposer:
    def test_nikhil_explains_fct_fires(self):
        ext = _extraction_for(NIKHIL)
        msg = compose_fixed_followup(ext, analyze_bill(ext))
        assert "Fixed Charges" in msg
        assert "145" in msg                 # Rs./kW rate
        assert "1,740" in msg               # annual overpayment

    def test_priya_explains_no_fct(self):
        # Priya's 2 kW sanctioned is at the FCT floor → no trap.
        ext = _extraction_for(PRIYA)
        msg = compose_fixed_followup(ext, analyze_bill(ext))
        assert "145" in msg
        # No "Rs. 1,740" since trap doesn't fire.
        assert "1,740" not in msg


class TestSubsidyFollowupComposer:
    def test_priya_renders_entitlement_formula(self):
        ext = _extraction_for(PRIYA)
        msg = compose_subsidy_followup(ext, analyze_bill(ext))
        assert "Gruha Jyothi" in msg
        assert "115" in msg                 # entitlement
        assert "+ 10" in msg                # formula component

    def test_non_gj_user_gets_enrollment_info(self):
        ext = _extraction_for(NIKHIL)
        msg = compose_subsidy_followup(ext, analyze_bill(ext))
        assert "sevasindhu" in msg or "Karnataka One" in msg
        assert "NOT currently enrolled" in msg


class TestCliffFollowupComposer:
    def test_rehena_mentions_entitlement_and_soft_step(self):
        ext = _rehena_extraction()
        msg = compose_cliff_followup(ext, analyze_bill(ext))
        assert "123" in msg                 # her entitlement
        assert "Soft Step" in msg
        assert "over" in msg.lower()        # since 170 > 123

    def test_koppala_mentions_hard_cliff_and_full_bill(self):
        ext = _koppala_extraction()
        msg = compose_cliff_followup(ext, analyze_bill(ext))
        assert "390" in msg
        assert "200" in msg                 # hard cap
        assert "ENTIRE" in msg              # subsidy lost for month
        # Explicit 3,044 Rs (the full bill she actually owed)
        assert "3,044" in msg or "3044" in msg

    def test_priya_under_entitlement_shows_room(self):
        ext = _extraction_for(PRIYA)
        msg = compose_cliff_followup(ext, analyze_bill(ext))
        assert "110" in msg                 # her consumption
        assert "115" in msg                 # her entitlement
        assert "room" in msg.lower() or "of room" in msg.lower()

    def test_non_gj_shows_generic_cliff_warning(self):
        ext = _extraction_for(NIKHIL)
        msg = compose_cliff_followup(ext, analyze_bill(ext))
        assert "not currently enrolled" in msg.lower()


class TestLimitReached:
    def test_template_prompts_for_new_bill(self):
        msg = compose_followup_limit_reached_response()
        assert "follow-up" in msg.lower()
        assert "bill" in msg.lower()


class TestNoRecentBill:
    def test_template_prompts_for_a_photo(self):
        msg = compose_no_recent_bill_response()
        assert "bill" in msg.lower()
        assert any(k in msg for k in ("SOLAR", "FIXED", "SUBSIDY", "CLIFF"))


# =============================================================================
# Webhook routing
# =============================================================================


@pytest.fixture
def client():
    from backend.app import create_app
    app = create_app(validate_env=False)
    app.config["TESTING"] = True
    return app.test_client()


def _post(client, body: str, phone: str = PHONE, num_media: int = 0):
    form = {"From": phone, "Body": body, "NumMedia": str(num_media)}
    if num_media:
        form["MediaUrl0"] = "https://api.twilio.com/.../ME123"
    return client.post("/whatsapp", data=form)


class TestWebhookRouting:
    def test_solar_with_no_cache_returns_no_recent_bill(self, client):
        with patch("backend.app.check_consent") as consent_mock:
            from backend.consent.consent_manager import ConsentState
            consent_mock.return_value = ConsentState.CONSENTED
            r = _post(client, body="SOLAR")
        assert r.status_code == 200
        assert b"No recent bill" in r.data

    def test_solar_with_nikhil_cache_returns_solar_breakdown(self, client):
        ext = _extraction_for(NIKHIL)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        with patch("backend.app.check_consent") as consent_mock:
            from backend.consent.consent_manager import ConsentState
            consent_mock.return_value = ConsentState.CONSENTED
            r = _post(client, body="SOLAR")
        assert r.status_code == 200
        assert b"Solar Eligibility Detail" in r.data
        assert b"45 months" in r.data
        # Count was bumped to 1.
        assert last_bill_cache.get_last_bill(PHONE)["follow_up_count"] == 1

    def test_cliff_with_rehena_cache_fires_soft_step_text(self, client):
        ext = _rehena_extraction()
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        with patch("backend.app.check_consent") as consent_mock:
            from backend.consent.consent_manager import ConsentState
            consent_mock.return_value = ConsentState.CONSENTED
            r = _post(client, body="CLIFF")
        assert r.status_code == 200
        assert b"200" in r.data             # 200-unit hard cap mentioned
        assert b"ENTIRE" in r.data          # subsidy-loss line

    def test_lowercase_keyword_also_works(self, client):
        ext = _extraction_for(NIKHIL)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        with patch("backend.app.check_consent") as consent_mock:
            from backend.consent.consent_manager import ConsentState
            consent_mock.return_value = ConsentState.CONSENTED
            r = _post(client, body="solar")
        assert b"Solar Eligibility Detail" in r.data

    def test_third_followup_hits_limit(self, client):
        ext = _extraction_for(NIKHIL)
        last_bill_cache.set_last_bill(
            PHONE, analyze_bill(ext), ext, follow_up_count=2
        )
        with patch("backend.app.check_consent") as consent_mock:
            from backend.consent.consent_manager import ConsentState
            consent_mock.return_value = ConsentState.CONSENTED
            r = _post(client, body="SOLAR")
        assert r.status_code == 200
        assert b"used your follow-up" in r.data or b"follow-up questions" in r.data

    def test_unknown_text_still_prompts_for_photo(self, client):
        with patch("backend.app.check_consent") as consent_mock:
            from backend.consent.consent_manager import ConsentState
            consent_mock.return_value = ConsentState.CONSENTED
            r = _post(client, body="hello there")
        assert r.status_code == 200
        assert b"bill" in r.data.lower()
        assert b"Solar Eligibility Detail" not in r.data


class TestStopClearsCache:
    def test_stop_wipes_cached_bill(self, client):
        ext = _extraction_for(PRIYA)
        last_bill_cache.set_last_bill(PHONE, analyze_bill(ext), ext)
        assert last_bill_cache.get_last_bill(PHONE) is not None

        # STOP executes without touching consent state checks by patching the
        # Supabase guts — consent_manager uses in-memory fallback on failure.
        with patch("backend.app.handle_stop_command") as stop_mock:
            from backend.consent.consent_manager import (
                ConsentResponse, ConsentState, handle_stop_command,
            )
            # Invoke the real handler so its side effects fire.
            stop_mock.side_effect = handle_stop_command
            r = _post(client, body="STOP")

        assert r.status_code == 200
        assert last_bill_cache.get_last_bill(PHONE) is None


# =============================================================================
# Successful-analysis path populates the cache
# =============================================================================


class TestProcessBillCachePopulation:
    def test_cache_set_after_successful_dispatch(self):
        """process_bill_and_dispatch populates last_bill_cache on OK path."""
        from backend.app import process_bill_and_dispatch
        from backend.analysis.models import ExtractionStatus

        ext = _extraction_for(NIKHIL)

        class _FakeResult:
            status = ExtractionStatus.OK
            extraction = ext

        with patch("backend.extraction.twilio_media.fetch_twilio_media", return_value=b"img"), \
             patch("backend.extraction.pipeline.run_extraction", return_value=_FakeResult()), \
             patch("backend.output.twilio_dispatcher.send_text", return_value="SM"), \
             patch("backend.db.supabase_client.init_client", return_value=None), \
             patch("backend.db.supabase_client.get_or_create_user", return_value={"id": "u"}), \
             patch("backend.db.supabase_client.write_bill", return_value="b"):
            process_bill_and_dispatch(PHONE, "https://x")

        cached = last_bill_cache.get_last_bill(PHONE)
        assert cached is not None
        assert cached["extraction"].units_consumed == 210
        assert cached["follow_up_count"] == 0

    def test_cache_not_set_on_pre_april_bill(self):
        from backend.app import process_bill_and_dispatch
        from backend.analysis.models import ExtractionStatus

        class _FakeResult:
            status = ExtractionStatus.PRE_APRIL_2025
            extraction = None

        with patch("backend.extraction.twilio_media.fetch_twilio_media", return_value=b"img"), \
             patch("backend.extraction.pipeline.run_extraction", return_value=_FakeResult()), \
             patch("backend.output.twilio_dispatcher.send_text", return_value="SM"):
            process_bill_and_dispatch(PHONE, "https://x")

        assert last_bill_cache.get_last_bill(PHONE) is None
