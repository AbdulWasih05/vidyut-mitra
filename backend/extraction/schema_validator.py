"""Structural validation for Gemini bill extractions — tech spec §4.3.

Validation is structural, not confidence-based. Gemini's self-reported
``extraction_confidence`` is a soft signal only.

Rules:
- R1: ``is_mescom_bill == True``. Failure is terminal ("not_mescom").
- R2: ``billing_period_end >= EARLIEST_ACCEPTED_BILL_DATE``. Failure is
  terminal ("pre_april_2025") per CLAUDE.md §3 Rule 5.
- R3-R8: range and arithmetic checks. Failures accumulate and trigger a
  single Gemini retry with a stricter prompt.

Issue strings are prefixed with the rule code (e.g. ``"R3: ..."``) so the
pipeline can dispatch on terminal vs retriable failures.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from backend.config.tariff_constants import (
    EARLIEST_ACCEPTED_BILL_DATE,
    ENERGY_CHARGE_FLAT_RATE,
)


# Tolerances from tech spec §4.3.
METER_READING_TOLERANCE_UNITS = 5    # R6
BILL_MATH_TOLERANCE_RUPEES = 5        # R7, R8
# R9: tariff sanity. Use the larger of Rs. 10 or 2% of expected; bills round
# differently across utilities and partial-month proration adds small drift.
TARIFF_SANITY_FLOOR_RUPEES = 10
TARIFF_SANITY_PCT = 0.02


def _parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def validate_extraction(data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Run R1-R8 on a raw Gemini extraction dict.

    Returns ``(is_valid, issues)``. ``is_valid`` is True iff no issues were
    found. Issue strings are human-readable but always prefixed with the
    rule code so the pipeline can dispatch on terminal failures.
    """
    issues: list[str] = []

    # --- R1: MESCOM bill ---
    if not data.get("is_mescom_bill"):
        issues.append("R1: Not a MESCOM bill (is_mescom_bill is false or missing).")
        # R1 is terminal — no point running further checks.
        return False, issues

    # --- R2: Pre-April 2025 gate ---
    billing_period_end = _parse_iso_date(data.get("billing_period_end"))
    earliest = date.fromisoformat(EARLIEST_ACCEPTED_BILL_DATE)
    if billing_period_end is None:
        issues.append(
            "R2: billing_period_end is missing or not an ISO date — "
            "cannot confirm this bill is post-April 2025."
        )
    elif billing_period_end < earliest:
        issues.append(
            f"R2: Bill is from before April 2025 "
            f"(billing_period_end={billing_period_end.isoformat()}, "
            f"earliest accepted={EARLIEST_ACCEPTED_BILL_DATE}). "
            f"KERC updated the tariff structure in April 2025."
        )
        # R2 is terminal — return now.
        return False, issues

    # --- R3: units_consumed range ---
    units = data.get("units_consumed")
    if not isinstance(units, (int, float)) or not (0 < units <= 10_000):
        issues.append(
            f"R3: units_consumed must be in (0, 10000]; got {units!r}."
        )

    # --- R4: sanctioned_load_kw range ---
    sanctioned = data.get("sanctioned_load_kw")
    if not isinstance(sanctioned, (int, float)) or not (0 < sanctioned <= 50):
        issues.append(
            f"R4: sanctioned_load_kw must be in (0, 50]; got {sanctioned!r}."
        )

    # --- R5 & R6: meter reading deltas ---
    prev = data.get("previous_reading")
    curr = data.get("current_reading")
    if isinstance(prev, (int, float)) and isinstance(curr, (int, float)):
        if not (curr > prev):
            issues.append(
                f"R5: current_reading ({curr}) must exceed previous_reading ({prev})."
            )
        elif isinstance(units, (int, float)):
            delta = curr - prev
            if abs(delta - units) > METER_READING_TOLERANCE_UNITS:
                issues.append(
                    f"R6: units_consumed ({units}) differs from "
                    f"current_reading - previous_reading ({delta}) by more than "
                    f"{METER_READING_TOLERANCE_UNITS} units."
                )
    # If readings are missing, skip R5/R6 quietly — not all bills show readings
    # clearly and R3 already covers units_consumed itself.

    # --- R7: bill math ---
    components = [
        data.get("energy_charges"),
        data.get("fixed_charges"),
        data.get("pg_surcharge"),
        data.get("electricity_tax"),
        data.get("fppca"),
        data.get("other_charges"),
    ]
    subtotal_1 = data.get("subtotal_1_before_subsidy")
    if isinstance(subtotal_1, (int, float)) and all(
        isinstance(c, (int, float)) for c in components
    ):
        summed = sum(c for c in components if isinstance(c, (int, float)))
        if abs(subtotal_1 - summed) > BILL_MATH_TOLERANCE_RUPEES:
            issues.append(
                f"R7: subtotal_1_before_subsidy ({subtotal_1:.2f}) does not match "
                f"sum of components ({summed:.2f}) within ±Rs. "
                f"{BILL_MATH_TOLERANCE_RUPEES}."
            )

    # --- R8: GJ math (only if GJ beneficiary) ---
    if data.get("is_gruha_jyothi_beneficiary"):
        gj_subsidy = data.get("gruha_jyothi_subsidy_amount")
        net_bill = data.get("net_bill_amount")
        if (
            isinstance(subtotal_1, (int, float))
            and isinstance(gj_subsidy, (int, float))
            and isinstance(net_bill, (int, float))
        ):
            expected_net = max(0.0, subtotal_1 - gj_subsidy)
            if abs(expected_net - net_bill) > BILL_MATH_TOLERANCE_RUPEES:
                issues.append(
                    f"R8: GJ bill math mismatch — "
                    f"max(0, subtotal_1 ({subtotal_1:.2f}) - gj_subsidy "
                    f"({gj_subsidy:.2f})) = {expected_net:.2f} does not match "
                    f"net_bill_amount ({net_bill:.2f}) within ±Rs. "
                    f"{BILL_MATH_TOLERANCE_RUPEES}."
                )

    # --- R9: tariff sanity (LT-1 domestic only) ---
    # Catches Gemini hallucinating energy_charges when units_consumed is read
    # correctly (or vice versa). LT-1 has a flat Rs. 5.80/unit rate post-April
    # 2025, so the product is deterministic. Skipped for non-LT-1 categories
    # (commercial, industrial) which use slabs we don't model here.
    tariff = data.get("tariff_category")
    if (
        isinstance(tariff, str)
        and tariff.upper().startswith("LT-1")
        and isinstance(units, (int, float))
        and isinstance(data.get("energy_charges"), (int, float))
    ):
        expected_energy = units * ENERGY_CHARGE_FLAT_RATE
        actual_energy = data["energy_charges"]
        tolerance = max(TARIFF_SANITY_FLOOR_RUPEES, expected_energy * TARIFF_SANITY_PCT)
        if abs(expected_energy - actual_energy) > tolerance:
            issues.append(
                f"R9: tariff sanity — units ({units}) × Rs. "
                f"{ENERGY_CHARGE_FLAT_RATE}/unit = Rs. {expected_energy:.2f} "
                f"does not match energy_charges (Rs. {actual_energy:.2f}) "
                f"within Rs. {tolerance:.0f}. One of the two has likely been misread."
            )

    return (len(issues) == 0), issues


def is_terminal_not_mescom(issues: list[str]) -> bool:
    return any(i.startswith("R1:") for i in issues)


def is_terminal_pre_april_2025(issues: list[str]) -> bool:
    return any(i.startswith("R2:") for i in issues)
