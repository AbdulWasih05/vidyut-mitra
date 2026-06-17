"""Smoke tests for analysis.load_inference (Session 5.8 Commit 3)."""
from __future__ import annotations

from datetime import date

import pytest

from backend.analysis.load_inference import DominantLoadResult, infer_dominant_load
from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA, SUNITA
from backend.output.response_composer import compose_gj_response, compose_non_gj_response

pytestmark = pytest.mark.smoke


# =============================================================================
# Rule matching — persona cases
# =============================================================================


APRIL_2026 = date(2026, 4, 15)
JANUARY_2026 = date(2026, 1, 15)


class TestPersonaRules:
    def test_nikhil_april_ac_cooling_high(self):
        r = infer_dominant_load(3.0, 210, APRIL_2026)
        assert r.dominant_load == "ac_cooling"
        assert r.confidence == "high"
        assert "AC" in r.reasoning or "cooling" in r.reasoning.lower()
        assert "April" in r.reasoning

    def test_priya_april_fans_lighting_high(self):
        r = infer_dominant_load(2.0, 110, APRIL_2026)
        assert r.dominant_load == "fans_lighting"
        assert r.confidence == "high"
        assert "fans" in r.reasoning.lower() or "lighting" in r.reasoning.lower()

    def test_sunita_april_ac_cooling_high(self):
        r = infer_dominant_load(3.0, 280, APRIL_2026)
        assert r.dominant_load == "ac_cooling"
        assert r.confidence == "high"

    def test_koppala_april_ac_cooling_high(self):
        # 2 kW sanctioned, 390 units — even with modest sanctioned load,
        # the summer + heavy consumption signal dominates.
        r = infer_dominant_load(2.0, 390, APRIL_2026)
        assert r.dominant_load == "ac_cooling"
        assert r.confidence == "high"

    def test_150_units_january_15kw_water_heating(self):
        r = infer_dominant_load(1.5, 150, JANUARY_2026)
        assert r.dominant_load == "water_heating"
        assert r.confidence == "medium"
        assert "geyser" in r.conservation_action.lower() or "water heater" in r.conservation_action.lower()

    def test_refrigeration_fallback(self):
        # Moderate load + consumption, October (no season match).
        r = infer_dominant_load(3.0, 200, date(2026, 10, 15))
        assert r.dominant_load == "refrigeration"
        assert r.confidence == "medium"

    def test_mixed_fallback_for_weird_inputs(self):
        # 2 kW, 170 units, October — not in fans/lighting band (>150),
        # not refrigeration (load exactly 2 OK, units 170 >= 150),
        # actually refrigeration rule matches. Try different numbers that
        # genuinely don't match any rule.
        r = infer_dominant_load(1.5, 170, date(2026, 10, 15))
        assert r.dominant_load == "mixed"
        assert r.confidence == "low"


# =============================================================================
# Conservation action quantification — Nikhil and Sunita
# =============================================================================


class TestConservationActions:
    def test_nikhil_savings_rupees_positive(self):
        r = infer_dominant_load(3.0, 210, APRIL_2026)
        # 30% of AC (50% of bill) × 210 × 5.80 = 0.15 × 210 × 5.80 = 182.7
        assert r.monthly_savings_rupees_estimate == pytest.approx(183, abs=2)

    def test_nikhil_co2_avoided_positive(self):
        r = infer_dominant_load(3.0, 210, APRIL_2026)
        # 183 / 5.80 × 0.710 ≈ 22.4 kg
        assert r.monthly_co2_avoided_kg_estimate == pytest.approx(22.4, abs=0.5)

    def test_winter_water_heater_savings(self):
        # 150 units × 0.25 × 5.80 = 217.5
        r = infer_dominant_load(1.5, 150, JANUARY_2026)
        assert r.monthly_savings_rupees_estimate == pytest.approx(218, abs=2)


# =============================================================================
# Response composer integration
# =============================================================================


def _persona_extraction(persona) -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-04-15",   # summer month for AC matches
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


class TestComposerIntegration:
    def test_non_gj_nikhil_contains_ac_thermostat_nudge(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_non_gj_response(r)
        assert "Dominant Load" in msg
        assert "AI inference" in msg
        assert "thermostat" in msg.lower()
        assert "24°C" in msg

    def test_non_gj_nikhil_shows_rupee_savings(self):
        r = analyze_bill(_persona_extraction(NIKHIL))
        msg = compose_non_gj_response(r)
        assert "Estimated monthly savings: Rs." in msg
        # Nikhil's savings ≈ Rs. 183. Allow the composer's ,.0f formatting.
        assert "183" in msg

    def test_gj_priya_contains_fans_lighting_nudge(self):
        r = analyze_bill(_persona_extraction(PRIYA))
        msg = compose_gj_response(r)
        assert "Dominant Load" in msg
        assert "fans" in msg.lower() or "BLDC" in msg or "LED" in msg
        assert "Confidence: high" in msg

    def test_non_gj_sunita_contains_ac_nudge(self):
        r = analyze_bill(_persona_extraction(SUNITA))
        msg = compose_non_gj_response(r)
        assert "AC" in msg
        assert "thermostat" in msg.lower()
