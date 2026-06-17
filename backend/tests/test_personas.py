"""End-to-end persona assertions (Nikhil, Sunita, Priya) + synthetic bills.

Covers the three demo choreography moments:
- Nikhil: solar ROI hero math — 45-month payback, Rs. 4.31 lakh lifetime,
  2.98 tonnes CO2/year (briefing §4 worked example, byte-for-byte).
- Sunita: higher consumption → faster payback, ~Rs. 2,260 monthly benefit.
- Priya: GJ Visibility — Level 0 approaching RED fires at 110/115, solar
  is "not_recommended" because she's under entitlement.

Plus synthetic edge-case bills seen in the wild:
- KOPPALA-class: 390 units / 63 entitlement → Level 2 monthly hard cliff RED.
- REHENA-class: 170 units / 123 entitlement → Level 1 soft step + Level 0
  approaching warning both present.
"""
from __future__ import annotations

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.solar_roi import compute_roi, size_system
from backend.analysis.subsidy_navigator import (
    check_pm_surya_ghar,
    compute_gj_visibility,
    compute_gj_warnings,
)
from backend.config.personas import ALL_PERSONAS, NIKHIL, PRIYA, SUNITA


# All tests in this file are smoke-marked by default.
pytestmark = pytest.mark.smoke


# =============================================================================
# Helper constructors
# =============================================================================


def _persona_to_extraction(persona) -> BillExtraction:
    """Build a BillExtraction dict from a Persona for passing into analysis."""
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-03-15",
        billing_period_days=persona.billing_period_days,
        sanctioned_load_kw=persona.sanctioned_load_kw,
        units_consumed=persona.units_consumed,
        subtotal_1_before_subsidy=persona.expected_subtotal_1,
        is_gruha_jyothi_beneficiary=persona.is_gj_beneficiary,
        historical_avg_baseline=persona.gj_historical_avg_units,
        entitlement_units=persona.gj_entitlement_units,
        gruha_jyothi_subsidy_amount=(
            persona.expected_subtotal_1 if persona.is_gj_beneficiary else None
        ),
        net_bill_amount=persona.expected_net_bill,
        gjs_registration_date="2023-08-26" if persona.is_gj_beneficiary else None,
    )


# --- Thin helpers for the tariff-engine-dependent suite ------

def _compute_tariff(persona):
    from backend.analysis.tariff_engine import apply_gj_subsidy, compute_bill

    bill = compute_bill(
        units_consumed=persona.units_consumed,
        sanctioned_load_kw=persona.sanctioned_load_kw,
    )
    net_bill = apply_gj_subsidy(
        subtotal_1=bill.subtotal_1,
        units_consumed=persona.units_consumed,
        entitlement_units=persona.gj_entitlement_units or 0,
    ) if persona.is_gj_beneficiary else bill.subtotal_1

    return {
        "subtotal_1": bill.subtotal_1,
        "net_bill": net_bill,
    }


def _compute_fct(persona):
    from backend.analysis.tariff_engine import estimate_peak_demand

    estimated_peak = estimate_peak_demand(persona.units_consumed)
    # Persona flow uses a practical floor of 2 kW for domestic recommendations.
    recommended_kw = max(2.0, round(estimated_peak))
    excess_kw = round(max(0.0, persona.sanctioned_load_kw - recommended_kw), 2)
    fires = excess_kw >= 1.0
    annual_overpayment = round(excess_kw * 145 * 12, 2)
    return {
        "fires": fires,
        "excess_kw": excess_kw,
        "excess_annual_cost": annual_overpayment,
    }


# =============================================================================
# Subtotal-1 and net-bill
# =============================================================================


@pytest.mark.parametrize("persona", ALL_PERSONAS, ids=[p.name for p in ALL_PERSONAS])
def test_subtotal_1_matches_briefing(persona):
    result = _compute_tariff(persona)
    assert result["subtotal_1"] == pytest.approx(persona.expected_subtotal_1, abs=0.01)


@pytest.mark.parametrize("persona", ALL_PERSONAS, ids=[p.name for p in ALL_PERSONAS])
def test_net_bill_matches_briefing(persona):
    result = _compute_tariff(persona)
    assert result["net_bill"] == pytest.approx(persona.expected_net_bill, abs=0.01)


def test_priya_net_bill_is_exactly_zero():
    result = _compute_tariff(PRIYA)
    assert result["net_bill"] == pytest.approx(0.00, abs=0.01)


# =============================================================================
# Fixed Charge Trap
# =============================================================================


def test_nikhil_fct_fires():
    fct = _compute_fct(NIKHIL)
    assert fct["fires"] is True
    assert fct["excess_annual_cost"] == pytest.approx(1_740, abs=1)


def test_sunita_fct_fires():
    fct = _compute_fct(SUNITA)
    assert fct["fires"] is True


def test_priya_fct_does_not_fire():
    fct = _compute_fct(PRIYA)
    assert fct["fires"] is False


# =============================================================================
# Gruha Jyothi Visibility (Session 3 — UNSKIPPED)
# =============================================================================


class TestPriyaGJVisibility:
    """Priya at 110/115 = 95.7% — the demo moment for Level 0 approaching."""

    @pytest.fixture
    def gj_report(self):
        return compute_gj_visibility(_persona_to_extraction(PRIYA))

    def test_entitlement_is_115_not_200(self):
        """Guard against the tech-spec copy-paste error flagged in Rule 1."""
        assert PRIYA.gj_entitlement_units == 115.0
        assert PRIYA.gj_entitlement_units != 200.0

    def test_is_gj_beneficiary(self, gj_report):
        assert gj_report.is_gj_beneficiary is True

    def test_utilization_is_about_95_percent(self, gj_report):
        assert gj_report.entitlement_utilization_pct == pytest.approx(95.65, abs=0.2)

    def test_monthly_hard_cliff_does_not_fire(self, gj_report):
        # 110 / 200 = 55 %, well below the 80 % Level 2 threshold.
        assert gj_report.cliffs["monthly_hard"]["triggered"] is False

    def test_fires_red_approaching_entitlement_warning(self, gj_report):
        """Level 0 is load-bearing — without it, Priya fires nothing."""
        assert gj_report.overall_risk == "red"
        approaching = [
            w for w in gj_report.warnings if w.cliff == "approaching_entitlement"
        ]
        assert approaching, "expected an approaching_entitlement warning"
        assert approaching[0].level == "red", (
            f"Priya's 110/115 = 95.7% should be RED (>= 90%), "
            f"got {approaching[0].level}"
        )


class TestNonGJPersonasHaveNoGJOutput:
    @pytest.mark.parametrize("persona", [NIKHIL, SUNITA], ids=["Nikhil", "Sunita"])
    def test_not_a_gj_beneficiary(self, persona):
        gj = compute_gj_visibility(_persona_to_extraction(persona))
        assert gj.is_gj_beneficiary is False
        assert gj.warnings == []
        assert gj.overall_risk == "green"


# =============================================================================
# Synthetic edge-case bills — KOPPALA + REHENA classes
# =============================================================================


class TestKoppalaClassHardCliff:
    """390 units / 63 entitlement / 0 subsidised units — crossed the 200-unit
    cliff. Level 2 monthly hard cliff RED warning must fire; eligibility and
    approaching warnings likely fire too (depending on trailing average).
    """

    def test_monthly_hard_cliff_red_warning_present(self):
        warnings = compute_gj_warnings(
            units_consumed=390,
            entitlement_units=63,
            trailing_10m_avg=None,
            hypothetical_full_bill=2_800.0,
        )
        monthly_hard = [w for w in warnings if w.cliff == "monthly_hard"]
        assert monthly_hard, "Level 2 hard-cliff warning expected for 390 units"
        assert monthly_hard[0].level == "red", (
            f"390 / 200 = 195% should be RED (>= 95%), got {monthly_hard[0].level}"
        )

    def test_soft_step_does_not_fire_once_over_200(self):
        # Level 1 soft step only applies between entitlement and 200 units.
        warnings = compute_gj_warnings(
            units_consumed=390,
            entitlement_units=63,
            trailing_10m_avg=None,
            hypothetical_full_bill=2_800.0,
        )
        assert not any(w.cliff == "soft_step" for w in warnings)


class TestRehenaClassSoftStep:
    """170 units / 123 entitlement — crossed personal entitlement but still
    under the 200-unit hard cliff. Level 1 soft step fires; approaching
    warning fires too (presence, not colour, is what matters).
    """

    def test_soft_step_warning_present(self):
        warnings = compute_gj_warnings(
            units_consumed=170,
            entitlement_units=123,
            trailing_10m_avg=None,
            hypothetical_full_bill=1_344.0,
        )
        soft = [w for w in warnings if w.cliff == "soft_step"]
        assert soft, "Level 1 soft step expected when units > entitlement but <= 200"

    def test_approaching_warning_present(self):
        warnings = compute_gj_warnings(
            units_consumed=170,
            entitlement_units=123,
            trailing_10m_avg=None,
            hypothetical_full_bill=1_344.0,
        )
        # 170 / 123 = 138 % — well above the 90 % Level 0 threshold, so
        # approaching fires. Colour is RED under pure threshold math; we
        # check presence to stay robust to a future "downgrade once over"
        # product tweak.
        approaching = [w for w in warnings if w.cliff == "approaching_entitlement"]
        assert approaching, "Level 0 approaching warning expected"

    def test_monthly_hard_yellow_fires_at_85_percent(self):
        warnings = compute_gj_warnings(
            units_consumed=170,
            entitlement_units=123,
            trailing_10m_avg=None,
            hypothetical_full_bill=1_344.0,
        )
        monthly_hard = [w for w in warnings if w.cliff == "monthly_hard"]
        assert monthly_hard
        assert monthly_hard[0].level == "yellow", (
            f"170/200 = 85% should be YELLOW, got {monthly_hard[0].level}"
        )


# =============================================================================
# Solar ROI — Nikhil hero math (briefing §4)
# =============================================================================


class TestNikhilSolarROI:
    """Briefing §4 worked example is the oracle — every number here is
    defensible at pitch time."""

    @pytest.fixture
    def roi(self):
        return compute_roi(
            system_kw=3, monthly_consumption=210, is_gj_beneficiary=False
        )

    def test_recommended(self, roi):
        assert roi.recommendation == "recommended"

    def test_system_cost_is_rs_1_65_lakh(self, roi):
        assert roi.system_cost == 165_000

    def test_pmsg_subsidy_is_rs_78_000(self, roi):
        assert roi.pmsg_subsidy == 78_000

    def test_net_cost_is_rs_87_000(self, roi):
        assert roi.net_cost == 87_000

    def test_annual_generation_is_4200(self, roi):
        assert roi.annual_generation_kwh == 4_200

    def test_monthly_benefit_is_1930_42(self, roi):
        assert roi.total_monthly_benefit == pytest.approx(1930.42, abs=0.01)

    def test_payback_is_45_months_38_years(self, roi):
        assert roi.payback_months == 45
        assert roi.payback_years == pytest.approx(3.8, abs=0.05)

    def test_lifetime_net_savings_flat_is_about_4_31_lakh(self, roi):
        # Briefing: Rs. 4,31,126. Tight tolerance catches regressions.
        assert roi.lifetime_net_savings_flat == pytest.approx(431_126, abs=1_000)

    def test_lifetime_net_savings_3pct_is_about_6_9_lakh(self, roi):
        # Briefing: Rs. 6.9 lakh realistic upside with 3% escalation.
        assert roi.lifetime_net_savings_3pct == pytest.approx(696_000, abs=10_000)

    def test_co2_offset_is_2_98_tonnes(self, roi):
        # 4,200 × 0.710 / 1000 = 2.982 → briefing says 2.98.
        assert roi.co2_offset_tonnes_per_year == pytest.approx(2.98, abs=0.05)

    def test_trees_equivalent_is_about_100(self, roi):
        # 2,982 / 30 = 99.4. Briefing says ~100.
        assert 95 <= roi.trees_equivalent <= 105


# =============================================================================
# Solar ROI — Sunita (higher consumption → faster payback)
# =============================================================================


class TestSunitaSolarROI:
    @pytest.fixture
    def roi(self):
        return compute_roi(
            system_kw=3, monthly_consumption=280, is_gj_beneficiary=False
        )

    def test_recommended(self, roi):
        assert roi.recommendation == "recommended"

    def test_monthly_benefit_is_about_2260(self, roi):
        # Reconciliation research: 2010.96 + 173.60 + 75.00 = 2259.56 ≈ 2260.
        assert roi.total_monthly_benefit == pytest.approx(2_260, abs=5)

    def test_payback_is_about_38_39_months(self, roi):
        # 87,000 / 2,259.56 = 38.5 — rounds to 38 or 39 depending on method.
        assert 38 <= roi.payback_months <= 39

    def test_payback_years_is_about_3_2(self, roi):
        assert roi.payback_years == pytest.approx(3.2, abs=0.1)

    def test_lifetime_flat_is_about_5_3_lakh(self, roi):
        # Reconciliation research: ~Rs. 5.3 lakh at flat tariffs.
        assert roi.lifetime_net_savings_flat == pytest.approx(530_000, abs=10_000)


# =============================================================================
# Solar ROI — Priya (GJ under entitlement → not recommended)
# =============================================================================


class TestPriyaSolarROI:
    """Priya's grid is effectively free; solar displaces nothing she pays for."""

    @pytest.fixture
    def roi(self):
        return compute_roi(
            system_kw=2,
            monthly_consumption=110,
            is_gj_beneficiary=True,
            entitlement_units=115,
        )

    def test_not_recommended(self, roi):
        assert roi.recommendation == "not_recommended"

    def test_reason_mentions_entitlement(self, roi):
        assert "Gruha Jyothi" in roi.recommendation_reason


# =============================================================================
# PM Surya Ghar eligibility — spot checks
# =============================================================================


class TestPMSuryaGhar:
    def test_nikhil_eligible(self):
        r = check_pm_surya_ghar(
            sanctioned_load_kw=NIKHIL.sanctioned_load_kw,
            is_gj_beneficiary=False,
            units_consumed=NIKHIL.units_consumed,
        )
        assert r["eligible"] is True
        assert r["subsidy_amount"] == 78_000

    def test_priya_eligible_but_gj_flagged(self):
        r = check_pm_surya_ghar(
            sanctioned_load_kw=PRIYA.sanctioned_load_kw,
            is_gj_beneficiary=True,
            units_consumed=PRIYA.units_consumed,
        )
        assert r["eligible"] is True
        assert "Gruha Jyothi" in r["reason"]


# =============================================================================
# System sizing — briefing §4 and tech-spec §8.2 worked examples
# =============================================================================


class TestSizeSystem:
    def test_nikhil_sizes_to_3_when_sanctioned_hint_passed(self):
        # Tech spec §8.2: raw formula → 2, but sanctioned-load hint bumps to 3.
        kw = size_system(
            annual_consumption_kwh=210 * 12,
            sanctioned_load_kw=3.0,
        )
        assert kw == 3

    def test_sunita_sizes_to_3(self):
        kw = size_system(annual_consumption_kwh=280 * 12)
        assert kw == 3

    def test_zero_consumption_returns_0(self):
        assert size_system(0) == 0

    def test_caps_at_3(self):
        # Very high consumption — cap is the subsidy ceiling.
        assert size_system(10_000 * 12) == 3
