"""Subsidy Navigator — PM Surya Ghar, Gruha Jyothi Visibility, SWH rebate.

Source: tech spec §7, PRD §4.4.

Three surfaces:
- ``check_pm_surya_ghar`` — eligibility verdict + tiered subsidy math.
- ``compute_gj_visibility`` — reveal the invisible subsidy + fire cliff warnings.
- ``check_solar_water_heater_rebate`` — secondary talking point.

All numeric constants come from ``config.tariff_constants``. No magic numbers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from backend.analysis.models import BillExtraction
from backend.config import tariff_constants as tc


# =============================================================================
# PM Surya Ghar — central subsidy (MNRE), tiered
# =============================================================================


def pm_surya_ghar_subsidy(system_kw: int) -> int:
    """Rupee subsidy for a given system size — tech spec §7.1 + §8.3.

    Tier: Rs. 30,000 × first 2 kW, plus Rs. 18,000 × 3rd kW, capped at
    Rs. 78,000. Anything above 3 kW still gets Rs. 78,000.
    """
    if system_kw <= 0:
        return 0
    if system_kw <= 2:
        return int(system_kw) * tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW
    if system_kw == 3:
        return 2 * tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW + tc.PMSG_SUBSIDY_3RD_KW
    return tc.PMSG_SUBSIDY_CAP


def check_pm_surya_ghar(
    sanctioned_load_kw: Optional[float],
    is_gj_beneficiary: bool,
    units_consumed: Optional[int] = None,
    tariff_category: str = tc.DOMESTIC_TARIFF_CODE,
) -> dict[str, Any]:
    """Evaluate PMSG eligibility. Tech spec §7.1 rules.

    Only asserts program eligibility; delegates sizing to the Solar ROI
    calculator. GJ status does not disqualify but is flagged since solar
    ROI is different for GJ beneficiaries under entitlement.
    """
    # Connection type check.
    if not tariff_category or not tariff_category.upper().startswith("LT-1"):
        return {
            "eligible": False,
            "reason": "Scheme is for residential LT-1 consumers only.",
            "subsidy_amount": 0,
            "system_size_kw": 0,
        }

    # Very-low-consumption flag (marginal — solar may not pay back).
    if units_consumed is not None and units_consumed < 50:
        return {
            "eligible": True,
            "status": "marginal",
            "reason": (
                "Your monthly consumption is very low; solar payback will be "
                "slower than typical."
            ),
            "subsidy_amount": tc.PMSG_SUBSIDY_CAP,
            "system_size_kw": 3,
            "subsidy_breakdown": (
                f"Rs. {tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW:,} x 2 + "
                f"Rs. {tc.PMSG_SUBSIDY_3RD_KW:,} x 1 = "
                f"Rs. {tc.PMSG_SUBSIDY_CAP:,}"
            ),
            "apply_url": "https://pmsuryaghar.gov.in",
            "mescom_srtpv_url": "https://srtpv.mesco.in",
            "note": (
                "Eligibility also requires that you own your roof or have a "
                "long-term tenancy."
            ),
        }

    # Standard case — assume 3 kW as the subsidy-maximising ceiling; Solar ROI
    # may downscale if appropriate.
    return {
        "eligible": True,
        "status": "eligible",
        "reason": (
            "Domestic LT-1 with sanctioned load suitable for rooftop solar."
            + (
                " You are currently a Gruha Jyothi beneficiary — solar payback "
                "is slower while you're under entitlement (see Solar ROI)."
                if is_gj_beneficiary else ""
            )
        ),
        "subsidy_amount": tc.PMSG_SUBSIDY_CAP,
        "system_size_kw": 3,
        "subsidy_breakdown": (
            f"Rs. {tc.PMSG_SUBSIDY_FIRST_2_KW_PER_KW:,} x 2 + "
            f"Rs. {tc.PMSG_SUBSIDY_3RD_KW:,} x 1 = Rs. {tc.PMSG_SUBSIDY_CAP:,}"
        ),
        "apply_url": "https://pmsuryaghar.gov.in",
        "mescom_srtpv_url": "https://srtpv.mesco.in",
        "note": (
            "Eligibility also requires that you own your roof or have a "
            "long-term tenancy."
        ),
    }


# =============================================================================
# Gruha Jyothi Visibility — the three-level cliff + Level 0 approaching
# =============================================================================


@dataclass(frozen=True)
class GJWarning:
    """A single cliff warning produced by ``compute_gj_warnings``."""

    level: str       # "red" | "yellow" | "info" | "green"
    cliff: Optional[str]   # "eligibility" | "monthly_hard" | "soft_step" | "approaching_entitlement" | None
    message: Optional[str]


def _overall_risk(warnings: list[GJWarning]) -> str:
    """Collapse a warnings list into a single red/yellow/green signal."""
    levels = {w.level for w in warnings}
    if "red" in levels:
        return "red"
    if "yellow" in levels or "info" in levels:
        return "yellow"
    return "green"


# =============================================================================
# Session 5.8 — Level 2 cliff enhancement (cost + behavior + CO2)
# =============================================================================

# Power draw assumptions used to translate "cut X units" into everyday units
# of behavior the user can act on. Pitch-defensible sources:
# - 70 W: BEE-certified 5-star BLDC ceiling fan.
# - 1000 W: mid-size split AC (1.0-1.5 ton nominal).
_FAN_WATTS = 70
_AC_WATTS = 1000


def _enhanced_level_2_message(
    units_consumed: int,
    hypothetical_full_bill: float,
    severity: str,            # "red" (>=95% of 200) | "yellow" (80-94%)
) -> str:
    """Actionable Level-2 cliff message with cost, behavior, and CO2 framing.

    Shown only for households still UNDER the 200-unit cap (we nudge them
    to stay under). Households already over 200 get a different, simpler
    "you've lost the subsidy" message handled upstream.
    """
    units_to_cut = max(1, tc.GJ_MONTHLY_HARD_CLIFF_UNITS - units_consumed)

    # Behavior prescription — per-day reductions so the framing is relatable.
    # Monthly kWh × 1000 / watts = monthly hours. Divide by 30 for daily.
    fan_hours_daily = round((units_to_cut * 1000 / _FAN_WATTS) / 30, 1)
    ac_minutes_daily = round((units_to_cut * 1000 / _AC_WATTS) / 30 * 60)

    # CO2 framing: kg avoided + tree-days of offset (1 tree absorbs
    # 30 kg/year = ~0.082 kg/day, so kg × 365/30 gives tree-days).
    co2_avoided_kg = units_to_cut * tc.GRID_EMISSION_FACTOR_KG_PER_KWH
    tree_days = int(round(co2_avoided_kg * 365 / tc.TREE_ABSORPTION_KG_PER_YEAR))

    if severity == "red":
        header = (
            f"⚠️ Gruha Jyothi Cliff Alert — {units_consumed} of "
            f"{tc.GJ_MONTHLY_HARD_CLIFF_UNITS} free units used.\n"
            f"Crossing {tc.GJ_MONTHLY_HARD_CLIFF_UNITS} means paying the "
            f"ENTIRE bill this month — approximately "
            f"Rs. {hypothetical_full_bill:,.0f}."
        )
    else:
        header = (
            f"⚡ Gruha Jyothi Watch — {units_consumed} of "
            f"{tc.GJ_MONTHLY_HARD_CLIFF_UNITS} free units used.\n"
            f"If you cross {tc.GJ_MONTHLY_HARD_CLIFF_UNITS} this month, "
            f"the full bill (~Rs. {hypothetical_full_bill:,.0f}) becomes "
            f"payable — no partial subsidy."
        )

    return (
        f"{header}\n\n"
        "To stay safe:\n"
        f"🎯 Cut {units_to_cut} units — roughly {fan_hours_daily} hours "
        f"less fan OR {ac_minutes_daily} minutes less AC per day.\n"
        "💰 Stay at your Rs. 0 net bill.\n"
        f"🌱 {co2_avoided_kg:.1f} kg CO2 avoided — equal to "
        f"{tree_days} tree-days of offset."
    )


def compute_gj_warnings(
    units_consumed: int,
    entitlement_units: float,
    trailing_10m_avg: Optional[float],
    hypothetical_full_bill: float,
) -> list[GJWarning]:
    """Produce the ordered warnings list for a GJ beneficiary.

    Precedence (user override of tech-spec ordering, Session 3):
    ``eligibility > monthly_hard > soft_step > approaching``.

    Level 0 (approaching) is load-bearing per CLAUDE.md §3 Rule 1. Without
    it, Priya (110/115 = 95.7%) fires no warnings under the 3-level logic
    and the GJ Visibility demo moment dies.
    """
    if entitlement_units is None or entitlement_units <= 0:
        # Defensive — the extractor should have populated entitlement_units
        # for GJ bills, but fall back gracefully.
        return [GJWarning(level="green", cliff=None, message=None)]

    warnings: list[GJWarning] = []

    entitlement_util = units_consumed / entitlement_units
    hard_cap_util = units_consumed / tc.GJ_MONTHLY_HARD_CLIFF_UNITS

    # --- Level 3 — eligibility at risk (most severe, flag first) ---
    if trailing_10m_avg is not None:
        eligibility_util = trailing_10m_avg / tc.GJ_MONTHLY_HARD_CLIFF_UNITS
        if eligibility_util >= tc.GJ_ELIGIBILITY_RED_THRESHOLD:
            warnings.append(GJWarning(
                level="red",
                cliff="eligibility",
                message=(
                    f"Your 10-month average is {trailing_10m_avg:.0f} units — "
                    f"near the 200-unit disqualification limit. One high-"
                    f"consumption month could end your Gruha Jyothi enrollment "
                    f"entirely (re-qualify only over a fresh 10-month window)."
                ),
            ))
        elif eligibility_util >= tc.GJ_ELIGIBILITY_YELLOW_THRESHOLD:
            warnings.append(GJWarning(
                level="yellow",
                cliff="eligibility",
                message=(
                    f"Your 10-month average ({trailing_10m_avg:.0f} units) is "
                    f"trending toward the 200-unit eligibility limit."
                ),
            ))

    # --- Level 2 — monthly hard cliff (200 units) ---
    # Enhanced in Session 5.8: 160-199 range adds specific cliff cost +
    # behavior prescription + CO2 equivalence so the warning is
    # actionable, not just alarming. Crossing 200 already → informational
    # "you lost the subsidy" message (no "stay safe" phrasing).
    if units_consumed > tc.GJ_MONTHLY_HARD_CLIFF_UNITS:
        warnings.append(GJWarning(
            level="red",
            cliff="monthly_hard",
            message=(
                f"You used {units_consumed} units — OVER the 200-unit cap. "
                f"The entire Rs. {hypothetical_full_bill:,.0f} was payable "
                f"this month, not just the excess. Subsidy fully lost for "
                f"this cycle."
            ),
        ))
    elif hard_cap_util >= tc.GJ_HARD_CAP_RED_THRESHOLD:
        warnings.append(GJWarning(
            level="red",
            cliff="monthly_hard",
            message=_enhanced_level_2_message(
                units_consumed=units_consumed,
                hypothetical_full_bill=hypothetical_full_bill,
                severity="red",
            ),
        ))
    elif hard_cap_util >= tc.GJ_HARD_CAP_YELLOW_THRESHOLD:
        warnings.append(GJWarning(
            level="yellow",
            cliff="monthly_hard",
            message=_enhanced_level_2_message(
                units_consumed=units_consumed,
                hypothetical_full_bill=hypothetical_full_bill,
                severity="yellow",
            ),
        ))

    # --- Level 1 — soft step (units > entitlement, still within 200) ---
    # "Info" severity: you're paying the standard tariff for the excess, not
    # losing the whole subsidy.
    if (
        entitlement_util >= 1.0
        and units_consumed <= tc.GJ_MONTHLY_HARD_CLIFF_UNITS
    ):
        excess_units = units_consumed - entitlement_units
        warnings.append(GJWarning(
            level="info",
            cliff="soft_step",
            message=(
                f"You've used {excess_units:.0f} units above your "
                f"{entitlement_units:.0f}-unit entitlement — "
                f"you'll pay standard tariff for those excess units."
            ),
        ))

    # --- Level 0 — approaching personal entitlement (proactive) ---
    # Fires regardless of soft_step; once you've crossed, the user sees
    # both warnings (soft_step first per precedence, then approaching).
    if entitlement_util >= tc.GJ_APPROACHING_RED_THRESHOLD:
        warnings.append(GJWarning(
            level="red",
            cliff="approaching_entitlement",
            message=(
                f"You've used {int(entitlement_util * 100)}% of your "
                f"{entitlement_units:.0f}-unit entitlement. Crossing "
                f"entitlement starts chargeable units."
            ),
        ))
    elif entitlement_util >= tc.GJ_APPROACHING_YELLOW_THRESHOLD:
        warnings.append(GJWarning(
            level="yellow",
            cliff="approaching_entitlement",
            message=(
                f"You've used {int(entitlement_util * 100)}% of your "
                f"{entitlement_units:.0f}-unit entitlement. Keep usage "
                f"in check this cycle."
            ),
        ))

    if not warnings:
        return [GJWarning(level="green", cliff=None, message=None)]
    return warnings


@dataclass(frozen=True)
class GJReport:
    """Output of ``compute_gj_visibility``."""

    is_gj_beneficiary: bool
    monthly_subsidy_received: float
    enrollment_date: Optional[str]
    months_since_enrollment: Optional[int]
    estimated_total_subsidy_received: float
    annualized_subsidy: float
    entitlement_units: Optional[float]
    units_consumed: Optional[int]
    entitlement_utilization_pct: Optional[float]
    cliffs: dict[str, Any]
    warnings: list[GJWarning] = field(default_factory=list)
    overall_risk: str = "green"
    cliff_explanation: str = ""


def _months_between(start_iso: Optional[str], end: Optional[date]) -> Optional[int]:
    if not start_iso or end is None:
        return None
    try:
        start = date.fromisoformat(start_iso)
    except ValueError:
        return None
    months = (end.year - start.year) * 12 + (end.month - start.month)
    return max(0, months)


CLIFF_EXPLANATION = (
    "Gruha Jyothi has three separate cliffs. "
    "(1) Cross your entitlement: pay for excess units. "
    "(2) Cross 200 units in any month: pay the ENTIRE bill, not just excess. "
    "(3) 10-month average above 200 units: lose the scheme entirely. "
    "Most beneficiaries know about #1. Very few know about #2 and #3."
)


def compute_gj_visibility(
    extraction: BillExtraction,
    trailing_10m_avg: Optional[float] = None,
) -> GJReport:
    """Reveal the invisible subsidy and attach cliff warnings.

    If the caller passes ``trailing_10m_avg=None``, the Level 3 eligibility
    warning is skipped (insufficient information). Session 4 will supply
    this from the ``bills`` table as history accumulates.
    """
    if not extraction.is_gruha_jyothi_beneficiary:
        return GJReport(
            is_gj_beneficiary=False,
            monthly_subsidy_received=0.0,
            enrollment_date=None,
            months_since_enrollment=None,
            estimated_total_subsidy_received=0.0,
            annualized_subsidy=0.0,
            entitlement_units=None,
            units_consumed=extraction.units_consumed,
            entitlement_utilization_pct=None,
            cliffs={},
            warnings=[],
            overall_risk="green",
            cliff_explanation="",
        )

    monthly_subsidy = extraction.gruha_jyothi_subsidy_amount or 0.0
    annualized = monthly_subsidy * 12

    billing_end = None
    if extraction.billing_period_end:
        try:
            billing_end = date.fromisoformat(extraction.billing_period_end)
        except ValueError:
            billing_end = None

    months_since = _months_between(extraction.gjs_registration_date, billing_end)
    total_subsidy = monthly_subsidy * months_since if months_since else monthly_subsidy

    entitlement = extraction.entitlement_units
    units = extraction.units_consumed or 0
    util_pct = (units / entitlement * 100) if (entitlement and entitlement > 0) else None

    # Hypothetical full bill = what the consumer would pay if they crossed
    # 200 units. Best estimate: subtotal_1 as-is (the extractor's value).
    hypothetical = extraction.subtotal_1_before_subsidy or 0.0

    warnings_list = compute_gj_warnings(
        units_consumed=units,
        entitlement_units=entitlement or 0.0,
        trailing_10m_avg=trailing_10m_avg,
        hypothetical_full_bill=hypothetical,
    )

    # Per-cliff state snapshot for the response composer / dashboard.
    approaching_triggered = bool(
        entitlement
        and (units / entitlement) >= tc.GJ_APPROACHING_YELLOW_THRESHOLD
    )
    cliffs = {
        "approaching_entitlement": {
            "triggered": approaching_triggered,
            "distance_units": (entitlement - units) if entitlement else None,
        },
        "soft_step": {
            "triggered": bool(
                entitlement
                and units > entitlement
                and units <= tc.GJ_MONTHLY_HARD_CLIFF_UNITS
            ),
            "excess_units": max(0, units - (entitlement or 0)) if entitlement else 0,
        },
        "monthly_hard": {
            "triggered": units > tc.GJ_MONTHLY_HARD_CLIFF_UNITS,
            "distance_units": tc.GJ_MONTHLY_HARD_CLIFF_UNITS - units,
            "hypothetical_full_bill_if_triggered": hypothetical,
        },
        "eligibility": {
            "at_risk": (
                trailing_10m_avg is not None
                and trailing_10m_avg / tc.GJ_MONTHLY_HARD_CLIFF_UNITS
                >= tc.GJ_ELIGIBILITY_YELLOW_THRESHOLD
            ),
            "trailing_10m_average": trailing_10m_avg,
            "distance_units": (
                tc.GJ_MONTHLY_HARD_CLIFF_UNITS - trailing_10m_avg
                if trailing_10m_avg is not None else None
            ),
        },
    }

    return GJReport(
        is_gj_beneficiary=True,
        monthly_subsidy_received=monthly_subsidy,
        enrollment_date=extraction.gjs_registration_date,
        months_since_enrollment=months_since,
        estimated_total_subsidy_received=total_subsidy,
        annualized_subsidy=annualized,
        entitlement_units=entitlement,
        units_consumed=units,
        entitlement_utilization_pct=util_pct,
        cliffs=cliffs,
        warnings=warnings_list,
        overall_risk=_overall_risk(warnings_list),
        cliff_explanation=CLIFF_EXPLANATION,
    )


# =============================================================================
# Solar water heater rebate — tech spec §7.3
# =============================================================================


def check_solar_water_heater_rebate(
    units_consumed: Optional[int],
    tariff_category: str = tc.DOMESTIC_TARIFF_CODE,
) -> dict[str, Any]:
    """Secondary talking point — Rs. 0.25/unit energy discount.

    Per tech spec §7.3: LT-1 only, requires BIS-certified SWH. Returns a
    monthly saving estimate the response composer can surface.
    """
    if not tariff_category or not tariff_category.upper().startswith("LT-1"):
        return {
            "eligible": False,
            "reason": "Solar water heater rebate is LT-1 Domestic only.",
        }

    per_unit_discount = 0.25  # tech spec §7.3; not a KERC primary source
    monthly_saving = (units_consumed or 0) * per_unit_discount
    return {
        "eligible": True,
        "reason": "LT-1 Domestic — BIS-certified solar water heater unlocks a per-unit discount.",
        "discount_per_unit_rupees": per_unit_discount,
        "monthly_saving_estimate": round(monthly_saving, 2),
        "annual_saving_estimate": round(monthly_saving * 12, 2),
        "fixed_charge_rebate_per_kw": tc.SOLAR_ROOFTOP_REBATE_PER_KW,
        "fixed_charge_rebate_cap_kw": tc.SOLAR_ROOFTOP_REBATE_CAP_KW,
        "condition": "Requires BIS-certified solar water heater installation.",
    }
