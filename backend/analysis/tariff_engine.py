"""Deterministic, pure-functional tariff engine for electricity bill analysis."""

from dataclasses import dataclass

from backend.config import tariff_constants as tc


ENERGY_RATE = getattr(tc, "ENERGY_CHARGE_FLAT_RATE", getattr(tc, "ENERGY_RATE", 5.80))
FIXED_CHARGE_RATE = getattr(
    tc,
    "FIXED_CHARGE_PER_KW_CURRENT",
    getattr(tc, "FIXED_CHARGE_PER_KW", 145),
)
ELECTRICITY_TAX_RATE = tc.ELECTRICITY_TAX_RATE
PG_SURCHARGE_PER_UNIT = tc.PG_SURCHARGE_PER_UNIT
FPPCA_PER_UNIT = getattr(tc, "FPPCA_PLACEHOLDER_RATE", getattr(tc, "FPPCA_PER_UNIT", 0.50))
FCT_OVERPROVISION_THRESHOLD_KW = getattr(
    tc,
    "FCT_BUFFER_KW",
    getattr(tc, "FCT_OVERPROVISION_THRESHOLD_KW", 1.0),
)


@dataclass(frozen=True)
class BillComputation:
    """Computed bill components from tariff rules."""

    energy_charges: float
    fixed_charges: float
    pg_surcharge: float
    electricity_tax: float
    fppca: float
    subtotal_1: float


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating extracted bill fields against expected computation."""

    expected: BillComputation
    actual: BillComputation
    discrepancies: dict[str, float]
    is_valid: bool


@dataclass(frozen=True)
class BillExtraction:
    """Extracted bill values required for tariff validation."""

    units_consumed: float
    sanctioned_load_kw: float
    energy_charges: float
    fixed_charges: float
    pg_surcharge: float
    electricity_tax: float
    fppca: float


def _round2(value: float) -> float:
    """Round monetary or scalar values to 2 decimal places."""
    return round(value, 2)


def compute_bill(units_consumed: float, sanctioned_load_kw: float) -> BillComputation:
    """Compute bill components using tariff constants.

    All returned monetary values are rounded to 2 decimals.
    """
    energy_charges = _round2(units_consumed * ENERGY_RATE)
    fixed_charges = _round2(sanctioned_load_kw * FIXED_CHARGE_RATE)
    pg_surcharge = _round2(units_consumed * PG_SURCHARGE_PER_UNIT)
    fppca = _round2(units_consumed * FPPCA_PER_UNIT)
    electricity_tax = _round2(energy_charges * ELECTRICITY_TAX_RATE)

    subtotal_1 = _round2(
        energy_charges
        + fixed_charges
        + pg_surcharge
        + electricity_tax
        + fppca
    )

    return BillComputation(
        energy_charges=energy_charges,
        fixed_charges=fixed_charges,
        pg_surcharge=pg_surcharge,
        electricity_tax=electricity_tax,
        fppca=fppca,
        subtotal_1=subtotal_1,
    )


def validate_bill(extraction: BillExtraction) -> ValidationResult:
    """Validate extracted bill fields against expected computed values.

    A discrepancy up to 5 rupees per component is acceptable.
    """
    expected = compute_bill(extraction.units_consumed, extraction.sanctioned_load_kw)

    actual = BillComputation(
        energy_charges=_round2(extraction.energy_charges),
        fixed_charges=_round2(extraction.fixed_charges),
        pg_surcharge=_round2(extraction.pg_surcharge),
        electricity_tax=_round2(extraction.electricity_tax),
        fppca=_round2(extraction.fppca),
        subtotal_1=_round2(
            extraction.energy_charges
            + extraction.fixed_charges
            + extraction.pg_surcharge
            + extraction.electricity_tax
            + extraction.fppca
        ),
    )

    discrepancies = {
        "energy_charges": _round2(abs(expected.energy_charges - actual.energy_charges)),
        "fixed_charges": _round2(abs(expected.fixed_charges - actual.fixed_charges)),
        "pg_surcharge": _round2(abs(expected.pg_surcharge - actual.pg_surcharge)),
        "electricity_tax": _round2(abs(expected.electricity_tax - actual.electricity_tax)),
        "fppca": _round2(abs(expected.fppca - actual.fppca)),
    }

    is_valid = all(diff <= 5.0 for diff in discrepancies.values())

    return ValidationResult(
        expected=expected,
        actual=actual,
        discrepancies=discrepancies,
        is_valid=is_valid,
    )


def estimate_peak_demand(units_consumed: float) -> float:
    """Estimate peak demand (kW) using monthly consumption heuristic."""
    diversity_factor = 0.35
    peak_kw = (units_consumed / (30 * 24)) / diversity_factor
    return _round2(peak_kw)


def detect_fixed_charge_trap(
    units_consumed: float, sanctioned_load_kw: float
) -> tuple[bool, float, float]:
    """Detect overprovisioned sanctioned load causing annual fixed-charge overpayment."""
    estimated_peak = estimate_peak_demand(units_consumed)
    excess_kw = _round2(sanctioned_load_kw - estimated_peak)

    fires = excess_kw >= FCT_OVERPROVISION_THRESHOLD_KW
    annual_overpayment = _round2(excess_kw * FIXED_CHARGE_RATE * 12)

    return fires, excess_kw, annual_overpayment


def apply_gj_subsidy(
    subtotal_1: float, units_consumed: float, entitlement_units: float
) -> float:
    """Apply Gujarat subsidy cliff logic.

    Returns net payable amount after subsidy rule application.
    """
    if units_consumed <= entitlement_units:
        return 0.0

    if units_consumed <= 200:
        excess_units = units_consumed - entitlement_units
        return _round2(excess_units * 7.18)

    return _round2(subtotal_1)
