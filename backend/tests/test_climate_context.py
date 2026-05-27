"""Smoke tests for analysis.climate_context (Session 5.8)."""
from __future__ import annotations

import pytest

from backend.analysis.climate_context import (
    compute_annual_household_footprint,
    compute_solar_climate_impact,
    generate_consumption_band_tip,
)

pytestmark = pytest.mark.smoke


# =============================================================================
# Household footprint
# =============================================================================


class TestHouseholdFootprint:
    def test_nikhil_210_units(self):
        fp = compute_annual_household_footprint(210)
        assert fp["annual_kwh"] == 2520
        # 2520 * 0.710 = 1789.2 kg
        assert fp["annual_co2_kg"] == pytest.approx(1789.2, abs=0.5)
        # 1789.2 / 30 = 59.64 → rounds to ~60
        assert fp["trees_to_offset"] == pytest.approx(59.6, abs=0.5)

    def test_priya_110_units(self):
        fp = compute_annual_household_footprint(110)
        assert fp["annual_kwh"] == 1320
        # 1320 * 0.710 = 937.2
        assert fp["annual_co2_kg"] == pytest.approx(937.2, abs=0.5)
        assert fp["trees_to_offset"] == pytest.approx(31.2, abs=0.5)

    def test_sunita_280_units(self):
        fp = compute_annual_household_footprint(280)
        assert fp["annual_kwh"] == 3360
        # 3360 * 0.710 = 2385.6
        assert fp["annual_co2_kg"] == pytest.approx(2385.6, abs=0.5)
        assert fp["trees_to_offset"] == pytest.approx(79.5, abs=0.5)

    def test_zero_units(self):
        fp = compute_annual_household_footprint(0)
        assert fp["annual_kwh"] == 0
        assert fp["annual_co2_kg"] == 0
        assert fp["trees_to_offset"] == 0


# =============================================================================
# Solar climate impact — for the scale pitch moment
# =============================================================================


class TestSolarClimateImpact:
    def test_3kw_default(self):
        imp = compute_solar_climate_impact()
        # 3 kW * 1400 kWh/kWp/yr = 4200 kWh displaced
        assert imp["annual_kwh_displaced"] == 4200
        # 4200 * 0.710 = 2982 kg = 2.98 tonnes
        assert imp["annual_co2_avoided_kg"] == pytest.approx(2982, abs=1)
        assert imp["annual_co2_avoided_tonnes"] == pytest.approx(2.98, abs=0.01)
        # 2982 * 25 / 1000 = 74.55 tonnes
        assert imp["lifetime_25yr_co2_tonnes"] == pytest.approx(74.55, abs=0.1)

    def test_mescom_scale_scenario(self):
        imp = compute_solar_climate_impact(3)
        # 22,60,000 × 0.01 = 22,600 households
        assert imp["mescom_1pct_households"] == 22_600
        # 22,600 × 2982 / 1000 ≈ 67,393 tonnes
        assert imp["mescom_scale_scenario_tonnes"] == pytest.approx(67_393, abs=50)
        # 67,393 / 4.6 ≈ 14,651 cars
        assert imp["equivalent_cars_off_road"] == pytest.approx(14_651, abs=20)

    def test_2kw_system(self):
        imp = compute_solar_climate_impact(2)
        # 2 × 1400 × 0.710 = 1988 kg = 1.988 tonnes
        assert imp["annual_co2_avoided_tonnes"] == pytest.approx(1.988, abs=0.01)


# =============================================================================
# Consumption band tips
# =============================================================================


class TestConsumptionBandTip:
    def test_efficient_band_under_100(self):
        tip = generate_consumption_band_tip(50, 1.0, is_gj=False)
        assert "efficient" in tip.lower() or "LED" in tip

    def test_mid_band_100_to_200(self):
        tip = generate_consumption_band_tip(150, 2.0, is_gj=False)
        assert "Fans" in tip or "BLDC" in tip

    def test_ac_band_200_to_350(self):
        tip = generate_consumption_band_tip(280, 3.0, is_gj=False)
        assert "AC" in tip or "thermostat" in tip.lower()

    def test_high_consumption_over_350(self):
        tip = generate_consumption_band_tip(450, 5.0, is_gj=False)
        assert "rooftop solar" in tip.lower() or "solar water heater" in tip.lower()

    def test_gj_above_160_gets_cliff_warning_appended(self):
        tip = generate_consumption_band_tip(170, 1.0, is_gj=True)
        # REHENA-class case — warning should be appended.
        assert "Approaching" in tip or "200-unit" in tip

    def test_gj_below_160_no_warning(self):
        tip = generate_consumption_band_tip(110, 2.0, is_gj=True)
        assert "Approaching" not in tip
        assert "200-unit" not in tip

    def test_non_gj_never_gets_cliff_warning_appended(self):
        # High-consumption non-GJ Sunita — shouldn't see a cliff warning.
        tip = generate_consumption_band_tip(280, 3.0, is_gj=False)
        assert "Approaching" not in tip
        assert "Gruha Jyothi cliff" not in tip
