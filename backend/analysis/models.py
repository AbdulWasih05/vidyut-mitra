"""Typed dataclasses shared across extraction and analysis modules.

Contract sources:
- ``BillExtraction`` fields: PRD v3 §4.1.
- ``ExtractionStatus`` values: CLAUDE.md §3 Rule 5 (pre_april_2025) and
  tech spec §4.3 (retry/terminal semantics).

Frozen + type-hinted for safety. Downstream modules (analysis/tariff_engine,
analysis/subsidy_navigator, analysis/solar_roi) will consume ``BillExtraction``
as input.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ExtractionStatus(str, Enum):
    """Terminal status of a ``run_extraction`` call.

    ``ok`` and ``failed`` distinguish first-pass success from post-retry
    failure. ``pre_april_2025`` and ``not_mescom`` are terminal R1/R2
    aborts (no retry — the photo itself is unsuitable). ``retry_needed``
    is an internal state used by the pipeline between the first extract and
    the retry; it is not returned as a terminal value.
    """

    OK = "ok"
    RETRY_NEEDED = "retry_needed"
    PRE_APRIL_2025 = "pre_april_2025"
    NOT_MESCOM = "not_mescom"
    FAILED = "failed"


@dataclass(frozen=True)
class BillExtraction:
    """Validated extraction of one MESCOM bill. Fields per PRD §4.1.

    All fields default to ``None`` for compactness when constructing from
    partial data. The validator asserts non-null on critical fields (R3-R8)
    before the analysis layer sees this object.
    """

    # --- Identification ---
    is_mescom_bill: bool = False
    extraction_confidence: Optional[float] = None

    # --- Consumer info ---
    consumer_name: Optional[str] = None
    rr_number: Optional[str] = None
    tariff_category: Optional[str] = None   # normalised to "LT-1"

    # --- Billing period ---
    billing_period_start: Optional[str] = None   # ISO YYYY-MM-DD
    billing_period_end: Optional[str] = None     # ISO YYYY-MM-DD
    billing_period_days: Optional[int] = None

    # --- Consumption & load ---
    sanctioned_load_kw: Optional[float] = None
    previous_reading: Optional[int] = None
    current_reading: Optional[int] = None
    units_consumed: Optional[int] = None

    # --- Pre-subsidy bill components (Sub-Total-1) ---
    energy_charges: Optional[float] = None
    fixed_charges: Optional[float] = None
    pg_surcharge: Optional[float] = None
    electricity_tax: Optional[float] = None
    fppca: Optional[float] = None
    other_charges: Optional[float] = None
    subtotal_1_before_subsidy: Optional[float] = None

    # --- Gruha Jyothi (nullable for non-GJ) ---
    is_gruha_jyothi_beneficiary: bool = False
    gjs_registration_date: Optional[str] = None
    historical_avg_baseline: Optional[float] = None
    entitlement_units: Optional[float] = None
    units_eligible_for_subsidy: Optional[float] = None
    units_chargeable: Optional[float] = None
    gruha_jyothi_subsidy_amount: Optional[float] = None

    # --- Final bill ---
    net_bill_amount: Optional[float] = None

    # --- Metadata ---
    due_date: Optional[str] = None
    arrears: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BillExtraction":
        """Build from a Gemini JSON response, tolerating unknown fields."""
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        filtered.setdefault("is_mescom_bill", False)
        filtered.setdefault("is_gruha_jyothi_beneficiary", False)
        return cls(**filtered)


@dataclass(frozen=True)
class ExtractionResult:
    """The single return type of ``extraction.pipeline.run_extraction``.

    Callers should inspect ``status`` first. ``extraction`` may be ``None``
    on terminal R1/R2 aborts or hard failures. ``raw`` is kept for debugging
    and the admin dashboard; do NOT persist the raw image — only the parsed
    fields end up in Supabase per CLAUDE.md §3 Rule 2.
    """

    status: ExtractionStatus
    extraction: Optional[BillExtraction] = None
    validation_issues: list[str] = field(default_factory=list)
    raw: Optional[dict[str, Any]] = None
    retries_used: int = 0
