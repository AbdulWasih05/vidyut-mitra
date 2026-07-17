"""Wipe all DEMO-prefixed users (and their bills via CASCADE).

For post-hackathon cleanup. Does NOT touch any real consented user row -
only rows whose phone_number starts with ``whatsapp:+91DEMO``.

Usage::

    python scripts/clean_demo_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from backend.db import supabase_client

DEMO_PHONE_PREFIX = "whatsapp:+91DEMO"


def main() -> int:
    client = supabase_client.init_client()

    users = (
        client.table("users")
        .select("id,phone_number")
        .ilike("phone_number", f"{DEMO_PHONE_PREFIX}%")
        .execute()
    )
    rows = users.data or []
    if not rows:
        print("No demo data found. Nothing to clean.")
        return 0

    # Count bills before deletion.
    user_ids = [r["id"] for r in rows]
    bills = (
        client.table("bills")
        .select("id", count="exact")
        .in_("user_id", user_ids)
        .execute()
    )
    bill_count = bills.count or 0

    # Delete users - bills cascade via FK.
    for uid in user_ids:
        client.table("users").delete().eq("id", uid).execute()

    print(f"Deleted {len(rows)} demo users and {bill_count} cascaded bills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
