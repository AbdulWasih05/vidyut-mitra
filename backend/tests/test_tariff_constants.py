"""Smoke tests for verified KERC / MNRE / CEA / GoK constants.

Every value here is load-bearing for the pitch. A change that breaks one of
these assertions is almost always a regression, not an improvement — flag to
Wasih before editing ``config/tariff_constants.py`` to match.

Run: ``pytest -v -m smoke``.
"""
from __future__ import annotations

import pytest

from backend.config import tariff_constants as tc


pytestmark = pytest.mark.smoke


# =============================================================================
# KERC LT-1 Domestic tariff (briefing §3, KERC Order 27-Mar-2025 Annexure 2)
# =============================================================================


class TestKERCTariff:
    def test_current_fy_is_2025_26(self):
        assert tc.CURRENT_FY == "2025-26"

    def test_energy_charge_is_flat_rs_5_80(self):
        assert tc.ENERGY_CHARGE_FLAT_RATE == 5.80

    def test_energy_charge_schedule_matches_briefing(self):
        # Briefing §3 wins over tech-spec on FY 2026-27 (5.90 vs 5.80).
        assert tc.ENERGY_CHARGE_PER_UNIT["2025-26"] == 5.80
        assert tc.ENERGY_CHARGE_PER_UNIT["2026-27"] == 5.90
        assert tc.ENERGY_CHARGE_PER_UNIT["2027-28"] == 5.75

    def test_fixed_charge_is_rs_145_for_current_fy(self):
        assert tc.FIXED_CHARGE_PER_KW_CURRENT == 145

    def test_fixed_charge_forward_schedule(self):
        assert tc.FIXED_CHARGE_PER_KW["2025-26"] == 145
        assert tc.FIXED_CHARGE_PER_KW["2026-27"] == 150
        assert tc.FIXED_CHARGE_PER_KW["2027-28"] == 160

    def test_electricity_tax_is_9_percent(self):
        assert tc.ELECTRICITY_TAX_RATE == pytest.approx(0.09)

    def test_pg_surcharge_is_rs_0_36_per_unit(self):
        assert tc.PG_SURCHARGE_PER_UNIT == pytest.approx(0.36)

    def test_fppca_placeholder_is_rs_0_50_per_unit(self):
        assert tc.FPPCA_PLACEHOLDER_RATE == pytest.approx(0.50)

    def test_solar_rooftop_rebate(self):
        assert tc.SOLAR_ROOFTOP_REBATE_PER_KW == 25
        assert tc.SOLAR_ROOFTOP_REBATE_CAP_KW == 10

    def test_tariff_code_is_lt_1_not_lt_2a(self):
        # Rule 1 explicitly forbids `LT-2(a)`.
        assert tc.DOMESTIC_TARIFF_CODE == "LT-1"


# =============================================================================
# Solar export rates (KERC Solar Tariff Order, effective 01-Jul-2025)
# =============================================================================


class TestSolarExportRates:
    def test_2_3_kw_export_is_rs_2_48(self):
        # The rate that applies to Nikhil and Sunita.
        assert tc.SOLAR_EXPORT_RATE_2_3_KW == pytest.approx(2.48)

    def test_1_2_kw_export_is_rs_2_30(self):
        assert tc.SOLAR_EXPORT_RATE_1_2_KW == pytest.approx(2.30)

    def test_above_3_kw_export_is_rs_2_93(self):
        assert tc.SOLAR_EXPORT_RATE_ABOVE_3_KW == pytest.approx(2.93)

    def test_non_subsidised_export_is_rs_3_86(self):
        assert tc.SOLAR_EXPORT_RATE_NONSUB_1_10_KW == pytest.approx(3.86)


# =============================================================================
# PM Surya Ghar subsidy (MNRE)
# =============================================================================


class TestPMSGSubsidy:
    def test_first_2_kw_rate_is_rs_30_000(self):
        assert tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW == 30_000

    def test_third_kw_rate_is_rs_18_000(self):
        assert tc.PMSG_SUBSIDY_3RD_KW == 18_000

    def test_total_cap_is_rs_78_000(self):
        assert tc.PMSG_SUBSIDY_CAP == 78_000

    def test_3_kw_subsidy_composition(self):
        # 2 × 30,000 + 1 × 18,000 = 78,000 — briefing §3 matches cap.
        three_kw = 2 * tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW + tc.PMSG_SUBSIDY_3RD_KW
        assert three_kw == tc.PMSG_SUBSIDY_CAP == 78_000


# =============================================================================
# Solar ROI — Mangalore constants
# =============================================================================


class TestSolarROI:
    def test_specific_yield_is_1400_kwh_per_kwp_year(self):
        assert tc.SPECIFIC_YIELD_KWP_YEAR == 1_400

    def test_annual_generation_3kw_is_4200_kwh(self):
        assert tc.ANNUAL_GENERATION_3KW == 4_200

    def test_system_cost_is_rs_55_000_per_kw(self):
        assert tc.SYSTEM_COST_PER_KW == 55_000

    def test_3kw_net_cost_after_pmsg_is_rs_87_000(self):
        assert tc.NET_COST_3KW_AFTER_PMSG == 87_000


# =============================================================================
# Environmental — emission factor and derived figures
# Critical: CEA v21.0 value, NOT v20.0's 0.727 or the pre-2024 ~0.82.
# =============================================================================


class TestEnvironmental:
    def test_emission_factor_is_cea_v21_value(self):
        assert tc.GRID_EMISSION_FACTOR_KG_PER_KWH == pytest.approx(0.710)

    def test_emission_factor_is_not_0_82(self):
        # Pre-2024 value. Older PRD drafts used this.
        assert tc.GRID_EMISSION_FACTOR_KG_PER_KWH != pytest.approx(0.82)
        assert tc.GRID_EMISSION_FACTOR_KG_PER_KWH < 0.80

    def test_emission_factor_is_not_cea_v20_value(self):
        # CEA v20.0 (Dec 2024) value, superseded by v21.0 (Dec 2025).
        assert tc.GRID_EMISSION_FACTOR_KG_PER_KWH != pytest.approx(0.727)

    def test_annual_co2_offset_3kw_is_about_2_98_tonnes(self):
        # 4,200 × 0.710 / 1,000 = 2.982 → 2.98 in pitch.
        assert tc.ANNUAL_CO2_OFFSET_3KW_TONNES == pytest.approx(2.982, abs=0.005)

    def test_annual_co2_offset_is_not_stale_3_05_figure(self):
        # 3.05 t/yr is the tell for a stale emission factor.
        assert tc.ANNUAL_CO2_OFFSET_3KW_TONNES < 3.0

    def test_tree_absorption_rate(self):
        assert tc.TREE_ABSORPTION_KG_PER_YEAR == 30

    def test_trees_equivalent_3kw_is_about_100(self):
        # 4,200 × 0.710 / 30 = 99.4 → rounds to 99 or ~100 in pitch.
        # NOT 135 (PRD v3's arithmetically inconsistent figure).
        assert tc.TREES_EQUIVALENT_3KW == pytest.approx(99, abs=2)
        assert tc.TREES_EQUIVALENT_3KW < 120


# =============================================================================
# Gruha Jyothi — entitlement formula and cliff warning thresholds
# =============================================================================


class TestGruhaJyothi:
    def test_flat_bonus_is_10_units(self):
        # Karnataka Cabinet 18-Jan-2024 — switched from avg×1.10 to avg+10.
        assert tc.GJ_ENTITLEMENT_FLAT_BONUS_UNITS == 10

    def test_entitlement_cap_is_200_units(self):
        assert tc.GJ_ENTITLEMENT_CAP_UNITS == 200

    def test_monthly_hard_cliff_is_200_units(self):
        assert tc.GJ_MONTHLY_HARD_CLIFF_UNITS == 200

    def test_eligibility_rolling_window_is_10_months(self):
        assert tc.GJ_ELIGIBILITY_ROLLING_MONTHS == 10

    def test_priya_entitlement_via_formula_is_115(self):
        # Rule 1: Priya's entitlement is min(105 + 10, 200) = 115, NOT 200.
        historical_avg = 105
        entitlement = min(
            historical_avg + tc.GJ_ENTITLEMENT_FLAT_BONUS_UNITS,
            tc.GJ_ENTITLEMENT_CAP_UNITS,
        )
        assert entitlement == 115

    # --- Level 0 — approaching entitlement (proactive) ---

    def test_approaching_entitlement_thresholds(self):
        assert tc.GJ_APPROACHING_YELLOW_THRESHOLD == pytest.approx(0.75)
        assert tc.GJ_APPROACHING_RED_THRESHOLD == pytest.approx(0.90)

    def test_level_0_red_fires_for_priya(self):
        # 110/115 = 0.9565 → RED (>= 0.90).
        util = 110 / 115
        assert util >= tc.GJ_APPROACHING_RED_THRESHOLD

    def test_level_0_prevents_dead_demo_moment(self):
        # Without Level 0, Priya fires nothing — confirm Level 0 catches her.
        units, entitlement = 110, 115
        util = units / entitlement
        hard_cap_util = units / tc.GJ_MONTHLY_HARD_CLIFF_UNITS  # 110/200 = 0.55
        eligibility_util = 115 / tc.GJ_MONTHLY_HARD_CLIFF_UNITS  # assume 10m avg ≈ 115

        # Level 2 should NOT fire.
        assert hard_cap_util < tc.GJ_HARD_CAP_YELLOW_THRESHOLD
        # Level 3 should NOT fire.
        assert eligibility_util < tc.GJ_ELIGIBILITY_YELLOW_THRESHOLD
        # Level 0 SHOULD fire red.
        assert util >= tc.GJ_APPROACHING_RED_THRESHOLD

    # --- Level 2 — monthly hard cliff ---

    def test_hard_cap_thresholds(self):
        assert tc.GJ_HARD_CAP_YELLOW_THRESHOLD == pytest.approx(0.80)
        assert tc.GJ_HARD_CAP_RED_THRESHOLD == pytest.approx(0.95)

    # --- Level 3 — eligibility cliff ---

    def test_eligibility_thresholds(self):
        assert tc.GJ_ELIGIBILITY_YELLOW_THRESHOLD == pytest.approx(0.80)
        assert tc.GJ_ELIGIBILITY_RED_THRESHOLD == pytest.approx(0.95)


# =============================================================================
# Fixed Charge Trap detection
# =============================================================================


class TestFixedChargeTrap:
    def test_peak_heuristic_constants(self):
        assert tc.PEAK_DEMAND_ACTIVE_HOURS_PER_DAY == 8
        assert tc.PEAK_TO_AVERAGE_FACTOR == pytest.approx(1.67)

    def test_trap_trigger_constants(self):
        assert tc.FCT_BUFFER_KW == pytest.approx(1.0)
        assert tc.FCT_MIN_SANCTIONED_KW == pytest.approx(2.0)

    def test_mescom_scale_constants(self):
        assert tc.MESCOM_CONSUMER_COUNT == 22_60_000
        assert tc.FCT_ASSUMED_OVERPROVISION_FRACTION == pytest.approx(0.10)

    def test_fct_pitch_number_works_out_to_39_crore(self):
        # 2,26,000 × Rs. 1,740 = Rs. 39.32 crore.
        affected = tc.MESCOM_CONSUMER_COUNT * tc.FCT_ASSUMED_OVERPROVISION_FRACTION
        annual_waste_per_household = tc.FIXED_CHARGE_PER_KW_CURRENT * 12  # 1 kW excess × 12 months
        total_waste_crore = (affected * annual_waste_per_household) / 1_00_00_000
        assert annual_waste_per_household == 1_740
        assert total_waste_crore == pytest.approx(39.324, abs=0.01)


# =============================================================================
# Date gates
# =============================================================================


class TestDateGates:
    def test_pre_april_2025_gate(self):
        assert tc.EARLIEST_ACCEPTED_BILL_DATE == "2025-04-01"
