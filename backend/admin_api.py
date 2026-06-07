"""Admin JSON API for the Next.js dashboard (``vidyut-dashboard/``).

Three read-only endpoints:

- ``GET /admin/metrics`` — aggregate rollups (consented users, bill count,
  avg bill, FCT flags, GJ subsidy total, CO2 footprint, cliff counts).
- ``GET /admin/activity`` — recent 10 bills, anonymised. NO phone_number,
  NO consumer_name — we surface a synthetic ``log_id`` instead.
- ``GET /admin/trend`` — last-8 daily buckets of avg bill + estimated solar
  equivalent for the Current-vs-Solar line chart on the dashboard.

Auth: every request must present ``Authorization: Bearer <ADMIN_PASSWORD>``.
If the header is missing or wrong, returns 401 with ``{"error": "..."}``.

CORS: allows ``http://localhost:3000`` (the Next dev server) by default.
For production, set ``ADMIN_DASHBOARD_ORIGIN`` to the deployed URL.

DPDPA (CLAUDE.md §3 Rule 2 + tech spec §9.5): every query here is COUNT /
AVG / SUM / anonymised-projection. No route returns ``phone_number``,
``consumer_name``, or ``rr_number``. Code review enforces this — if you
find yourself typing ``phone_number`` in a select, stop.
"""
from __future__ import annotations

import logging
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any

from flask import Blueprint, jsonify, request

from backend.config import tariff_constants as tc

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin_api", __name__, url_prefix="/admin")


# =============================================================================
# Auth + CORS
# =============================================================================


def _allowed_origin() -> str:
    # Accept both common Next.js dev ports by default. ``ADMIN_DASHBOARD_ORIGIN``
    # can override with a comma-separated allowlist (single value also works).
    configured = os.environ.get("ADMIN_DASHBOARD_ORIGIN", "").strip()
    if not configured:
        return "http://localhost:3000,http://localhost:3001"
    return configured


def _resolve_allowed_origin(request_origin: str | None) -> str:
    allowed = {
        origin.strip()
        for origin in _allowed_origin().split(",")
        if origin.strip()
    }
    # Same-origin/non-browser calls won't send Origin; keep a deterministic
    # default so tools and curl still get a valid CORS header.
    if not request_origin:
        return "http://localhost:3000" if "http://localhost:3000" in allowed else next(iter(allowed), "http://localhost:3000")
    return request_origin if request_origin in allowed else "null"


def _apply_cors(response):
    response.headers["Access-Control-Allow-Origin"] = _resolve_allowed_origin(
        request.headers.get("Origin")
    )
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Vary"] = "Origin"
    return response


@admin_bp.after_request
def _after(response):
    return _apply_cors(response)


def _require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        # OPTIONS preflight — let it through for CORS.
        if request.method == "OPTIONS":
            return ("", 204)

        expected = os.environ.get("ADMIN_PASSWORD")
        if not expected:
            return jsonify(error="ADMIN_PASSWORD not configured on server"), 500

        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="missing Authorization: Bearer <password>"), 401

        token = header.removeprefix("Bearer ").strip()
        if token != expected:
            return jsonify(error="invalid admin token"), 401

        return view(*args, **kwargs)
    return wrapped


# =============================================================================
# Supabase query helpers — aggregate only
# =============================================================================


def _client():
    from backend.db import supabase_client
    return supabase_client.init_client()


def _fetch_all_bills() -> list[dict]:
    """Pull every bill we need for the aggregate views.

    Explicitly does NOT select phone_number / consumer_name / rr_number.
    The ``bills`` table already has no bill_image column (DPDPA), so the
    set of columns requested here is the full non-PII surface.
    """
    c = _client()
    resp = (
        c.table("bills")
        .select(
            "id,created_at,billing_period_end,units_consumed,"
            "sanctioned_load_kw,subtotal_1,net_bill_amount,"
            "is_gj_beneficiary,entitlement_units,gj_subsidy_amount,"
            "analysis_result"
        )
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    return resp.data or []


def _fetch_user_counts() -> dict:
    c = _client()
    total = c.table("users").select("id", count="exact").execute()
    consented = (
        c.table("users")
        .select("id", count="exact")
        .eq("consent_given", True)
        .execute()
    )
    return {
        "total_users": total.count or 0,
        "consented_users": consented.count or 0,
    }


# =============================================================================
# Routes
# =============================================================================


@admin_bp.route("/metrics", methods=["GET", "OPTIONS"])
@_require_admin
def metrics():
    """Headline aggregate metrics for the top of the dashboard."""
    try:
        bills = _fetch_all_bills()
        users = _fetch_user_counts()
    except Exception as exc:  # noqa: BLE001
        logger.exception("metrics query failed")
        return jsonify(error=f"supabase query failed: {type(exc).__name__}"), 500

    total_bills = len(bills)
    gj_bills = sum(1 for b in bills if b.get("is_gj_beneficiary"))
    fct_fires = sum(1 for b in bills if _fct_fires(b))
    pmsg_eligible = sum(1 for b in bills if _pmsg_eligible(b))

    # Three headline solar metrics scoped to the SAME cohort: non-GJ
    # households. Mixing GJ (Rs. 0 net bills) into the "avg bill" baseline
    # while computing savings only from non-GJ bills gives negative deltas
    # that clamp to 0 — the user-visible "solar-replaced bill shows 0" bug.
    non_gj = [b for b in bills if not b.get("is_gj_beneficiary")]
    non_gj_bills_net = [b.get("net_bill_amount") or 0 for b in non_gj]
    avg_non_gj_bill = (sum(non_gj_bills_net) / len(non_gj)) if non_gj else 0

    per_bill_solar_replaced = [
        max(
            0,
            (b.get("net_bill_amount") or 0)
            - (((b.get("analysis_result") or {}).get("solar_roi") or {}).get(
                "total_monthly_benefit"
            ) or 0),
        )
        for b in non_gj
    ]
    avg_solar_bill = (
        sum(per_bill_solar_replaced) / len(per_bill_solar_replaced)
        if per_bill_solar_replaced else 0
    )
    avg_monthly_solar_benefit = avg_non_gj_bill - avg_solar_bill

    # Global avg bill across ALL bills — shown lower in the second row, not
    # in the solar comparison triplet. Kept for dashboard context.
    net_bills = [b.get("net_bill_amount") or 0 for b in bills]
    avg_bill = (sum(net_bills) / total_bills) if total_bills else 0

    # Annual CO2 footprint.
    total_annual_kwh = sum((b.get("units_consumed") or 0) * 12 for b in bills)
    total_annual_co2_tonnes = total_annual_kwh * tc.GRID_EMISSION_FACTOR_KG_PER_KWH / 1_000

    # Cliff counters.
    cliff_approaching = sum(
        1 for b in bills
        if b.get("is_gj_beneficiary")
        and 160 <= (b.get("units_consumed") or 0) <= 199
    )
    cliff_crossed = sum(
        1 for b in bills
        if b.get("is_gj_beneficiary")
        and (b.get("units_consumed") or 0) > 200
    )

    # GJ subsidy visible — "government paid on your behalf" total.
    gj_subsidy_total = sum(
        (b.get("gj_subsidy_amount") or 0)
        for b in bills
        if b.get("is_gj_beneficiary")
    )

    return jsonify({
        "consented_users": users["consented_users"],
        "total_users": users["total_users"],
        "total_bills": total_bills,
        "gj_bills": gj_bills,
        "fct_flags_fired": fct_fires,
        "pmsg_eligible_count": pmsg_eligible,
        "avg_bill_rupees": round(avg_bill, 0),              # all bills, mixed
        "avg_non_gj_bill_rupees": round(avg_non_gj_bill, 0),  # solar-eligible cohort baseline
        "avg_solar_bill_rupees": round(avg_solar_bill, 0),    # same cohort, after 3 kW solar
        "avg_monthly_solar_savings_rupees": round(avg_monthly_solar_benefit, 0),
        "annual_co2_footprint_tonnes": round(total_annual_co2_tonnes, 1),
        "cliff_approaching_count": cliff_approaching,
        "cliff_crossed_count": cliff_crossed,
        "gj_subsidy_visible_rupees": round(gj_subsidy_total, 0),
    })


@admin_bp.route("/activity", methods=["GET", "OPTIONS"])
@_require_admin
def activity():
    """Last N bills, anonymised. NO phone_number / consumer_name ever.

    Synthetic ``log_id`` generated from the bill's UUID so ops can correlate
    via the bills table's primary key if needed, but the dashboard itself
    shows no PII.
    """
    try:
        limit = int(request.args.get("limit", "10"))
    except ValueError:
        limit = 10
    limit = max(1, min(100, limit))

    try:
        bills = _fetch_all_bills()
    except Exception as exc:  # noqa: BLE001
        logger.exception("activity query failed")
        return jsonify(error=f"supabase query failed: {type(exc).__name__}"), 500

    rows = []
    for b in bills[:limit]:
        bill_id = b.get("id") or ""
        log_id = f"LOG-{bill_id[:8].upper()}" if bill_id else "LOG-??????"
        units = b.get("units_consumed") or 0
        is_gj = bool(b.get("is_gj_beneficiary"))
        fct = _fct_fires(b)

        if is_gj and units > 200:
            status, source = "Cliff Crossed", "Gruha Jyothi"
        elif is_gj and 160 <= units <= 199:
            status, source = "Approaching", "Gruha Jyothi"
        elif is_gj:
            status, source = "Subsidised", "Gruha Jyothi"
        elif fct:
            status, source = "FCT Flagged", "Tariff Engine"
        else:
            status, source = "Analysed", "WhatsApp Sandbox"

        rows.append({
            "log_id": log_id,
            "units_consumed": units,
            "sanctioned_load_kw": b.get("sanctioned_load_kw"),
            "is_gj": is_gj,
            "net_bill_rupees": round(b.get("net_bill_amount") or 0, 0),
            "status": status,
            "source": source,
            "time": _short_time(b.get("created_at")),
        })

    return jsonify({"rows": rows})


@admin_bp.route("/trend", methods=["GET", "OPTIONS"])
@_require_admin
def trend():
    """8-bucket daily trend of avg bill and estimated solar-replaced bill.

    Bucket = 1 day back from today. Last bucket is today.
    """
    try:
        bills = _fetch_all_bills()
    except Exception as exc:  # noqa: BLE001
        logger.exception("trend query failed")
        return jsonify(error=f"supabase query failed: {type(exc).__name__}"), 500

    now = datetime.now(timezone.utc)
    buckets: list[dict] = []
    for day_offset in range(7, -1, -1):
        day_start = (now - timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        day_end = day_start + timedelta(days=1)
        day_bills = [
            b for b in bills
            if b.get("created_at")
            and day_start <= _parse_iso(b["created_at"]) < day_end
        ]
        if day_bills:
            avg_bill = sum((b.get("net_bill_amount") or 0) for b in day_bills) / len(day_bills)
            avg_solar_benefit = _avg_solar_benefit(day_bills)
            avg_solar_bill = max(0, avg_bill - avg_solar_benefit)
        else:
            avg_bill = 0
            avg_solar_bill = 0
        buckets.append({
            "date": day_start.date().isoformat(),
            "avg_bill": round(avg_bill, 0),
            "avg_solar_bill": round(avg_solar_bill, 0),
        })

    return jsonify({"buckets": buckets})


# =============================================================================
# Helpers
# =============================================================================


def _fct_fires(bill: dict) -> bool:
    ar = bill.get("analysis_result") or {}
    return bool((ar.get("fct") or {}).get("fires"))


def _pmsg_eligible(bill: dict) -> bool:
    ar = bill.get("analysis_result") or {}
    return bool((ar.get("pm_surya_ghar") or {}).get("eligible"))


def _avg_solar_benefit(bills: list[dict]) -> float:
    benefits = [
        ((b.get("analysis_result") or {}).get("solar_roi") or {}).get("total_monthly_benefit") or 0
        for b in bills
        if not b.get("is_gj_beneficiary")
    ]
    return (sum(benefits) / len(benefits)) if benefits else 0


def _parse_iso(ts: str) -> datetime:
    # Supabase timestamps come back with timezone offsets; fromisoformat
    # handles the standard ones in Python 3.11+.
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _short_time(ts: str | None) -> str:
    if not ts:
        return "—"
    return ts.replace("T", " ")[:16]
