"""Smoke tests for output.response_composer."""
from __future__ import annotations

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA, SUNITA
from backend.output.response_composer import (
    compose_bad_photo_response,
    compose_for_result,
    compose_gemini_error_response,
    compose_gj_response,
    compose_non_gj_response,
    compose_pre_april_2025_response,
    split_for_whatsapp,
)

pytestmark = pytest.mark.smoke


def _persona_extraction(persona) -> BillExtraction:
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


# =============================================================================
# Non-GJ composition (Nikhil)
# =============================================================================


class TestNonGJResponse:
    @pytest.fixture
    def msg(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        return compose_non_gj_response(r)

    def test_contains_fixed_charge_alert(self, msg):
        assert "Fixed Charge Alert" in msg

    def test_contains_1740_annual_number(self, msg):
        # Load-bearing pitch number.
        assert "1,740" in msg

    def test_contains_pmsg_eligible(self, msg):
        assert "PM Surya Ghar" in msg
        assert "78,000" in msg or "Rs. 78" in msg

    def test_contains_solar_roi_section(self, msg):
        assert "Solar ROI" in msg
        assert "Payback" in msg

    def test_contains_co2_offset(self, msg):
        assert "CO2 offset" in msg or "CO₂" in msg

    def test_contains_unit_count(self, msg):
        assert "210" in msg

    def test_does_not_mention_gruha_jyothi_benefit_section(self, msg):
        # Non-GJ user → no "Gruha Jyothi Benefit" header.
        assert "Gruha Jyothi Benefit" not in msg


# =============================================================================
# GJ composition (Priya) — highest-precedence warning only
# =============================================================================


class TestGJResponse:
    @pytest.fixture
    def msg(self):
        r = analyze_bill(_persona_extraction(PRIYA))
        return compose_gj_response(r)

    def test_contains_gj_benefit_header(self, msg):
        assert "Gruha Jyothi Benefit" in msg

    def test_shows_paid_zero(self, msg):
        # Priya's net bill is Rs. 0.
        assert "You paid: Rs. 0" in msg

    def test_contains_approaching_warning(self, msg):
        # Priya at 110/115 → Level 0 RED approaching fires.
        assert "Approaching Entitlement" in msg or "approaching" in msg.lower()

    def test_only_one_cliff_header(self, msg):
        """The composer should pick ONE highest-precedence warning header,
        not stack all four. Count how many warning headers appear."""
        headers = [
            "⚠️ Eligibility Cliff Warning",
            "🚨 Monthly Hard Cliff Warning",
            "⚠️ Entitlement Crossed",
            "⚠️ Approaching Entitlement",
        ]
        count = sum(1 for h in headers if h in msg)
        assert count == 1, f"expected exactly one cliff header, got {count}"

    def test_mentions_three_cliffs_in_explanation(self, msg):
        # The pitch line that explains the cliff system.
        assert "three cliffs" in msg or "three" in msg.lower()

    def test_solar_not_recommended_note_present(self, msg):
        assert "close to Rs. 0" in msg or "not_recommended" in msg or "longer" in msg.lower()


# =============================================================================
# Dispatcher — compose_for_result picks right template
# =============================================================================


class TestDispatcher:
    def test_non_gj_dispatch(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_for_result(r)
        assert "Fixed Charge Alert" in msg

    def test_gj_dispatch(self):
        r = analyze_bill(_persona_extraction(PRIYA))
        msg = compose_for_result(r)
        assert "Gruha Jyothi Benefit" in msg


class TestLanguageWrapper:
    """Round-2 localization: intro + footer differ by language; body stays
    English (KERC numbers + program names don't translate)."""

    def test_default_language_is_english_intro_and_footer(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_for_result(r)
        assert msg.startswith("Here's your bill analysis:")
        assert msg.rstrip().endswith(
            "Reply LANG to switch language / STOP to delete data."
        )

    def test_kannada_language_swaps_intro_and_footer(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_for_result(r, language="kn")
        assert msg.startswith("ನಿಮ್ಮ ಬಿಲ್ ವಿಶ್ಲೇಷಣೆ:")
        assert msg.rstrip().endswith("ಭಾಷೆ ಬದಲಾಯಿಸಲು LANG ಕಳುಹಿಸಿ / ಡೇಟಾ ಅಳಿಸಲು STOP.")

    def test_body_stays_english_in_kannada_mode(self):
        # KERC tariff lines must stay readable regardless of language pref.
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_for_result(r, language="kn")
        assert "Fixed Charge Alert" in msg
        assert "PM Surya Ghar" in msg

    def test_unknown_language_falls_back_to_english(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_for_result(r, language="zz")
        assert msg.startswith("Here's your bill analysis:")


# =============================================================================
# Error templates
# =============================================================================


class TestClimateSectionsInMainResponse:
    """Session 5.8 — every persona response includes Climate Footprint +
    Conservation Tip + a solar-scale line in the Solar ROI section."""

    def test_nikhil_response_has_climate_footprint(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_non_gj_response(r)
        assert "Climate Footprint" in msg
        # 2520 kWh/yr projected, annual CO2 ~1,789 kg.
        assert "2,520" in msg
        assert "1,789" in msg

    def test_nikhil_response_has_conservation_tip(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_non_gj_response(r)
        assert "Conservation tip:" in msg
        # 210 units → 200-350 band (AC/water heater).
        assert "AC" in msg or "thermostat" in msg.lower()

    def test_nikhil_solar_section_has_14500_cars_scale_line(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_non_gj_response(r)
        assert "Climate Impact of This Install" in msg
        # 3 kW → ~14,651 cars; we accept the rounded figure nearby.
        assert "cars off" in msg.lower()
        assert "14,6" in msg or "14,5" in msg

    def test_sunita_response_has_ac_band_tip(self):
        r = analyze_bill(_persona_extraction(SUNITA))
        msg = compose_non_gj_response(r)
        assert "Conservation tip:" in msg
        # 280 units → AC/water-heater band.
        assert "AC" in msg or "thermostat" in msg.lower()

    def test_priya_gj_response_has_climate_footprint(self):
        r = analyze_bill(_persona_extraction(PRIYA))
        msg = compose_gj_response(r)
        assert "Climate Footprint" in msg
        # 110 units → 100-200 band (Fans/lighting/TV).
        assert "Fans" in msg or "BLDC" in msg

    def test_priya_at_110_units_no_cliff_in_tip(self):
        # Priya's 110 units is well below the 160-unit threshold for the
        # appended cliff warning. Confirm the warning is absent.
        r = analyze_bill(_persona_extraction(PRIYA))
        msg = compose_gj_response(r)
        # The CLIFF section header already appears separately for Priya's
        # Level 0 approaching warning; check the tip text itself doesn't
        # add the "Approaching 200-unit" line.
        tip_section = msg.split("Conservation tip:")[1].split("━━")[0]
        assert "200-unit Gruha Jyothi cliff" not in tip_section



    def test_pre_april_2025(self):
        msg = compose_pre_april_2025_response()
        assert "before April 2025" in msg
        assert "KERC" in msg

    def test_bad_photo(self):
        msg = compose_bad_photo_response()
        assert "couldn't read" in msg.lower() or "MESCOM bill" in msg

    def test_gemini_error(self):
        msg = compose_gemini_error_response()
        assert "try again" in msg.lower()


# =============================================================================
# WhatsApp 1600-char cap helper
# =============================================================================


class TestSplit:
    def test_short_message_not_split(self):
        assert split_for_whatsapp("hello") == ["hello"]

    def test_long_message_split_into_chunks(self):
        msg = "\n".join(f"line {i}" for i in range(400))
        chunks = split_for_whatsapp(msg, limit=1600)
        assert len(chunks) > 1
        assert all(len(c) <= 1600 for c in chunks)
