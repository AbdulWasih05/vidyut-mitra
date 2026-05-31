"""Live Supabase integration test — end-to-end user + bill lifecycle.

Skipped by default. Run with::

    pytest -v -m integration tests/test_supabase_live.py

Requires ``SUPABASE_URL`` and ``SUPABASE_KEY`` set and the schema from
``db/schema.sql`` applied to the project. Uses a fixed test phone
``whatsapp:+919999999000`` that doesn't collide with demo data (seed data
uses the ``whatsapp:+91DEMO...`` prefix).
"""
from __future__ import annotations

import os

import pytest

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from backend.analysis.models import BillExtraction

pytestmark = pytest.mark.integration

TEST_PHONE = "whatsapp:+919999999000"


def _require_supabase():
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY")):
        pytest.skip("SUPABASE_URL / SUPABASE_KEY not set")


def _nikhil_bill() -> BillExtraction:
    return BillExtraction(
        is_mescom_bill=True,
        extraction_confidence=0.95,
        tariff_category="LT-1",
        billing_period_start="2026-02-15",
        billing_period_end="2026-03-15",
        billing_period_days=30,
        sanctioned_load_kw=3.0,
        units_consumed=210,
        energy_charges=1218.0,
        fixed_charges=435.0,
        pg_surcharge=75.6,
        electricity_tax=109.62,
        fppca=105.0,
        other_charges=0.0,
        subtotal_1_before_subsidy=1943.22,
        is_gruha_jyothi_beneficiary=False,
        net_bill_amount=1943.22,
    )


def test_end_to_end_user_and_bill_lifecycle():
    """get_or_create → set_consent → write_bill → query → delete cascade."""
    _require_supabase()
    from backend.db import supabase_client

    # Belt-and-braces cleanup first — in case a previous test didn't teardown.
    supabase_client.delete_user_cascade(TEST_PHONE)

    try:
        user = supabase_client.get_or_create_user(TEST_PHONE)
        assert user["phone_number"] == TEST_PHONE
        assert user["consent_given"] is False

        again = supabase_client.get_or_create_user(TEST_PHONE)
        assert again["id"] == user["id"]

        updated = supabase_client.set_consent(TEST_PHONE, True)
        assert updated["consent_given"] is True

        analysis_blob = {
            "net_bill_amount": 1943.22,
            "fct": {"fires": True, "excess_annual_cost": 1740},
            "is_gj_beneficiary": False,
            "_test_marker": True,
        }
        bill_id = supabase_client.write_bill(
            user_id=user["id"],
            extraction=_nikhil_bill(),
            analysis=analysis_blob,
        )
        assert isinstance(bill_id, str)

        c = supabase_client.init_client()
        fetched = c.table("bills").select("*").eq("id", bill_id).execute()
        assert len(fetched.data) == 1
        row = fetched.data[0]
        assert row["units_consumed"] == 210
        assert row["sanctioned_load_kw"] == 3.0
        assert row["is_gj_beneficiary"] is False
        assert row["analysis_result"]["fct"]["fires"] is True

        existed, count = supabase_client.delete_user_cascade(TEST_PHONE)
        assert existed is True
        assert count == 1

        after = (
            c.table("users")
            .select("id", count="exact")
            .eq("phone_number", TEST_PHONE)
            .execute()
        )
        assert (after.count or 0) == 0
    finally:
        supabase_client.delete_user_cascade(TEST_PHONE)
