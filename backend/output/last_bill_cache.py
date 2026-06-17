"""In-memory cache of the most recent analysis per phone number.

Used by the follow-up routing in ``app.py``: when a consented user replies
``SOLAR`` / ``FIXED`` / ``SUBSIDY`` / ``CLIFF``, we need the analysis of the
bill they JUST sent so we can deep-dive into one section.

**Not images, not PII beyond what's already in DB-bound fields.** Entries
store only the ``BillExtraction`` + ``AnalysisResult`` that the analysis
pipeline already produced — raw bill image bytes never reach this module.
Per CLAUDE.md §3 Rule 2, no ``open(..., 'wb')`` call exists here and
nothing is written to disk.

TTL: 30 minutes. After that the entry is considered stale and ``get_last_bill``
returns ``None`` — judges shouldn't be able to fire "CLIFF" a day later and
get an answer tied to yesterday's bill.

Supabase migration for this cache is planned for Session 7 once we need
multi-process persistence (e.g. running the web-fallback on a second
worker). Session 5.5 scope is single-process in-memory only.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Optional

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import AnalysisResult


CACHE_TTL = timedelta(minutes=30)


@dataclass
class _CacheEntry:
    extraction: BillExtraction
    analysis: AnalysisResult
    follow_up_count: int
    cached_at: datetime


_LAST_BILL_CACHE: dict[str, _CacheEntry] = {}
_LOCK = Lock()


def _now() -> datetime:
    """Module-level indirection so tests can monkey-patch ``_now``."""
    return datetime.now(timezone.utc)


def set_last_bill(
    phone_number: str,
    analysis: AnalysisResult,
    extraction: BillExtraction,
    follow_up_count: int = 0,
) -> None:
    """Cache the latest bill + analysis for a phone number. Overwrites."""
    with _LOCK:
        _LAST_BILL_CACHE[phone_number] = _CacheEntry(
            extraction=extraction,
            analysis=analysis,
            follow_up_count=follow_up_count,
            cached_at=_now(),
        )


def get_last_bill(phone_number: str) -> Optional[dict[str, Any]]:
    """Return the cached entry or ``None`` if missing / expired."""
    with _LOCK:
        entry = _LAST_BILL_CACHE.get(phone_number)
        if entry is None:
            return None
        if _now() - entry.cached_at > CACHE_TTL:
            # Expired — proactively evict so we don't keep stale data around.
            del _LAST_BILL_CACHE[phone_number]
            return None
        return {
            "extraction": entry.extraction,
            "analysis": entry.analysis,
            "follow_up_count": entry.follow_up_count,
            "cached_at": entry.cached_at,
        }


def increment_follow_up(phone_number: str) -> int:
    """Bump the follow-up counter; returns the new value. 0 if entry is gone."""
    with _LOCK:
        entry = _LAST_BILL_CACHE.get(phone_number)
        if entry is None:
            return 0
        entry.follow_up_count += 1
        return entry.follow_up_count


def clear_bill(phone_number: str) -> None:
    """Wipe the entry for a phone number. Idempotent."""
    with _LOCK:
        _LAST_BILL_CACHE.pop(phone_number, None)


def _reset_for_tests() -> None:
    """Clear the entire cache — test fixtures only."""
    with _LOCK:
        _LAST_BILL_CACHE.clear()
