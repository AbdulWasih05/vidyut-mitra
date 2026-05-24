"""Frozen demo persona definitions — the test suite's ground truth.

Values match ``docs/briefing_v4.md`` §4 byte-for-byte. Any change that breaks
these assertions is wrong per CLAUDE.md §3 Rule 3, even if the code "looks
cleaner."
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Persona:
    """A verified demo persona with both inputs and expected outputs.

    Expected outputs are asserted by ``tests/test_personas.py`` once the
    analysis modules land (Session 3+).
    """

    # --- Identity ---
    name: str
    location: str

    # --- Inputs (bill fields) ---
    units_consumed: int
    sanctioned_load_kw: float
    billing_period_days: int

    # --- Gruha Jyothi inputs (None for non-GJ) ---
    is_gj_beneficiary: bool
    gj_historical_avg_units: Optional[float]  # FY22-23 monthly avg
    gj_entitlement_units: Optional[float]     # = min(historical_avg + 10, 200)

    # --- Expected tariff outputs (from briefing §4) ---
    expected_subtotal_1: float
    expected_net_bill: float

    # --- Expected analysis outputs ---
    expected_fct_fires: bool
    expected_gj_warning_level: Optional[str]     # "red" / "yellow" / "green" / None
    expected_gj_entitlement_util_pct: Optional[float]  # Level 0 metric


# =============================================================================
# Persona 1 — Nikhil Shetty: Fixed Charge Trap hero
# Briefing §4, primary demo example. 3 kW sanctioned, peak ~1.5 kW.
# =============================================================================

NIKHIL = Persona(
    name="Nikhil Shetty",
    location="Surathkal, Dakshina Kannada",
    units_consumed=210,
    sanctioned_load_kw=3.0,
    billing_period_days=30,
    is_gj_beneficiary=False,
    gj_historical_avg_units=None,
    gj_entitlement_units=None,
    expected_subtotal_1=1943.22,
    expected_net_bill=1943.22,
    expected_fct_fires=True,
    expected_gj_warning_level=None,
    expected_gj_entitlement_util_pct=None,
)

# =============================================================================
# Persona 2 — Sunita Bhat: Solar ROI hero
# Briefing §4. 3 kW sanctioned, 280 units — Fixed Charge Trap also fires
# (peak ≈ 1.95 kW < 3-1=2 kW threshold) per CLAUDE.md §3 Rule 3 table.
# =============================================================================

SUNITA = Persona(
    name="Sunita Bhat",
    location="Chikmagalur town",
    units_consumed=280,
    sanctioned_load_kw=3.0,
    billing_period_days=30,
    is_gj_beneficiary=False,
    gj_historical_avg_units=None,
    gj_entitlement_units=None,
    expected_subtotal_1=2445.96,
    expected_net_bill=2445.96,
    expected_fct_fires=True,
    expected_gj_warning_level=None,
    expected_gj_entitlement_util_pct=None,
)

# =============================================================================
# Persona 3 — Priya Nayak: Gruha Jyothi Visibility hero
# Briefing §4. Entitlement = min(105 + 10, 200) = 115 (NOT 200 — CLAUDE.md
# Rule 1 warns about this copy-paste error). Consumption 110 < 115, so net
# bill is Rs. 0.00 and utilization 110/115 = 95.65% → RED approaching-
# entitlement warning fires (Level 0, threshold 0.90).
# =============================================================================

PRIYA = Persona(
    name="Priya Nayak",
    location="Manipal, Udupi district",
    units_consumed=110,
    sanctioned_load_kw=2.0,
    billing_period_days=30,
    is_gj_beneficiary=True,
    gj_historical_avg_units=105.0,
    gj_entitlement_units=115.0,
    expected_subtotal_1=1080.02,
    expected_net_bill=0.00,
    expected_fct_fires=False,
    expected_gj_warning_level="red",
    expected_gj_entitlement_util_pct=95.65,   # 110/115 × 100 ≈ 95.652
)


# Canonical ordered list for parametrized tests.
ALL_PERSONAS = [NIKHIL, SUNITA, PRIYA]
