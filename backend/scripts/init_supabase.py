"""One-time Supabase schema initialiser.

Tries to apply ``db/schema.sql`` via the ``supabase-py`` client. Supabase's
python client does NOT expose a direct raw-SQL execution path (postgrest-py
is REST-only), so we attempt the ``rpc('exec_sql', ...)`` pattern first — if
that fails (expected on a fresh project without the helper function), we
print the schema and tell the operator to paste it into Supabase Dashboard >
SQL Editor.

After schema is applied (by whichever path), re-run this script to verify:
it selects 0 rows from both ``users`` and ``bills`` and confirms the tables
exist + are queryable.

Usage::

    python scripts/init_supabase.py            # try to apply + verify
    python scripts/init_supabase.py --verify   # verify only (after manual paste)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env from repo root.
try:
    from dotenv import load_dotenv
    REPO_ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    REPO_ROOT = Path(__file__).resolve().parent.parent


SCHEMA_PATH = REPO_ROOT / "backend" / "db" / "schema.sql"


# =============================================================================
# Pretty output helpers
# =============================================================================

_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"{_GREEN}[OK]{_RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{_YELLOW}[WARN]{_RESET} {msg}")


def err(msg: str) -> None:
    print(f"{_RED}[ERR]{_RESET} {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"{_DIM}{msg}{_RESET}")


# =============================================================================
# Client + schema helpers
# =============================================================================


def _client():
    url = os.environ.get("SUPABASE_URL")
    if not url:
        err("SUPABASE_URL not set. Copy .env.example -> .env and fill it in.")
        sys.exit(1)

    # Prefer service-role key for schema work; fall back to anon.
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_KEY")
    key = service_key or anon_key
    role = "service_role" if service_key else "anon"
    if not key:
        err("Neither SUPABASE_SERVICE_ROLE_KEY nor SUPABASE_KEY is set.")
        sys.exit(1)

    info(f"Connecting to {url} with {role} key")
    from supabase import create_client
    return create_client(url, key), role


def _verify(client) -> bool:
    """Return True iff both ``users`` and ``bills`` exist + are queryable."""
    for table in ("users", "bills"):
        try:
            client.table(table).select("*").limit(0).execute()
            ok(f"table '{table}' exists and is queryable")
        except Exception as exc:  # noqa: BLE001
            err(f"table '{table}' check failed: {type(exc).__name__}: {str(exc)[:200]}")
            return False
    return True


def _print_manual_instructions() -> None:
    warn("")
    warn("Supabase's python client doesn't support raw DDL execution.")
    warn("One-time manual step:")
    warn("")
    warn("  1. Open Supabase Dashboard -> SQL Editor -> New Query")
    warn(f"  2. Paste the contents of: {SCHEMA_PATH}")
    warn("  3. Click 'Run'")
    warn(f"  4. Re-run this script with --verify to confirm")
    warn("")


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    verify_only = "--verify" in sys.argv

    if not SCHEMA_PATH.exists():
        err(f"schema file missing: {SCHEMA_PATH}")
        return 2

    client, role = _client()

    if _verify(client):
        ok("")
        ok("Schema already initialised. Nothing to do.")
        return 0

    if verify_only:
        err("verify-only mode requested but tables not found. Apply the schema first.")
        _print_manual_instructions()
        return 3

    # Attempt direct SQL via rpc — works only if the operator has already
    # added an ``exec_sql`` helper. On a fresh project this fails; we then
    # print the manual-paste instructions.
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    try:
        info("Attempting rpc('exec_sql', ...) — usually fails on fresh projects...")
        client.rpc("exec_sql", {"sql": schema_sql}).execute()
        ok("Schema applied via rpc.")
    except Exception as exc:  # noqa: BLE001
        warn(f"rpc('exec_sql') failed ({type(exc).__name__}). Falling back to manual paste.")
        _print_manual_instructions()
        print()
        print("--- BEGIN schema.sql ---")
        print(schema_sql)
        print("--- END schema.sql ---")
        return 1

    # Re-verify.
    if _verify(client):
        ok("Schema applied and verified.")
        return 0
    err("Schema reported applied, but verification failed.")
    return 4


if __name__ == "__main__":
    sys.exit(main())
