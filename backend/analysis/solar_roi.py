"""Solar ROI Calculator — system sizing, payback, lifetime, CO2.

Source: tech spec §8. Nikhil's worked example in briefing §4 is the test
oracle — ``compute_roi(3, 210, False)`` must produce:

- ``payback_months == 45``
- ``lifetime_net_savings_flat`` within Rs. 1,000 of Rs. 4,31,126
- ``co2_offset_tonnes_per_year`` within 0.05 of 2.98
- ``trees_equivalent`` ≈ 100

GJ beneficiaries whose current consumption is under entitlement receive a
``recommendation="not_recommended"`` result with an honest explanation
(tech spec §8.7).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Optional

from backend.config import tariff_constants as tc


# =============================================================================
# System sizing
# =============================================================================


def size_system(
    annual_consumption_kwh: float,
    sanctioned_load_kw: Optional[float] = None,
) -> int:
    """Recommend a system size (kW) for a household's annual consumption.

    Heuristic: `ceil(annual_kWh / specific_yield)`, capped at 3 kW
    (hackathon scope + PMSG subsidy ceiling). If the caller supplies the
    sanctioned load and the sized system is strictly smaller, bump up to
    min(sanctioned, 3) — this matches tech spec §8.2's "sized to sanctioned
    load to maximize subsidy" note for Nikhil.
    """
    if annual_consumption_kwh <= 0:
        return 0
    sized = ceil(annual_consumption_kwh / tc.SPECIFIC_YIELD_KWP_YEAR)
    if sanctioned_load_kw is not None:
        sized = max(sized, int(min(sanctioned_load_kw, 3)))
    return max(1, min(sized, 3))


# =============================================================================
# Financial components — per-month figures for a given consumption profile
# =============================================================================


def _monthly_variable_bill(units_consumed: int) -> float:
    """Variable portion of a non-GJ LT-1 bill (energy + P&G + tax + FPPCA).

    Solar displaces these, but NOT the fixed charge (the consumer remains
    grid-connected). Tech spec §8.4.
    """
    energy = units_consumed * tc.ENERGY_CHARGE_FLAT_RATE
    pg = units_consumed * tc.PG_SURCHARGE_PER_UNIT
    tax = energy * tc.ELECTRICITY_TAX_RATE
    fppca = units_consumed * tc.FPPCA_PLACEHOLDER_RATE
    return energy + pg + tax + fppca


# =============================================================================
# Output dataclass
# =============================================================================


@dataclass(frozen=True)
class SolarROI:
    """Solar ROI analysis result for one household."""

    system_kw: int
    recommendation: str                # "recommended" | "marginal" | "not_recommended"
    recommendation_reason: str

    # Costs
    system_cost: float
    pmsg_subsidy: float
    net_cost: float

    # Generation & consumption split
    annual_generation_kwh: float
    monthly_generation_kwh: float
    monthly_self_consumption_kwh: float
    monthly_export_kwh: float

    # Monthly benefit components
    monthly_bill_displaced: float
    monthly_export_credit: float
    monthly_fixed_rebate: float
    total_monthly_benefit: float

    # Payback
    payback_months: int
    payback_years: float

    # 25-year lifetime (flat tariffs — conservative pitch number)
    lifetime_gross_savings_flat: float
    lifetime_net_savings_flat: float

    # 25-year lifetime with 3% annual escalation (realistic upside)
    lifetime_gross_savings_3pct: float
    lifetime_net_savings_3pct: float

    # Environmental
    co2_offset_tonnes_per_year: float
    trees_equivalent: int


# =============================================================================
# Core ROI computation
# =============================================================================


def _pmsg_subsidy(system_kw: int) -> int:
    """Mirror of analysis.subsidy_navigator.pm_surya_ghar_subsidy, duplicated
    here to keep solar_roi decoupled from the Navigator.
    """
    if system_kw <= 0:
        return 0
    if system_kw <= 2:
        return system_kw * tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW
    if system_kw == 3:
        return 2 * tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW + tc.PMSG_SUBSIDY_3RD_KW
    return tc.PMSG_SUBSIDY_CAP


def _lifetime_savings(
    monthly_benefit: float,
    net_cost: float,
    system_kw: int,
) -> tuple[float, float, float, float]:
    """Return (gross_flat, net_flat, gross_3pct, net_3pct) over 25 years."""
    months = tc.LIFETIME_YEARS * 12
    gross_flat = monthly_benefit * months

    degradation = system_kw * tc.DEGRADATION_LIFETIME_COST_PER_KW
    deductions = net_cost + degradation + tc.INVERTER_REPLACEMENT_COST
    net_flat = gross_flat - deductions

    # 3% compounding annual escalation: geometric series.
    r = tc.ANNUAL_TARIFF_ESCALATION
    annual_benefit = monthly_benefit * 12
    gross_3pct = annual_benefit * ((1 + r) ** tc.LIFETIME_YEARS - 1) / r
    net_3pct = gross_3pct - deductions

    return gross_flat, net_flat, gross_3pct, net_3pct


def compute_roi(
    system_kw: int,
    monthly_consumption: int,
    is_gj_beneficiary: bool,
    entitlement_units: Optional[float] = None,
) -> SolarROI:
    """Full Solar ROI analysis.

    For GJ beneficiaries under entitlement, returns a ``not_recommended``
    result with reasoning per tech spec §8.7 — the honest outcome the pitch
    commits to surfacing rather than hiding.
    """
    # --- Costs ---
    system_cost = system_kw * tc.SYSTEM_COST_PER_KW
    pmsg = _pmsg_subsidy(system_kw)
    net_cost = system_cost - pmsg

    # --- Generation ---
    annual_gen = system_kw * tc.SPECIFIC_YIELD_KWP_YEAR
    monthly_gen = annual_gen / 12
    self_consumption = min(monthly_consumption, monthly_gen)
    export = max(0.0, monthly_gen - monthly_consumption)

    # --- Monthly benefit ---
    bill_displaced = _monthly_variable_bill(int(self_consumption))
    export_credit = export * tc.SOLAR_EXPORT_RATE_2_3_KW
    fixed_rebate = min(system_kw, tc.SOLAR_ROOFTOP_REBATE_CAP_KW) * tc.SOLAR_ROOFTOP_REBATE_PER_KW
    monthly_benefit = bill_displaced + export_credit + fixed_rebate

    # --- Payback ---
    payback_months_exact = net_cost / monthly_benefit if monthly_benefit > 0 else float("inf")
    payback_months = int(round(payback_months_exact))
    payback_years = round(payback_months_exact / 12, 1)

    # --- Lifetime savings (both scenarios) ---
    gross_flat, net_flat, gross_3pct, net_3pct = _lifetime_savings(
        monthly_benefit, net_cost, system_kw
    )

    # --- Environmental ---
    co2_tonnes = annual_gen * tc.GRID_EMISSION_FACTOR_KG_PER_KWH / 1_000
    trees = round(annual_gen * tc.GRID_EMISSION_FACTOR_KG_PER_KWH / tc.TREE_ABSORPTION_KG_PER_YEAR)

    # --- Recommendation (GJ-under-entitlement gets honest "not recommended") ---
    if (
        is_gj_beneficiary
        and entitlement_units
        and monthly_consumption < entitlement_units
    ):
        recommendation = "not_recommended"
        reason = (
            "Your grid electricity is effectively free under Gruha Jyothi. "
            "Solar displaces something you aren't paying for, making the "
            "investment much slower to pay back. Consider solar when you're "
            "approaching the three-level cliff — monthly consumption trending "
            "toward 200, 10-month average approaching 200, or already paying "
            "for excess units above your entitlement."
        )
    elif monthly_consumption < 50:
        recommendation = "marginal"
        reason = "Your monthly consumption is very low; payback will be slower than typical."
    else:
        recommendation = "recommended"
        reason = (
            "Full bill liability with clear ROI case."
            if not is_gj_beneficiary
            else "You're already over Gruha Jyothi entitlement — solar has real value here."
        )

    return SolarROI(
        system_kw=system_kw,
        recommendation=recommendation,
        recommendation_reason=reason,
        system_cost=system_cost,
        pmsg_subsidy=pmsg,
        net_cost=net_cost,
        annual_generation_kwh=annual_gen,
        monthly_generation_kwh=monthly_gen,
        monthly_self_consumption_kwh=self_consumption,
        monthly_export_kwh=export,
        monthly_bill_displaced=round(bill_displaced, 2),
        monthly_export_credit=round(export_credit, 2),
        monthly_fixed_rebate=float(fixed_rebate),
        total_monthly_benefit=round(monthly_benefit, 2),
        payback_months=payback_months,
        payback_years=payback_years,
        lifetime_gross_savings_flat=round(gross_flat, 2),
        lifetime_net_savings_flat=round(net_flat, 2),
        lifetime_gross_savings_3pct=round(gross_3pct, 2),
        lifetime_net_savings_3pct=round(net_3pct, 2),
        co2_offset_tonnes_per_year=round(co2_tonnes, 3),
        trees_equivalent=trees,
    )
