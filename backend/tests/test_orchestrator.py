"""Smoke tests for analysis.orchestrator.analyze_bill.

Five personas: Nikhil, Sunita, Priya, KOPPALA (hard cliff), REHENA (soft
step). Each exercises a different product branch.
"""
from __future__ import annotations

import pytest

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.config.personas import NIKHIL, PRIYA, SUNITA

pytestmark = pytest.mark.smoke


# =============================================================================
# Helpers
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


def _koppala_extraction() -> BillExtraction:
    """390-unit GJ hard-cliff bill from demo_fallbacks.json (synthetic)."""
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2026-04-10",
        billing_period_days=31,
        sanctioned_load_kw=2.0,
        units_consumed=390,
        subtotal_1_before_subsidy=3044.18,
        net_bill_amount=3044.18,        # crossed 200 → full bill owed
        is_gruha_jyothi_beneficiary=True,
        historical_avg_baseline=57.0,
        entitlement_units=63.0,
        gruha_jyothi_subsidy_amount=0.0,
        gjs_registration_date="2023-07-25",
    )


def _rehena_extraction() -> BillExtraction:
    """170-unit GJ bill from demo_fallbacks.json (real Session 2 extraction)."""
    return BillExtraction(
        is_mescom_bill=True,
        tariff_category="LT-1",
        billing_period_end="2025-12-06",
        billing_period_days=30,
        sanctioned_load_kw=1.0,
        units_consumed=170,
        subtotal_1_before_subsidy=1343.84,
        net_bill_amount=331.44,
        is_gruha_jyothi_beneficiary=True,
        historical_avg_baseline=111.0,
        entitlement_units=123.0,
        gruha_jyothi_subsidy_amount=1012.4,
        gjs_registration_date="2023-06-22",
    )


# =============================================================================
# Nikhil — Fixed Charge Trap + PMSG + 45-month payback hero
# =============================================================================


class TestNikhil:
    @pytest.fixture
    def r(self):
        return analyze_bill(_extraction_for(NIKHIL))

    def test_subtotal_matches_briefing(self, r):
        assert r.computed_bill.subtotal_1 == pytest.approx(1943.22, abs=0.01)

    def test_net_bill_equals_subtotal_for_non_gj(self, r):
        assert r.net_bill_amount == pytest.approx(1943.22, abs=0.01)

    def test_fct_fires(self, r):
        assert r.fct.fires is True

    def test_fct_annual_cost_is_1_740(self, r):
        # Briefing's load-bearing pitch number.
        assert r.fct.excess_annual_cost == pytest.approx(1_740, abs=1)

    def test_fct_excess_is_1_kw(self, r):
        assert r.fct.excess_kw == pytest.approx(1.0, abs=0.01)

    def test_pmsg_eligible(self, r):
        assert r.pm_surya_ghar["eligible"] is True

    def test_solar_payback_is_45(self, r):
        assert r.solar_roi.payback_months == 45

    def test_chosen_template_is_non_gj(self, r):
        assert r.chosen_template == "non_gj"

    def test_gj_visibility_none(self, r):
        assert r.gj_visibility is None


# =============================================================================
# Sunita — solar hero, faster payback
# =============================================================================


class TestSunita:
    @pytest.fixture
    def r(self):
        return analyze_bill(_extraction_for(SUNITA))

    def test_fct_fires(self, r):
        # Rule 3 table: Sunita's FCT also fires (1 kW excess at floor).
        assert r.fct.fires is True

    def test_solar_payback_in_briefing_range(self, r):
        # Reconciliation research: 38.5 months.
        assert 38 <= r.solar_roi.payback_months <= 39

    def test_monthly_benefit_is_about_2260(self, r):
        assert r.solar_roi.total_monthly_benefit == pytest.approx(2_260, abs=5)

    def test_chosen_template_is_non_gj(self, r):
        assert r.chosen_template == "non_gj"


# =============================================================================
# Priya — GJ Level 0 approaching RED, solar not recommended
# =============================================================================


class TestPriya:
    @pytest.fixture
    def r(self):
        return analyze_bill(_extraction_for(PRIYA))

    def test_chosen_template_is_gj(self, r):
        assert r.chosen_template == "gj"

    def test_fct_does_not_fire(self, r):
        assert r.fct.fires is False

    def test_net_bill_is_zero(self, r):
        assert r.net_bill_amount == pytest.approx(0.0, abs=0.01)

    def test_gj_visibility_populated(self, r):
        assert r.gj_visibility is not None
        assert r.gj_visibility.entitlement_units == 115.0

    def test_approaching_red_warning_present(self, r):
        warnings = r.gj_visibility.warnings
        approaching = [w for w in warnings if w.cliff == "approaching_entitlement"]
        assert approaching, "Level 0 approaching warning expected"
        assert approaching[0].level == "red"

    def test_solar_not_recommended(self, r):
        assert r.solar_roi.recommendation == "not_recommended"


# =============================================================================
# KOPPALA — crossed 200 units, Level 2 hard cliff
# =============================================================================


class TestKoppala:
    @pytest.fixture
    def r(self):
        return analyze_bill(_koppala_extraction())

    def test_chosen_template_is_gj(self, r):
        assert r.chosen_template == "gj"

    def test_monthly_hard_cliff_red_fires(self, r):
        warnings = r.gj_visibility.warnings
        monthly_hard = [w for w in warnings if w.cliff == "monthly_hard"]
        assert monthly_hard, "Level 2 hard-cliff expected for 390 units"
        assert monthly_hard[0].level == "red"

    def test_overall_risk_is_red(self, r):
        assert r.gj_visibility.overall_risk == "red"

    def test_soft_step_does_not_fire_once_over_200(self, r):
        # Level 1 only applies between entitlement and 200 units; 390 > 200.
        assert not any(
            w.cliff == "soft_step" for w in r.gj_visibility.warnings
        )


# =============================================================================
# REHENA — between entitlement and 200, Level 1 soft step + Level 2 YELLOW
# =============================================================================


class TestRehena:
    @pytest.fixture
    def r(self):
        return analyze_bill(_rehena_extraction())

    def test_chosen_template_is_gj(self, r):
        assert r.chosen_template == "gj"

    def test_soft_step_fires(self, r):
        warnings = r.gj_visibility.warnings
        assert any(w.cliff == "soft_step" for w in warnings)

    def test_monthly_hard_yellow_fires(self, r):
        # 170/200 = 85% → YELLOW (>=0.80).
        warnings = r.gj_visibility.warnings
        monthly_hard = [w for w in warnings if w.cliff == "monthly_hard"]
        assert monthly_hard and monthly_hard[0].level == "yellow"

    def test_approaching_warning_also_fires(self, r):
        # 170/123 = 138% → approaching RED (no suppression when soft_step fires).
        warnings = r.gj_visibility.warnings
        assert any(w.cliff == "approaching_entitlement" for w in warnings)


# =============================================================================
# JSONB serialisation — write_bill accepts analysis.to_jsonable() without
# tripping the DPDPA forbidden-field guards.
# =============================================================================


def test_to_jsonable_has_no_forbidden_keys():
    from backend.db.supabase_client import _FORBIDDEN_FIELDS
    r = analyze_bill(_extraction_for(NIKHIL))
    blob = r.to_jsonable()
    flat_keys = set(blob.keys())
    assert not (flat_keys & _FORBIDDEN_FIELDS), (
        f"analysis blob contains forbidden keys: {flat_keys & _FORBIDDEN_FIELDS}"
    )
