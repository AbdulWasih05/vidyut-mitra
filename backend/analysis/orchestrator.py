"""Single entry-point that runs the three analysis modules on one extraction.

Both the WhatsApp webhook (``app.py``) and the web-fallback form
(``web_fallback/upload.py``, Session 7) call ``analyze_bill`` so they share
exactly one code path.

Dispatches:
- ``tariff_engine`` — bill re-computation + Fixed Charge Trap (with the 2-kW
  floor heuristic that makes Nikhil yield briefing §4's Rs. 1,740/year).
- ``subsidy_navigator`` — PMSG + GJ Visibility (+ SWH rebate).
- ``solar_roi`` — sizing + payback + lifetime savings + CO2.

The output dataclass flattens every field the response composer needs, so the
composer has no dependency on any analysis module internals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import ceil
from typing import Any, Optional

from backend.analysis import solar_roi, subsidy_navigator, tariff_engine
from backend.analysis.models import BillExtraction
from backend.analysis.solar_roi import SolarROI
from backend.analysis.subsidy_navigator import GJReport
from backend.config import tariff_constants as tc


# =============================================================================
# Fixed Charge Trap — briefing-aligned report
# =============================================================================


@dataclass(frozen=True)
class FCTReport:
    """Briefing §4-aligned Fixed Charge Trap output.

    Uses ``tariff_engine.estimate_peak_demand`` for the peak estimate but
    applies a 2-kW recommendation floor — this is what produces Nikhil's
    Rs. 1,740/year pitch number (3 sanctioned - 2 recommended = 1 kW × 145
    × 12 = 1,740). Without the floor we'd report Rs. 3,770, which isn't the
    briefing-defended figure.
    """

    fires: bool
    sanctioned_load_kw: float
    estimated_peak_kw: float
    recommended_load_kw: float
    excess_kw: float
    excess_monthly_cost: float
    excess_annual_cost: float
    reduction_process: str = (
        "Reducing your sanctioned load requires a MESCOM application and "
        "possibly a meter change. Contact MESCOM or visit mescom.karnataka.gov.in."
    )


def _compute_fct(
    units_consumed: int,
    sanctioned_load_kw: float,
) -> FCTReport:
    estimated_peak = tariff_engine.estimate_peak_demand(units_consumed)
    # Rule: never recommend a load below the FCT min sanctioned (2 kW) — it's
    # impractical for most households and not an outcome MESCOM approves.
    recommended = max(float(tc.FCT_MIN_SANCTIONED_KW), float(ceil(estimated_peak)))
    excess = round(max(0.0, sanctioned_load_kw - recommended), 2)
    fires = excess >= tc.FCT_BUFFER_KW and sanctioned_load_kw >= tc.FCT_MIN_SANCTIONED_KW
    monthly_excess = round(excess * tc.FIXED_CHARGE_PER_KW_CURRENT, 2)
    annual_excess = round(monthly_excess * 12, 2)
    return FCTReport(
        fires=fires,
        sanctioned_load_kw=sanctioned_load_kw,
        estimated_peak_kw=estimated_peak,
        recommended_load_kw=recommended,
        excess_kw=excess,
        excess_monthly_cost=monthly_excess,
        excess_annual_cost=annual_excess,
    )


# =============================================================================
# AnalysisResult
# =============================================================================


@dataclass(frozen=True)
class AnalysisResult:
    """Everything the response composer + Supabase writer need."""

    extraction: BillExtraction

    # Tariff
    computed_bill: tariff_engine.BillComputation
    net_bill_amount: float
    fct: FCTReport

    # Subsidies
    pm_surya_ghar: dict[str, Any]
    gj_visibility: Optional[GJReport]             # None for non-GJ
    solar_water_heater_rebate: dict[str, Any]

    # Solar
    solar_roi: SolarROI

    # Derived flags the composer uses to pick a template.
    is_gj_beneficiary: bool
    chosen_template: str            # "non_gj" | "gj"

    def to_jsonable(self) -> dict[str, Any]:
        """Turn the result into a JSON-serialisable dict for Supabase JSONB."""
        return {
            "computed_bill": asdict(self.computed_bill),
            "net_bill_amount": self.net_bill_amount,
            "fct": asdict(self.fct),
            "pm_surya_ghar": self.pm_surya_ghar,
            "gj_visibility": (
                _gj_report_to_dict(self.gj_visibility)
                if self.gj_visibility else None
            ),
            "solar_water_heater_rebate": self.solar_water_heater_rebate,
            "solar_roi": asdict(self.solar_roi),
            "is_gj_beneficiary": self.is_gj_beneficiary,
            "chosen_template": self.chosen_template,
        }


def _gj_report_to_dict(r: GJReport) -> dict[str, Any]:
    """GJReport includes GJWarning dataclasses in its warnings list; expand."""
    d = asdict(r)
    # asdict recursively turns dataclasses into dicts so warnings are already
    # plain dicts at this point — no extra work.
    return d


# =============================================================================
# Entry point
# =============================================================================


def analyze_bill(
    extraction: BillExtraction,
    trailing_10m_avg: Optional[float] = None,
) -> AnalysisResult:
    """Run the three analysis modules on one extraction."""
    units = extraction.units_consumed or 0
    load = extraction.sanctioned_load_kw or 0.0
    is_gj = bool(extraction.is_gruha_jyothi_beneficiary)
    entitlement = extraction.entitlement_units

    # --- Tariff ----------------------------------------------------------------
    computed = tariff_engine.compute_bill(
        units_consumed=units,
        sanctioned_load_kw=load,
    )
    if is_gj and entitlement:
        net_bill = tariff_engine.apply_gj_subsidy(
            subtotal_1=computed.subtotal_1,
            units_consumed=units,
            entitlement_units=entitlement,
        )
    else:
        net_bill = computed.subtotal_1

    # --- Fixed Charge Trap (briefing-aligned) ---------------------------------
    fct = _compute_fct(units, load)

    # --- Subsidies -------------------------------------------------------------
    pmsg = subsidy_navigator.check_pm_surya_ghar(
        sanctioned_load_kw=load,
        is_gj_beneficiary=is_gj,
        units_consumed=units,
        tariff_category=extraction.tariff_category or tc.DOMESTIC_TARIFF_CODE,
    )

    gj_report = (
        subsidy_navigator.compute_gj_visibility(
            extraction=extraction,
            trailing_10m_avg=trailing_10m_avg,
        )
        if is_gj
        else None
    )

    swh = subsidy_navigator.check_solar_water_heater_rebate(
        units_consumed=units,
        tariff_category=extraction.tariff_category or tc.DOMESTIC_TARIFF_CODE,
    )

    # --- Solar ROI -------------------------------------------------------------
    # For Nikhil/Sunita (3 kW sanctioned) we recommend 3 kW to maximise PMSG.
    system_kw = solar_roi.size_system(
        annual_consumption_kwh=units * 12,
        sanctioned_load_kw=load,
    )
    roi = solar_roi.compute_roi(
        system_kw=system_kw,
        monthly_consumption=units,
        is_gj_beneficiary=is_gj,
        entitlement_units=entitlement,
    )

    return AnalysisResult(
        extraction=extraction,
        computed_bill=computed,
        net_bill_amount=net_bill,
        fct=fct,
        pm_surya_ghar=pmsg,
        gj_visibility=gj_report,
        solar_water_heater_rebate=swh,
        solar_roi=roi,
        is_gj_beneficiary=is_gj,
        chosen_template="gj" if is_gj else "non_gj",
    )
