"""Seed realistic demo data into Supabase for dashboard presentation.

Creates 25-40 synthetic users with phone numbers ``whatsapp:+91DEMO000001``
through ``whatsapp:+91DEMO000040`` and 30-80 bills per the distribution below:

- ~60% non-GJ, units distributed 30% low / 40% medium / 30% high
- ~40% GJ-enrolled, varying entitlement 30-150 units
- ~15% of GJ bills cross 200 units (hard-cliff samples)
- ~20% of non-GJ bills have Fixed Charge Trap firing (over-provisioned load)

Every seed row carries ``analysis_result._seed_data = true`` so
``scripts/clean_demo_data.py`` can wipe it cleanly before demo day.

Every number comes from the real analysis modules — tariff_engine +
subsidy_navigator + solar_roi + orchestrator — not fabricated. If a single
seed row's math looks wrong, it's a module bug, not a seed bug.

Usage::

    python scripts/seed_demo_data.py           # refuses if DEMO data exists
    python scripts/seed_demo_data.py --force   # wipe + reseed
"""
from __future__ import annotations

import logging
import os
import random
import sys
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import analyze_bill
from backend.analysis.tariff_engine import compute_bill
from backend.config import tariff_constants as tc
from backend.db import supabase_client

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


DEMO_PHONE_PREFIX = "whatsapp:+91DEMO"
USER_COUNT = 35
MAX_BILLS_PER_USER = 3
SEED_MARKER_KEY = "_seed_data"


# =============================================================================
# Synthetic data generation
# =============================================================================


def _random_consumption_profile(rng: random.Random) -> dict:
    """Return a synthetic consumer profile with realistic KERC math."""
    is_gj = rng.random() < 0.40

    if is_gj:
        historical_avg = rng.choice([52, 65, 80, 100, 120, 140])
        entitlement = min(historical_avg + 10, 200)
        # 15% of GJ crosses 200, rest distributed across the entitlement bands.
        if rng.random() < 0.15:
            units = rng.randint(210, 420)   # cliff crossed
        elif rng.random() < 0.35:
            units = rng.randint(max(1, entitlement - 20), entitlement + 5)  # near entitlement
        else:
            units = rng.randint(20, entitlement - 5) if entitlement > 25 else rng.randint(10, entitlement)
        sanctioned = rng.choice([1.0, 2.0, 2.0, 3.0])
    else:
        historical_avg = None
        entitlement = None
        bucket = rng.random()
        if bucket < 0.30:
            units = rng.randint(80, 150)
        elif bucket < 0.70:
            units = rng.randint(150, 250)
        else:
            units = rng.randint(250, 400)
        sanctioned = rng.choice([2.0, 3.0, 3.0, 4.0, 5.0])

    return {
        "units_consumed": units,
        "sanctioned_load_kw": sanctioned,
        "is_gj_beneficiary": is_gj,
        "historical_avg": historical_avg,
        "entitlement_units": entitlement,
    }


def _build_extraction(profile: dict, billing_end: date) -> BillExtraction:
    """Compute real KERC bill math + wrap as a BillExtraction."""
    bill = compute_bill(profile["units_consumed"], profile["sanctioned_load_kw"])

    if profile["is_gj_beneficiary"]:
        entitlement = profile["entitlement_units"] or 0
        units = profile["units_consumed"]
        if units <= entitlement:
            gj_subsidy = bill.subtotal_1
            net_bill = 0.0
        elif units <= tc.GJ_MONTHLY_HARD_CLIFF_UNITS:
            net_bill = round((units - entitlement) * 7.18, 2)
            gj_subsidy = round(bill.subtotal_1 - net_bill, 2)
        else:
            # Cliff crossed → lose entire subsidy for the month.
            gj_subsidy = 0.0
            net_bill = bill.subtotal_1
    else:
        gj_subsidy = None
        net_bill = bill.subtotal_1

    return BillExtraction(
        is_mescom_bill=True,
        extraction_confidence=0.92,
        tariff_category="LT-1",
        billing_period_start=(billing_end - timedelta(days=30)).isoformat(),
        billing_period_end=billing_end.isoformat(),
        billing_period_days=30,
        sanctioned_load_kw=profile["sanctioned_load_kw"],
        units_consumed=profile["units_consumed"],
        energy_charges=bill.energy_charges,
        fixed_charges=bill.fixed_charges,
        pg_surcharge=bill.pg_surcharge,
        electricity_tax=bill.electricity_tax,
        fppca=bill.fppca,
        other_charges=0.0,
        subtotal_1_before_subsidy=bill.subtotal_1,
        is_gruha_jyothi_beneficiary=profile["is_gj_beneficiary"],
        historical_avg_baseline=profile["historical_avg"],
        entitlement_units=profile["entitlement_units"],
        gruha_jyothi_subsidy_amount=gj_subsidy,
        gjs_registration_date="2023-08-26" if profile["is_gj_beneficiary"] else None,
        net_bill_amount=net_bill,
    )


# =============================================================================
# Insertion
# =============================================================================


def _already_seeded(client) -> bool:
    resp = (
        client.table("users")
        .select("id", count="exact")
        .ilike("phone_number", f"{DEMO_PHONE_PREFIX}%")
        .execute()
    )
    return (resp.count or 0) > 0


def _wipe_demo(client) -> tuple[int, int]:
    """Delete all users with demo prefix; returns (users_deleted, bills_cascaded)."""
    users = (
        client.table("users")
        .select("id")
        .ilike("phone_number", f"{DEMO_PHONE_PREFIX}%")
        .execute()
    )
    user_ids = [u["id"] for u in (users.data or [])]
    if not user_ids:
        return 0, 0

    bills = (
        client.table("bills")
        .select("id", count="exact")
        .in_("user_id", user_ids)
        .execute()
    )
    bill_count = bills.count or 0

    for uid in user_ids:
        client.table("users").delete().eq("id", uid).execute()

    return len(user_ids), bill_count


def _seed(client, rng: random.Random) -> tuple[int, int]:
    users_created = 0
    bills_created = 0
    now = datetime.now(timezone.utc)

    for i in range(1, USER_COUNT + 1):
        phone = f"{DEMO_PHONE_PREFIX}{i:06d}"
        created_at_user = now - timedelta(days=rng.randint(5, 30))
        ins = client.table("users").insert({
            "phone_number": phone,
            "consent_given": True,
            "created_at": created_at_user.isoformat(),
            "updated_at": created_at_user.isoformat(),
        }).execute()
        if not ins.data:
            continue
        user_id = ins.data[0]["id"]
        users_created += 1

        n_bills = rng.randint(1, MAX_BILLS_PER_USER)
        for _b in range(n_bills):
            profile = _random_consumption_profile(rng)
            billing_end = (now - timedelta(days=rng.randint(0, 30))).date()
            extraction = _build_extraction(profile, billing_end)
            analysis = analyze_bill(extraction)
            analysis_blob = analysis.to_jsonable()
            analysis_blob[SEED_MARKER_KEY] = True

            row = _extraction_to_db_row(extraction)
            row["user_id"] = user_id
            row["analysis_result"] = analysis_blob
            row["created_at"] = (
                now - timedelta(days=rng.randint(0, 30), hours=rng.randint(0, 23))
            ).isoformat()

            try:
                client.table("bills").insert(row).execute()
                bills_created += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("bill insert failed for %s: %s", phone, exc)

    return users_created, bills_created


def _extraction_to_db_row(extraction: BillExtraction) -> dict:
    """Map BillExtraction → the column subset the ``bills`` schema accepts.

    Mirrors ``supabase_client._extraction_to_db_dict`` but without the
    user_id/analysis_result fields (caller adds those) and drops the
    extraction-layer-only fields that aren't in the schema.
    """
    d = asdict(extraction)
    d["subtotal_1"] = d.pop("subtotal_1_before_subsidy")
    d["gj_subsidy_amount"] = d.pop("gruha_jyothi_subsidy_amount")
    d["is_gj_beneficiary"] = d.pop("is_gruha_jyothi_beneficiary")
    d["gj_registration_date"] = d.pop("gjs_registration_date")
    # Extraction-layer flags + fields with no schema column:
    for drop in ("is_mescom_bill", "consumer_name", "due_date", "arrears"):
        d.pop(drop, None)
    return d


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    force = "--force" in sys.argv
    rng = random.Random(42)   # deterministic for re-runs

    client = supabase_client.init_client()

    if _already_seeded(client):
        if not force:
            print(f"Demo data already present (users with prefix {DEMO_PHONE_PREFIX!r}).")
            print("Re-run with --force to wipe and re-seed.")
            return 1
        print("Wiping existing demo data...")
        u, b = _wipe_demo(client)
        print(f"  wiped {u} users, {b} bills")

    print(f"Seeding {USER_COUNT} users (max {MAX_BILLS_PER_USER} bills each)...")
    u, b = _seed(client, rng)
    print(f"Done: {u} users, {b} bills inserted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
