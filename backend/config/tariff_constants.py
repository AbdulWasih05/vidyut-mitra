"""Verified KERC, MNRE, CEA, and Karnataka-state constants for VidyutMitra.

Every number here traces back to a primary source cited in the comments and in
``docs/briefing_v4.md`` §3-4. Do NOT add a constant without a source. Do NOT
change a value without verifying against the conflict-resolution order:
briefing_v4 > tech_spec_v1_1 > prd_v3.

Tests in ``tests/test_tariff_constants.py`` enforce these values.
"""
from __future__ import annotations


# =============================================================================
# KERC LT-1 Domestic tariff
# Source: KERC Tariff Order 2025, Order Dated 27-Mar-2025, Annexure 2.
# Single-slab structure confirmed by Clauses 19 and 30 (slabs abolished).
# =============================================================================

# Current FY. Demo bills are March 2026, so FY 2025-26 rates apply.
CURRENT_FY = "2025-26"

# Energy charge per unit (Rs./kWh), flat — NO slabs.
# Briefing §3 wins on FY 2026-27 (Rs. 5.90 vs tech-spec's 5.80); briefing > tech_spec.
ENERGY_CHARGE_PER_UNIT = {
    "2025-26": 5.80,
    "2026-27": 5.90,
    "2027-28": 5.75,
}
ENERGY_CHARGE_FLAT_RATE = ENERGY_CHARGE_PER_UNIT[CURRENT_FY]  # Rs. 5.80/unit

# Fixed charge per kW of sanctioned load, per month (Rs.).
FIXED_CHARGE_PER_KW = {
    "2025-26": 145,
    "2026-27": 150,
    "2027-28": 160,
}
FIXED_CHARGE_PER_KW_CURRENT = FIXED_CHARGE_PER_KW[CURRENT_FY]  # Rs. 145/kW/month

# Electricity tax as a fraction of energy charges (Government of Karnataka).
ELECTRICITY_TAX_RATE = 0.09  # 9 %

# P&G surcharge (KPTCL/ESCOM Pension & Gratuity), per unit.
# Source: KERC Separate Order, 18-Mar-2025. GJ beneficiaries exempt.
PG_SURCHARGE_PER_UNIT = 0.36  # Rs./unit, FY 2025-26

# Fuel & Power Purchase Cost Adjustment — varies monthly; demo placeholder.
FPPCA_PLACEHOLDER_RATE = 0.50  # Rs./unit

# Solar rooftop rebate on fixed charge — LT-1 Note (b), capped at 10 kW.
SOLAR_ROOFTOP_REBATE_PER_KW = 25  # Rs./kW/month
SOLAR_ROOFTOP_REBATE_CAP_KW = 10

# Tariff code on bills (MESCOM sometimes prints "2LT1"; normalize to "LT-1").
DOMESTIC_TARIFF_CODE = "LT-1"


# =============================================================================
# KERC Solar Tariff Order — net-metering export rates under PM Surya Ghar
# Source: KERC Solar Tariff Order, effective 01-Jul-2025 through 30-Jun-2026.
# =============================================================================

SOLAR_EXPORT_RATE_1_2_KW = 2.30    # Rs./unit, 1-2 kW system
SOLAR_EXPORT_RATE_2_3_KW = 2.48    # Rs./unit, 2-3 kW system (Nikhil, Sunita)
SOLAR_EXPORT_RATE_ABOVE_3_KW = 2.93  # Rs./unit, >3 kW system

# Non-subsidized domestic (without PMSG central subsidy).
SOLAR_EXPORT_RATE_NONSUB_1_10_KW = 3.86  # Rs./unit


# =============================================================================
# PM Surya Ghar: Muft Bijli Yojana — central subsidy (MNRE)
# Tiered structure, capped at Rs. 78,000 for 3+ kW.
# =============================================================================

PMSG_SUBSIDY_FIRST_2_KW_PER_KW = 30_000  # Rs./kW for first 2 kW
PMSG_SUBSIDY_3RD_KW = 18_000              # Rs. flat for 3rd kW
PMSG_SUBSIDY_CAP = 78_000                 # Rs., maximum regardless of size


# =============================================================================
# Solar ROI — Mangalore-specific constants
# Sources: Global Solar Atlas (12.87°N 74.88°E), 2026 MNRE vendor benchmarks.
# =============================================================================

SOLAR_IRRADIANCE_MANGALORE = 5.55  # kWh/m²/day (state avg; Mangalore seasonal 3.89–6.16)
PERFORMANCE_RATIO = 0.69           # Coastal-humidity adjusted
SPECIFIC_YIELD_KWP_YEAR = 1_400    # kWh/kWp/year (industry consensus)

ANNUAL_GENERATION_3KW = 4_200       # kWh/year for 3 kW system
SYSTEM_COST_PER_KW = 55_000         # Rs./kW, 2026 Karnataka market avg

# Derived net consumer cost for a 3 kW system with PMSG.
NET_COST_3KW_AFTER_PMSG = 3 * SYSTEM_COST_PER_KW - PMSG_SUBSIDY_CAP  # Rs. 87,000

# 25-year lifetime deductions (tech spec §8.5 + briefing §4 worked example).
# Per-kW degradation is calibrated so Nikhil's 3 kW yields briefing's
# Rs. 36,000 cumulative degradation figure.
LIFETIME_YEARS = 25
DEGRADATION_LIFETIME_COST_PER_KW = 12_000  # Rs.; 3 kW → Rs. 36,000
INVERTER_REPLACEMENT_COST = 25_000  # Rs., flat, one replacement at yr 12-15
ANNUAL_TARIFF_ESCALATION = 0.03     # 3% Karnataka historical trend


# =============================================================================
# Environmental — grid emission factor and tree equivalence
# Source: CEA CO2 Baseline Database Version 21.0, December 2025
#         (FY 2024-25 weighted average including renewables).
# Supersedes CEA v20.0's 0.727 kg/kWh and the older ~0.82 figure from
# pre-2024 sources. See CLAUDE.md §3 Rule 1.
# =============================================================================

GRID_EMISSION_FACTOR_KG_PER_KWH = 0.710  # kg CO2/kWh — CEA v21.0, Dec 2025

# Widely-cited urban-tree absorption rate for public communication.
TREE_ABSORPTION_KG_PER_YEAR = 30  # kg CO2/tree/year

# Derived for 3 kW Mangalore system.
ANNUAL_CO2_OFFSET_3KW_TONNES = (
    ANNUAL_GENERATION_3KW * GRID_EMISSION_FACTOR_KG_PER_KWH / 1_000
)  # ≈ 2.982 tonnes/year — rounds to 2.98 in pitch
TREES_EQUIVALENT_3KW = round(
    ANNUAL_GENERATION_3KW * GRID_EMISSION_FACTOR_KG_PER_KWH / TREE_ABSORPTION_KG_PER_YEAR
)  # ≈ 99 — round to "~100 trees/year"


# =============================================================================
# Gruha Jyothi (Karnataka state subsidy)
# Source: Karnataka Cabinet Order, 18-Jan-2024 (switched from avg×1.10 to
#         avg+10 flat). Enforcement clarified by CESC MD K.M. Munigopalraju,
#         Star of Mysore, 23-Nov-2025.
# =============================================================================

GJ_ENTITLEMENT_FLAT_BONUS_UNITS = 10  # Added to FY22-23 historical monthly avg
GJ_ENTITLEMENT_CAP_UNITS = 200        # Upper bound for entitlement formula
GJ_MONTHLY_HARD_CLIFF_UNITS = 200     # Crossing loses entire subsidy for the month
GJ_ELIGIBILITY_ROLLING_MONTHS = 10    # 10-month rolling average review window

# Cliff warning thresholds. See CLAUDE.md §3 Rule 1 table.
# Level 0 — approaching personal entitlement (proactive).
GJ_APPROACHING_YELLOW_THRESHOLD = 0.75
GJ_APPROACHING_RED_THRESHOLD = 0.90

# Level 2 — monthly hard cliff (200 units).
GJ_HARD_CAP_YELLOW_THRESHOLD = 0.80
GJ_HARD_CAP_RED_THRESHOLD = 0.95

# Level 3 — eligibility at risk (10-month rolling avg / 200).
GJ_ELIGIBILITY_YELLOW_THRESHOLD = 0.80
GJ_ELIGIBILITY_RED_THRESHOLD = 0.95


# =============================================================================
# Fixed Charge Trap detection
# Logic spec: tech_spec_v1_1 §6.
# =============================================================================

# Heuristic to estimate peak demand from monthly aggregate.
PEAK_DEMAND_ACTIVE_HOURS_PER_DAY = 8
PEAK_TO_AVERAGE_FACTOR = 1.67

# Trap fires only when BOTH conditions hold:
FCT_BUFFER_KW = 1.0              # peak must be < (sanctioned - FCT_BUFFER_KW)
FCT_MIN_SANCTIONED_KW = 2.0      # don't recommend sub-2 kW loads


# =============================================================================
# MESCOM scale (for pitch + at-scale framing)
# Source: MESCOM Annual Report 2023-24.
# =============================================================================

MESCOM_CONSUMER_COUNT = 22_60_000   # 22.6 lakh consumers
FCT_ASSUMED_OVERPROVISION_FRACTION = 0.10  # conservative for the pitch


# =============================================================================
# Climate context — for the Sustainable Development track reframe
# Sources: CEIC India (avg passenger car emissions ~192 g/km), IEA 2024
# country report (avg Indian car ~4.6 tonnes CO2/yr at ~24,000 km/yr).
# =============================================================================

AVG_INDIAN_CAR_EMISSIONS_KG_PER_KM = 0.192   # kg CO2/km — CEIC India 2024
AVG_INDIAN_CAR_ANNUAL_CO2_TONNES = 4.6        # tonnes CO2/car/year — IEA 2024


# =============================================================================
# Date gates
# Source: CLAUDE.md §3 Rule 5.
# =============================================================================

# Bills with billing_period_end before this date are declined (pre-KERC 2025).
# Name used by extraction/schema_validator.py R2 rule.
EARLIEST_ACCEPTED_BILL_DATE = "2025-04-01"
