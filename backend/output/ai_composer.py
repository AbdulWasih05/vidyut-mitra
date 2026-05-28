"""Groq-based AI framing for analysis replies.

Generates 2 personalized lines per main bill report (HEADLINE + PRIORITY)
that get injected into the templated body, plus 1 context line per follow-up
reply. Math is owned by the analysis modules; AI never invents numbers.

Every public function returns ``None`` on any failure (no API key, network
error, malformed JSON, validation failure). Callers fall back to fully
templated rendering — the user always gets a correct response.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from backend.analysis.models import BillExtraction
from backend.analysis.orchestrator import AnalysisResult

logger = logging.getLogger(__name__)

# Llama 3.3 70B Versatile — best instruction-following at LPU speed.
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_OUTPUT_TOKENS_MAIN = 160
MAX_OUTPUT_TOKENS_FOLLOWUP = 80
TEMPERATURE = 0.3
GROQ_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class AILines:
    headline: str
    priority: str


@dataclass(frozen=True)
class AIFollowupLine:
    context: str


# =============================================================================
# System prompts — minified for token efficiency (Groq has no context cache).
# =============================================================================


_MAIN_SYSTEM_PROMPT = (
    "You write 2 short lines for a Karnataka MESCOM bill analyzer (WhatsApp). "
    "Users are rural; be brief, scannable, professional.\n\n"
    "Input: JSON fact-pack about one bill. "
    "Output: JSON ONLY (no markdown, no prose).\n"
    'Format: {"headline":"...","priority":"..."}\n\n'
    "HEADLINE rules:\n"
    "- 2 lines, total <=14 words.\n"
    "- Prefix with emoji: 👉 for facts/wins, 🚨 for danger.\n"
    "- Pick the SINGLE most important finding for this user.\n"
    "- Rs. amounts and unit counts MUST appear verbatim from fact-pack.\n"
    "- No paraphrasing, no rounding (write 1,740 not 'about 1,700').\n\n"
    "PRIORITY rules:\n"
    "- Format: '🎯 Start with: X\\n   (<=8-word reason)'\n"
    "- X must be one of: FIXED, SOLAR, SUBSIDY, CLIFF.\n"
    "- Pick by biggest impact for this user:\n"
    "  • GJ red-zone or near 200 units → CLIFF\n"
    "  • High consumption + solar-eligible → SOLAR\n"
    "  • FCT fires + lower consumption → FIXED\n"
    "  • GJ-eligible not enrolled with no FCT/solar → SUBSIDY\n\n"
    "GJ buffer semantics (when fact-pack contains buf + bk):\n"
    "- bk=\"soft\": user is approaching personal entitlement. Crossing = pay\n"
    "  standard tariff on excess units (subsidy still applies to the rest).\n"
    "- bk=\"hard\": user is approaching the 200-unit MESCOM cap. Crossing =\n"
    "  lose the ENTIRE month's subsidy. Use stronger language for hard.\n"
    "- bk=\"past\": user has already crossed 200; full bill is payable.\n\n"
    "Examples:\n\n"
    'Input: {"u":210,"l":3,"b":1943,"fc":1,"fa":1740,"fm":145,"se":1,"sm":2100,"sp":3.8}\n'
    'Output: {"headline":"👉 You\'re paying Rs. 1,740/year extra in fixed charges.",'
    '"priority":"🎯 Start with: FIXED\\n   (small effort, sure savings)"}\n\n'
    'Input: {"u":280,"l":3,"b":2446,"fc":1,"fa":1740,"se":1,"sm":2400,"sp":3.4}\n'
    'Output: {"headline":"👉 Solar saves Rs. 2,400/month. Payback in 3.4 years.",'
    '"priority":"🎯 Start with: SOLAR\\n   (biggest lever for your usage)"}\n\n'
    'Input: {"u":110,"l":2,"b":0,"g":1,"ge":1,"ent":115,"uPct":96,"warn":"approaching","subM":1080.02,"buf":5,"bk":"soft"}\n'
    'Output: {"headline":"🚨 You\'re 5 units from paying for excess.",'
    '"priority":"🎯 Start with: CLIFF\\n   (summer survival tactics)"}\n\n'
    'Input: {"u":170,"l":1,"b":331,"g":1,"ge":1,"ent":123,"uPct":138,"warn":"monthly_hard","subM":1012.4,"buf":30,"bk":"hard"}\n'
    'Output: {"headline":"🚨 30 units from losing entire Rs. 1,012.4 subsidy.",'
    '"priority":"🎯 Start with: CLIFF\\n   (don\'t cross 200 this month)"}'
)


_FOLLOWUP_SYSTEM_PROMPT = (
    "You write 1 short context line for a Karnataka MESCOM bill follow-up "
    "(WhatsApp). Users are rural; be brief, professional.\n\n"
    "Input: JSON fact-pack. Output: JSON ONLY (no markdown).\n"
    'Format: {"context":"..."}\n\n'
    "CONTEXT rules:\n"
    "- 2 lines, total <=14 words.\n"
    "- Prefix with 👉.\n"
    "- Add personalized framing for this user's specific situation.\n"
    "- Numbers MUST appear verbatim from fact-pack.\n\n"
    "Example:\n"
    'Input: {"topic":"solar","u":210,"sp":3.8}\n'
    'Output: {"context":"👉 At 210 units/month, your payback beats the average."}'
)


# =============================================================================
# Fact-pack builders — compact JSON the AI may reference.
# =============================================================================


def build_main_factpack(result: AnalysisResult) -> dict[str, Any]:
    """Compact fact-pack for the main bill report.

    Field names are abbreviated to save input tokens:
      u   — units consumed
      l   — sanctioned load (kW)
      b   — net bill amount (rupees)
      g   — is GJ beneficiary (1/0)
      fc  — FCT fires (1/0)
      p   — estimated peak (kW)
      fm  — FCT excess monthly cost (rupees)
      fa  — FCT excess annual cost (rupees)
      fr  — FCT recommended load (kW)
      se  — solar eligible (1/0)
      ss  — solar PMSG subsidy (rupees)
      sm  — solar monthly savings (rupees)
      sp  — solar payback years
      sl  — solar lifetime savings (lakh)
      sc  — solar CO2 tonnes/year
      ge  — GJ enrolled (1/0)
      ent — GJ entitlement units
      uPct— GJ entitlement utilization %
      subM— GJ monthly subsidy received (rupees)
      warn— GJ cliff warning level
      buf — units of buffer left before crossing entitlement
    """
    ext = result.extraction
    roi = result.solar_roi
    fct = result.fct
    pmsg = result.pm_surya_ghar
    gj = result.gj_visibility

    pack: dict[str, Any] = {
        "u": ext.units_consumed or 0,
        "l": int(ext.sanctioned_load_kw or 0),
        "b": int(round(result.net_bill_amount or 0)),
        "g": 1 if (gj and gj.is_gj_beneficiary) else 0,
    }

    if fct.fires:
        pack["fc"] = 1
        pack["p"] = round(fct.estimated_peak_kw, 1)
        pack["fm"] = int(round(fct.excess_monthly_cost))
        pack["fa"] = int(round(fct.excess_annual_cost))
        pack["fr"] = int(fct.recommended_load_kw)

    if pmsg.get("eligible"):
        pack["se"] = 1
        pack["ss"] = int(pmsg.get("subsidy_amount") or 0)
        pack["sm"] = int(round(roi.total_monthly_benefit or 0))
        pack["sp"] = round(roi.payback_years or 0, 1)
        pack["sl"] = round((roi.lifetime_net_savings_flat or 0) / 100_000, 1)
        pack["sc"] = round(roi.co2_offset_tonnes_per_year or 0, 2)

    if gj and gj.is_gj_beneficiary:
        pack["ge"] = 1
        ent = int(gj.entitlement_units or 0)
        pack["ent"] = ent
        pack["uPct"] = int(round(gj.entitlement_utilization_pct or 0))
        pack["subM"] = round(gj.monthly_subsidy_received or 0, 2)

        # buf = distance to the closest pending cliff (Option A semantics).
        # Cliff 1 (soft step): personal entitlement. Crossing = pay standard
        #   tariff for excess units, but keep the rest subsidized.
        # Cliff 2 (monthly hard): 200-unit MESCOM cap. Crossing = lose the
        #   ENTIRE month's subsidy.
        # We report whichever positive distance is SMALLER (most imminent),
        # tagging the kind so the AI can phrase appropriately. If Cliff 1 is
        # already crossed but Cliff 2 isn't, we report Cliff 2.
        units = ext.units_consumed or 0
        buf_to_ent = ent - units if ent > 0 else None      # may be negative
        buf_to_200 = 200 - units                            # may be negative
        if buf_to_ent is not None and buf_to_ent > 0 and buf_to_ent <= buf_to_200:
            pack["buf"] = buf_to_ent
            pack["bk"] = "soft"     # next cliff is the soft step
        elif buf_to_200 > 0:
            pack["buf"] = buf_to_200
            pack["bk"] = "hard"     # next cliff is the 200-unit hard cap
        else:
            pack["buf"] = 0
            pack["bk"] = "past"     # already over 200 — full subsidy lost

        # Highest-precedence cliff warning, if any.
        from backend.output.response_composer import _pick_highest_precedence_warning
        top = _pick_highest_precedence_warning(gj.warnings)
        if top is not None and top.cliff is not None:
            pack["warn"] = top.cliff

    return pack


def build_followup_factpack(
    keyword: str,
    extraction: BillExtraction,
    result: AnalysisResult,
) -> dict[str, Any]:
    """Compact fact-pack for SOLAR/FIXED/SUBSIDY/CLIFF follow-ups."""
    pack: dict[str, Any] = {
        "topic": keyword.lower(),
        "u": extraction.units_consumed or 0,
    }
    if keyword == "SOLAR":
        roi = result.solar_roi
        pack["sp"] = round(roi.payback_years or 0, 1)
        pack["sm"] = int(round(roi.total_monthly_benefit or 0))
    elif keyword == "FIXED":
        fct = result.fct
        if fct.fires:
            pack["fa"] = int(round(fct.excess_annual_cost))
            pack["fr"] = int(fct.recommended_load_kw)
    elif keyword == "SUBSIDY":
        gj = result.gj_visibility
        if gj and gj.is_gj_beneficiary:
            pack["ent"] = int(gj.entitlement_units or 0)
            pack["subM"] = round(gj.monthly_subsidy_received or 0, 2)
    elif keyword == "CLIFF":
        gj = result.gj_visibility
        if gj and gj.is_gj_beneficiary:
            pack["uPct"] = int(round(gj.entitlement_utilization_pct or 0))
            pack["ent"] = int(gj.entitlement_units or 0)
    return pack


# =============================================================================
# Validator — guards against hallucinated numbers.
# =============================================================================


_NUMBER_TOKEN_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
# Trivial values that carry no factual claim (counts, list indices, etc.).
# NOTE: "0" is NOT in this set — it's a factual claim ("0 unit buffer",
# "Rs. 0 paid") and the AI has been observed hallucinating it. If the
# fact-pack genuinely contains 0, the value is exposed via _factpack_numbers
# and the AI's "0" passes validation; otherwise the AI is rejected.
_TRIVIAL_NUMBERS = {"1", "2", "3", "4", "5", "10", "12"}


def _normalize(s: str) -> str:
    return s.replace(",", "").rstrip(".")


def _extract_number_tokens(text: str) -> set[str]:
    return {_normalize(n) for n in _NUMBER_TOKEN_RE.findall(text) if n}


def _factpack_numbers(pack: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for v in pack.values():
        if isinstance(v, bool):
            continue  # bools are int subclasses; skip
        if isinstance(v, int):
            out.add(str(v))
        elif isinstance(v, float):
            out.add(str(v))
            if v.is_integer():
                out.add(str(int(v)))
            else:
                out.add(str(int(v)))  # also allow rounded-down form
                out.add(f"{v:.1f}")
                out.add(f"{v:.2f}")
    return out


def validate_ai_output(text: str, pack: dict[str, Any]) -> bool:
    """Return True iff every non-trivial numeric token in `text` is present
    in the fact-pack values. Catches paraphrased / hallucinated numbers."""
    text_nums = _extract_number_tokens(text)
    pack_nums = _factpack_numbers(pack)
    for n in text_nums:
        if n in _TRIVIAL_NUMBERS or n in pack_nums:
            continue
        logger.warning("ai-validation: %r not in factpack %s", n, pack_nums)
        return False
    return True


# =============================================================================
# Groq client — lazy import so non-AI paths don't need the SDK.
# =============================================================================


def _groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key, timeout=GROQ_TIMEOUT_SECONDS)
    except ImportError:
        logger.warning("groq SDK not installed; AI composition disabled")
        return None


def _call_groq(
    system_prompt: str,
    payload: dict[str, Any],
    max_tokens: int,
) -> Optional[dict[str, Any]]:
    """One Groq call. Returns parsed JSON dict, or None on any failure."""
    client = _groq_client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
            ],
            max_tokens=max_tokens,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or ""
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("groq returned non-JSON: %s", e)
        return None
    except Exception as e:  # noqa: BLE001 — fallback path covers everything
        logger.warning("groq call failed: %s", e)
        return None


# =============================================================================
# Public API.
# =============================================================================


def compose_main_lines(result: AnalysisResult) -> Optional[AILines]:
    """Generate the headline + priority lines for a main bill report.

    Returns None if Groq is unavailable, the call fails, the response is
    malformed, or validation rejects it. Caller falls back to template-only.
    """
    pack = build_main_factpack(result)
    parsed = _call_groq(_MAIN_SYSTEM_PROMPT, pack, MAX_OUTPUT_TOKENS_MAIN)
    if parsed is None:
        return None

    headline = (parsed.get("headline") or "").strip()
    priority = (parsed.get("priority") or "").strip()
    if not headline or not priority:
        logger.warning("ai output missing fields: %s", parsed)
        return None

    if not validate_ai_output(headline + "\n" + priority, pack):
        return None

    return AILines(headline=headline, priority=priority)


def compose_followup_line(
    keyword: str,
    extraction: BillExtraction,
    result: AnalysisResult,
) -> Optional[AIFollowupLine]:
    """Generate the single context line for a SOLAR/FIXED/SUBSIDY/CLIFF reply."""
    pack = build_followup_factpack(keyword, extraction, result)
    parsed = _call_groq(_FOLLOWUP_SYSTEM_PROMPT, pack, MAX_OUTPUT_TOKENS_FOLLOWUP)
    if parsed is None:
        return None

    context = (parsed.get("context") or "").strip()
    if not context:
        return None
    if not validate_ai_output(context, pack):
        return None
    return AIFollowupLine(context=context)
