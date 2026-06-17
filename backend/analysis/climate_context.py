"""Climate-context framing for bill responses — the Sustainable Development
track reframe (Session 5.8).

Three pure functions:

- ``compute_annual_household_footprint`` — annual kWh → kg CO2 → trees to
  offset, km of car travel. Gives the user a visceral sense of their grid
  footprint in units they already understand (trees, cars).
- ``compute_solar_climate_impact`` — what a 3 kW rooftop system avoids per
  year + 25-year lifetime + a MESCOM-scale scenario ("if 1 % of the 22.6
  lakh MESCOM households install 3 kW, that's ~14,500 cars off road").
- ``generate_consumption_band_tip`` — one-line conservation prescription
  keyed on the consumption band. GJ-enrolled households within striking
  distance of the 200-unit cliff get an extra warning line appended.

All constants come from ``config.tariff_constants``. No magic numbers.
"""
from __future__ import annotations

from typing import Any

from backend.config import tariff_constants as tc


# =============================================================================
# Household footprint
# =============================================================================


def compute_annual_household_footprint(units_consumed: int) -> dict[str, Any]:
    """Annual footprint from one month's consumption figure, projected flat.

    We project the current month × 12 — this is the honest estimate for a
    user who just submitted one bill. Session 7+ could refine with bill
    history when we have more than one row per user.
    """
    annual_kwh = (units_consumed or 0) * 12
    annual_co2_kg = annual_kwh * tc.GRID_EMISSION_FACTOR_KG_PER_KWH
    trees_to_offset = annual_co2_kg / tc.TREE_ABSORPTION_KG_PER_YEAR
    equivalent_km_driven = annual_co2_kg / tc.AVG_INDIAN_CAR_EMISSIONS_KG_PER_KM
    return {
        "annual_kwh": annual_kwh,
        "annual_co2_kg": round(annual_co2_kg, 2),
        "trees_to_offset": round(trees_to_offset, 1),
        "equivalent_km_driven": round(equivalent_km_driven, 0),
    }


# =============================================================================
# Solar climate impact
# =============================================================================


def compute_solar_climate_impact(system_kw: int = 3) -> dict[str, Any]:
    """CO2 a rooftop system avoids + scale framing at 1 % MESCOM adoption."""
    annual_kwh_displaced = system_kw * tc.SPECIFIC_YIELD_KWP_YEAR
    annual_co2_avoided_kg = annual_kwh_displaced * tc.GRID_EMISSION_FACTOR_KG_PER_KWH
    lifetime_25yr_co2_tonnes = annual_co2_avoided_kg * tc.LIFETIME_YEARS / 1_000

    mescom_1pct_households = tc.MESCOM_CONSUMER_COUNT * 0.01
    mescom_scale_co2_tonnes = mescom_1pct_households * annual_co2_avoided_kg / 1_000
    equivalent_cars_off_road = mescom_scale_co2_tonnes / tc.AVG_INDIAN_CAR_ANNUAL_CO2_TONNES

    return {
        "system_kw": system_kw,
        "annual_kwh_displaced": annual_kwh_displaced,
        "annual_co2_avoided_kg": round(annual_co2_avoided_kg, 2),
        "annual_co2_avoided_tonnes": round(annual_co2_avoided_kg / 1_000, 2),
        "lifetime_25yr_co2_tonnes": round(lifetime_25yr_co2_tonnes, 2),
        "mescom_1pct_households": int(mescom_1pct_households),
        "mescom_scale_scenario_tonnes": round(mescom_scale_co2_tonnes, 0),
        "equivalent_cars_off_road": round(equivalent_cars_off_road, 0),
    }


# =============================================================================
# Consumption-band conservation tip
# =============================================================================

_BAND_TIPS = (
    (100,  "Your household is already efficient. Maintain LED lighting and unplug idle electronics."),
    (200,  "Fans, lighting, TV likely dominate. A 5-star BLDC ceiling fan cuts fan electricity by ~50%."),
    (350,  "AC or water heater likely drives consumption. Each 1°C higher AC thermostat saves ~6%. Solar water heater rebate applies for households above 100 units/month."),
    (None, "High-consumption household. Priority levers: solar water heater, AC thermostat, appliance upgrades. Rooftop solar has strongest payback here."),
)


def generate_consumption_band_tip(
    units_consumed: int,
    sanctioned_load_kw: float,
    is_gj: bool,
) -> str:
    """One-line conservation prescription keyed on consumption band.

    For GJ beneficiaries already at 80%+ of the 200-unit hard cliff, append
    an explicit warning so the tip doubles as a cliff reminder.
    """
    units = units_consumed or 0
    tip = _BAND_TIPS[-1][1]  # fallback
    for threshold, text in _BAND_TIPS:
        if threshold is None or units < threshold:
            tip = text
            break

    if is_gj and units > 160:
        tip += " ⚠️ Approaching 200-unit Gruha Jyothi cliff — see cliff warning above."

    return tip
