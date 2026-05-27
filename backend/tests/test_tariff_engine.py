"""Tests for deterministic tariff engine."""

from backend.analysis.tariff_engine import (
    BillExtraction,
    apply_gj_subsidy,
    compute_bill,
    detect_fixed_charge_trap,
    validate_bill,
)


def test_compute_bill_known_values() -> None:
    result = compute_bill(units_consumed=100, sanctioned_load_kw=2)

    assert result.energy_charges == 580.00
    assert result.fixed_charges == 290.00
    assert result.pg_surcharge == 36.00
    assert result.fppca == 50.00
    assert result.electricity_tax == 52.20
    assert result.subtotal_1 == 1008.20


def test_validate_bill_tolerance_rule_accepts_discrepancies_within_five() -> None:
    extraction = BillExtraction(
        units_consumed=100,
        sanctioned_load_kw=2,
        energy_charges=584.50,
        fixed_charges=286.00,
        pg_surcharge=34.00,
        electricity_tax=54.00,
        fppca=47.00,
    )

    result = validate_bill(extraction)

    assert result.is_valid is True
    assert all(diff <= 5.0 for diff in result.discrepancies.values())


def test_validate_bill_tolerance_rule_rejects_large_discrepancy() -> None:
    extraction = BillExtraction(
        units_consumed=100,
        sanctioned_load_kw=2,
        energy_charges=580.00,
        fixed_charges=260.00,
        pg_surcharge=36.00,
        electricity_tax=52.20,
        fppca=50.00,
    )

    result = validate_bill(extraction)

    assert result.discrepancies["fixed_charges"] == 30.00
    assert result.is_valid is False


def test_detect_fixed_charge_trap_should_fire_for_units_280_load_3() -> None:
    fires, excess_kw, annual_overpayment = detect_fixed_charge_trap(
        units_consumed=280,
        sanctioned_load_kw=3,
    )

    assert fires is True
    assert excess_kw == 1.89
    assert annual_overpayment == 3288.6


def test_apply_gj_subsidy_full_subsidy_when_units_within_entitlement() -> None:
    net = apply_gj_subsidy(subtotal_1=1200.0, units_consumed=50, entitlement_units=63)
    assert net == 0.0


def test_apply_gj_subsidy_rehena_case() -> None:
    net = apply_gj_subsidy(subtotal_1=9999.0, units_consumed=170, entitlement_units=123)
    assert net == 337.46


def test_apply_gj_subsidy_koppala_case_full_bill_when_units_above_200() -> None:
    bill = compute_bill(units_consumed=390, sanctioned_load_kw=2)
    net = apply_gj_subsidy(
        subtotal_1=bill.subtotal_1,
        units_consumed=390,
        entitlement_units=63,
    )
    assert net == bill.subtotal_1
