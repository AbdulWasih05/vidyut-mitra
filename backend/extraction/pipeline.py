"""End-to-end extraction orchestrator.

``run_extraction`` is the single entry point downstream modules call. It:

1. Calls ``extract_with_fallback`` (which wraps ``extract_bill`` + cached
   fallbacks for demo phones).
2. Runs ``validate_extraction``. If R1 (not MESCOM) or R2 (pre-April 2025)
   fires, returns immediately with the terminal status — no retry.
3. On R3-R8 issues, issues one retry using the retry prompt with those
   issues enumerated. Tech spec §4.4: exactly one retry; no third attempt.
4. Returns an ``ExtractionResult`` with ``status``, ``extraction`` (or None
   on terminal failure), ``validation_issues``, ``raw``, and ``retries_used``.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from backend.analysis.models import BillExtraction, ExtractionResult, ExtractionStatus
from backend.extraction.gemini_client import GeminiError, extract_bill, extract_with_fallback
from backend.extraction.schema_validator import (
    is_terminal_not_mescom,
    is_terminal_pre_april_2025,
    validate_extraction,
)

logger = logging.getLogger(__name__)


def _classify(issues: list[str]) -> Optional[ExtractionStatus]:
    """Return a terminal status if issues include R1/R2, else None."""
    if is_terminal_not_mescom(issues):
        return ExtractionStatus.NOT_MESCOM
    if is_terminal_pre_april_2025(issues):
        return ExtractionStatus.PRE_APRIL_2025
    return None


def run_extraction(
    image_bytes: bytes,
    phone_number: Optional[str] = None,
) -> ExtractionResult:
    """Extract + validate + (optionally) retry. Returns a typed result.

    On terminal R1/R2 failure, ``extraction`` is None and ``status`` is
    ``NOT_MESCOM`` or ``PRE_APRIL_2025``. The caller should render the
    appropriate user-facing decline message.

    DPDPA (CLAUDE.md §3 Rule 2): ``image_bytes`` is passed by reference
    into Gemini; no disk write exists in this path.
    """
    # --- Attempt 1 -----------------------------------------------------------
    try:
        raw = extract_with_fallback(image_bytes, phone_number)
    except (GeminiError, TimeoutError) as e:
        logger.error("extraction attempt 1 failed: %s", e)
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            validation_issues=[f"gemini_error: {e}"],
        )

    is_valid, issues = validate_extraction(raw)
    if is_valid:
        return ExtractionResult(
            status=ExtractionStatus.OK,
            extraction=BillExtraction.from_dict(raw),
            raw=raw,
            retries_used=0,
        )

    # Terminal R1 or R2 — no retry, user gets the decline message.
    terminal = _classify(issues)
    if terminal is not None:
        return ExtractionResult(
            status=terminal,
            extraction=None,
            validation_issues=issues,
            raw=raw,
            retries_used=0,
        )

    # --- Attempt 2 (single retry, tech spec §4.4) ---------------------------
    logger.info("extraction validation issues, retrying once: %s", issues)
    try:
        raw2 = extract_bill(image_bytes, issues=issues)
    except (GeminiError, TimeoutError) as e:
        logger.error("extraction retry failed: %s", e)
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            validation_issues=issues + [f"gemini_error_on_retry: {e}"],
            raw=raw,
            retries_used=1,
        )

    is_valid2, issues2 = validate_extraction(raw2)
    if is_valid2:
        return ExtractionResult(
            status=ExtractionStatus.OK,
            extraction=BillExtraction.from_dict(raw2),
            raw=raw2,
            retries_used=1,
        )

    # Terminal on retry (rare but possible — e.g. prompt made it clearer the
    # bill is pre-April-2025).
    terminal2 = _classify(issues2)
    if terminal2 is not None:
        return ExtractionResult(
            status=terminal2,
            extraction=None,
            validation_issues=issues2,
            raw=raw2,
            retries_used=1,
        )

    # Two attempts, still invalid. The user gets the "bad photo" message
    # — tech spec §4.4 is explicit: no third retry.
    return ExtractionResult(
        status=ExtractionStatus.FAILED,
        extraction=None,
        validation_issues=issues2,
        raw=raw2,
        retries_used=1,
    )
