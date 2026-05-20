# VidyutMitra — Technical Specification

**Version:** 2.0
**Date:** April 17, 2026 (afternoon update)
**Status:** Hackfest'26 Finals Build Specification
**Primary sources:**
- Tariff constants: KERC Tariff Order 2025 (Order Dated 27th March 2025, Annexure 2)
- Grid emission factor: CEA CO₂ Baseline Database Version 21.0, December 2025
- Gruha Jyothi rules: Karnataka Cabinet decision 18-Jan-2024, as enforced per CESC MD K.M. Munigopalraju, Star of Mysore, 23-Nov-2025

**Canonical persona math:** `VidyutMitra_Verified_Tariff_v3.md`
**Canonical product spec:** `VidyutMitra_PRD_v3.md`

**Changed in v2.0:** Emission factor updated from 0.82 → 0.710 kg CO₂/kWh; Gruha Jyothi cliff model rewritten as three-level (soft step + monthly hard cliff + eligibility cliff) with an added Level 0 approaching-entitlement warning; CO₂ offset recomputed to 2.98 tonnes/year / ~100 trees; 25-year solar savings now presented as both flat-tariff (Rs. 4.3 lakh) and 3%-escalation (Rs. 6.9 lakh) scenarios.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Overview](#2-architecture-overview)
3. [Data Flow](#3-data-flow)
4. [Gemini Integration Specification](#4-gemini-integration-specification)
5. [MESCOM Tariff Engine Specification](#5-mescom-tariff-engine-specification)
6. [Fixed Charge Trap Detection Logic](#6-fixed-charge-trap-detection-logic)
7. [Subsidy Navigator Specification](#7-subsidy-navigator-specification)
8. [Solar ROI Calculation Methodology](#8-solar-roi-calculation-methodology)
9. [DPDPA Compliance Design](#9-dpdpa-compliance-design)
10. [Database Schema](#10-database-schema)
11. [API Surface](#11-api-surface)
12. [Environment and Deployment](#12-environment-and-deployment)
13. [Error Handling and Fallback Ladder](#13-error-handling-and-fallback-ladder)
14. [Scalability Considerations](#14-scalability-considerations)
15. [Known Limitations and Future Work](#15-known-limitations-and-future-work)

---

## 1. System Overview

VidyutMitra is a WhatsApp-first conversational assistant that converts a photo of a MESCOM (Mangalore Electricity Supply Company) electricity bill into personalized, MESCOM-calibrated financial guidance — delivered in Kannada with zero app downloads required. A consumer sends a bill photo to a WhatsApp number; Google's Gemini 2.5 Flash vision model extracts structured fields (units, sanctioned load, tariff category, charge breakdown, Gruha Jyothi status); a rules-based analysis engine validates the bill against KERC's FY 2025-26 tariff schedule, detects a pattern called the "Fixed Charge Trap" where households pay fixed charges on sanctioned loads they don't actually use, surfaces the invisible Gruha Jyothi subsidy most beneficiaries don't know they receive, checks PM Surya Ghar rooftop solar eligibility, and computes a locally-calibrated solar ROI; the response is returned as formatted WhatsApp text plus a Kannada voice note plus a pre-rendered infographic. All of this happens in 8–12 seconds end-to-end, with no raw bill image ever written to storage (only extracted text fields persist), a one-word STOP command that hard-deletes all user data, and an explicit opt-in consent flow gating every downstream action.

---

## 2. Architecture Overview

The system is organized into five layers. Data flows strictly in one direction from Input → Processing → Analysis → Output, with Storage accessed by Analysis and Output for persistence and retrieval.

### Layer 1: Input

Receives WhatsApp messages and media, handles consent state, and routes requests to downstream processing.

| Component | Responsibility |
|-----------|----------------|
| Twilio WhatsApp Sandbox webhook | Receives POST from Twilio when a user sends a message or media. Parses the Twilio form payload to extract phone number, message body, media URL. |
| Consent gate | Checks `users.consent_given` for the sender's phone number. If false, returns the consent message and blocks all downstream processing. |
| STOP handler | Intercepts any message containing "STOP" (case-insensitive) before any other routing, triggers a CASCADE delete of the user's data, and returns a confirmation. |

### Layer 2: Processing

Takes raw bill media and produces a validated, structured `BillExtraction` JSON object suitable for analysis.

| Component | Responsibility |
|-----------|----------------|
| Media fetcher | Downloads the bill image from Twilio's media URL into a byte buffer. Image bytes are held in memory only — never written to disk. |
| Gemini 2.5 Flash client | Sends image bytes + extraction prompt to the Gemini API, requests JSON-mode output, returns parsed dict. |
| Schema validator | Runs structural checks on the extracted JSON (required fields present, numeric ranges, meter reading consistency, bill math). Returns a list of issues. |
| Retry handler | On validation failure, re-prompts Gemini once with explicit guidance about which fields failed. After two failures, routes to the "bad photo" error response. |
| Pre-April 2025 gate | Rejects bills with `billing_period_end < 2025-04-01` with a graceful-decline message. |

### Layer 3: Analysis

Takes a validated `BillExtraction` and produces all downstream analytical outputs. Three modules, all pure functions — no I/O, no external calls.

| Module | Responsibility |
|--------|----------------|
| **Tariff Engine** | Two concerns in one module because they share the bill-structure parsing logic. (a) **Bill validator:** recomputes the expected bill from KERC rates (`units × 5.80 + kW × 145 + ...`) and flags any discrepancy with the extracted total. (b) **Fixed Charge Trap detector:** estimates peak demand from consumption, flags when sanctioned load is materially higher than estimated peak, quantifies the overpayment. (c) **Gruha Jyothi Visibility:** for GJ-enrolled consumers, computes monthly subsidy received, annualized subsidy, months-since-enrollment cumulative benefit, and fires **three-level cliff warnings** (soft step above entitlement, monthly hard cliff at 200 units, eligibility cliff on 10-month rolling average). |
| **Subsidy Navigator** | Evaluates three separate subsidy programs against the consumer's profile: PM Surya Ghar (rooftop solar), Gruha Jyothi (state electricity subsidy), and the solar water heater rebate. Returns eligibility plus application path plus next steps. |
| **Solar ROI Calculator** | Sizes the recommended system based on annual consumption and Mangalore irradiance, computes system cost, applies the tiered PM Surya Ghar subsidy, projects monthly savings from displaced grid consumption plus net-metering exports, derives payback and 25-year lifetime savings, estimates CO₂ offset. Returns "not recommended" for GJ beneficiaries whose current consumption is well within entitlement. |

> The original PRD included a fourth module — a Slab Optimizer — which suggested unit reductions to cross slab boundaries. It was removed in PRD v2 because KERC's Tariff Order 2025 eliminated telescopic slabs for LT-1 Domestic consumers in favor of a single flat rate of Rs. 5.80 per unit (KERC Tariff Order 2025, Annexure 2, Clause 19 and Clause 30). There are no slab boundaries to optimize around. Linear consumption reduction is surfaced as a tip inside the Tariff Engine, not a standalone module.

### Layer 4: Output

Composes analytical results into multi-modal WhatsApp responses.

| Component | Responsibility |
|-----------|----------------|
| Response composer | Assembles formatted WhatsApp text from persona-appropriate templates (non-GJ, GJ, pre-April-2025-decline, error). Inserts computed values via string substitution. |
| Kannada TTS | Sends a shortened version of the key findings to Google Cloud TTS (Kannada voice), receives audio, returns audio URL. |
| Infographic renderer | Loads a pre-rendered PNG/SVG template, overlays computed values via Pillow (or equivalent), writes a temp file, returns its URL. |
| Twilio dispatcher | Sends three sequential WhatsApp messages with a 1-second gap between each (sandbox rate limit compliance): text, then voice note, then infographic. |

### Layer 5: Storage

Persists only what's needed for history and analytics. Never the raw bill image.

| Component | Responsibility |
|-----------|----------------|
| Supabase `users` table | Stores phone number, consent state, timestamps. One row per unique phone number. |
| Supabase `bills` table | Stores extracted fields + full analysis JSONB per analyzed bill. Foreign-keyed to `users` with `ON DELETE CASCADE`. No `bill_image` column by design. |
| Demo fallback cache | A local JSON file (`demo_fallbacks.json`) keyed by phone number, containing pre-generated extraction results for the demo bills. Used only when live Gemini calls fail during the live demo. |

---

## 3. Data Flow

### Happy path — non-GJ consumer (Nikhil scenario)

| # | Step | Component | Input | Output | Latency target |
|---|------|-----------|-------|--------|----------------|
| 1 | User sends bill photo on WhatsApp | Twilio WhatsApp Sandbox | User's WhatsApp message with media | Webhook POST to our Flask endpoint | ~500 ms (outside our control) |
| 2 | Receive webhook | `POST /whatsapp` (Flask) | Twilio form payload | Parsed `from_phone`, `media_url` | 50 ms |
| 3 | Consent check | Consent gate | `from_phone` | `consent_given` boolean from Supabase | 100 ms |
| 4 | Acknowledge | Twilio dispatcher | Ack message text | "⏳ Analyzing your bill…" sent to WhatsApp | 300 ms |
| 5 | Fetch media | Media fetcher | `media_url` + Twilio auth | Image bytes in memory | 500–1,500 ms |
| 6 | Extract | Gemini 2.5 Flash client | Image bytes + `EXTRACTION_PROMPT` | `BillExtraction` JSON dict | 3,000–5,000 ms |
| 7 | Validate | Schema validator | `BillExtraction` | `(is_valid, issues)` tuple | <10 ms |
| 8 | Pre-April 2025 gate | Date gate | `billing_period_end` | Pass or decline | <1 ms |
| 9 | Tariff Engine | Tariff Engine | `BillExtraction` | `TariffResult` with bill validation, Fixed Charge Trap flag, GJ Visibility | <10 ms |
| 10 | Subsidy Navigator | Subsidy Navigator | `BillExtraction` | `SubsidyResult` | <10 ms |
| 11 | Solar ROI Calculator | Solar ROI Calculator | `BillExtraction` + `TariffResult` | `SolarROI` | <10 ms |
| 12 | Compose response | Response composer | All analysis outputs | WhatsApp text message body | 20 ms |
| 13 | Kannada TTS | Google Cloud TTS | Short summary text in Kannada | Audio file URL | 1,500–2,500 ms |
| 14 | Infographic render | Infographic renderer | Key numbers | PNG/SVG file URL | 500 ms |
| 15 | Persist | Supabase write | Extracted fields + analysis JSONB | Row in `bills` | 200 ms |
| 16 | Discard bytes | Garbage collector | Image bytes variable | None | <1 ms |
| 17 | Dispatch | Twilio dispatcher | Text + voice URL + infographic URL | 3 WhatsApp messages (1 sec apart) | 3,000 ms |

**Total end-to-end target: 8–12 seconds** from user photo to full response on their phone.

### GJ path variant

At step 9, the Tariff Engine detects `is_gruha_jyothi_beneficiary = true` and routes to the GJ response template (emphasizing subsidy visibility, three-level cliff intelligence, and a "solar not recommended" note for under-entitlement households). Steps 10–17 otherwise identical.

### Error paths

| Condition | Detected at | Response | Persisted? |
|-----------|-------------|----------|------------|
| Unconsented user sends any message | Step 3 | Consent request message | No bill data persisted |
| Unconsented user sends a bill photo | Step 3 | Consent request message; image never fetched, never sent to Gemini | No |
| STOP command | Pre-step 3 (intercepted) | Confirmation; CASCADE delete of user | All user data hard-deleted |
| Non-MESCOM bill / unreadable | Step 7 (`is_mescom_bill = false`) | "Bad photo" message with tips | No |
| Pre-April 2025 bill | Step 8 | "Tariff structure updated April 2025, please send a recent bill" | No |
| Validation fails twice | Step 7 after retry | "Bad photo" message | No |
| Gemini API timeout/5xx | Step 6 | Demo: load from `demo_fallbacks.json` if phone matches; else "try again in a minute" | Depends on path |
| Twilio media fetch fails | Step 5 | "Couldn't retrieve your photo, please resend" | No |
| Supabase write fails | Step 15 | Log error; still dispatch response (fire-and-forget analytics) | Partially — user sees response, no history record |

---

## 4. Gemini Integration Specification

### 4.1 Model and configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Model | `gemini-2.5-flash` | Best speed/cost/quality balance for image extraction; Flash latency ~3 sec; ~Rs. 0.11/bill |
| `temperature` | 0.1 (first attempt), 0.05 (retry) | Deterministic for factual extraction; retry is even tighter |
| `response_mime_type` | `application/json` | Forces structured output; eliminates markdown-wrapping parsing bugs |
| `max_output_tokens` | 2048 | Comfortably above the ~800 tokens the schema requires |

### 4.2 Extraction prompt

```python
EXTRACTION_PROMPT = """You are an expert at reading Indian electricity bills. Analyze this image of a MESCOM (Mangalore Electricity Supply Company) electricity bill.

Extract the following fields and return ONLY a valid JSON object. No markdown, no explanation, no preamble.

IDENTIFICATION:
- is_mescom_bill (boolean): Is this a MESCOM electricity bill? Set false if different utility, non-bill document, or unreadable.
- extraction_confidence (float 0.0-1.0): Your self-reported confidence.
- consumer_name (string): Consumer name as printed.
- rr_number (string): RR Number / Account Number / Consumer Number.
- tariff_category (string): Tariff code (e.g., "LT-1", "2LT1", "LT-2(a)"). Normalize "2LT1" to "LT-1".

BILLING PERIOD:
- billing_period_start (string): Period start in YYYY-MM-DD.
- billing_period_end (string): Period end in YYYY-MM-DD. Dates on bills may be in DD/MM/YYYY format - convert to ISO.
- billing_period_days (integer): Number of days in billing period.

CONSUMPTION AND LOAD:
- sanctioned_load_kw (float): Sanctioned load in kW. Bills may say "2.99KW+0HP" etc. - extract the kW value.
- previous_reading (integer): Previous meter reading.
- current_reading (integer): Current meter reading.
- units_consumed (integer): Units consumed in this period.

PRE-SUBSIDY BILL COMPONENTS (Sub-Total-1 on the bill):
- energy_charges (float): Energy/consumption charges in Rs.
- fixed_charges (float): Fixed charges in Rs.
- pg_surcharge (float): P&G surcharge in Rs. Set 0.0 if not present.
- electricity_tax (float): Electricity tax / tax @ 9% in Rs.
- fppca (float): FPPCA (Fuel and Power Purchase Cost Adjustment) in Rs. Set 0.0 if not present.
- other_charges (float): Sum of any other line items (arrears, adjustments) in Rs.
- subtotal_1_before_subsidy (float): Total of all pre-subsidy charges. On GJ bills this is Sub-Total-1.

GRUHA JYOTHI (CRITICAL):
MESCOM bills with Gruha Jyothi show the bill TWICE - once as pre-subsidy (Sub-Total-1) and once as subsidy amount (Sub-Total-2). Net bill = Sub-Total-1 - Sub-Total-2.

- is_gruha_jyothi_beneficiary (boolean): True if the bill has a "Gruha Jyothi Subsidy" / "GJ" section with a Sub-Total-2.
- gjs_registration_date (string): GJS Reg Date in YYYY-MM-DD, or null.
- historical_avg_baseline (float): "Average (FY XX-XX)" field showing historical consumption baseline, or null.
- entitlement_units (float): "Entitlement Unit" field - the subsidized unit allowance, or null.
- units_eligible_for_subsidy (float): Units covered by subsidy this month, or null.
- units_chargeable (float): Units the consumer actually pays for (0 if fully covered), or null.
- gruha_jyothi_subsidy_amount (float): Sub-Total-2 amount in Rs., or null.

NET BILL:
- net_bill_amount (float): What the consumer actually pays. For non-GJ = Sub-Total-1. For GJ = Sub-Total-1 - Sub-Total-2 (usually 0).
- due_date (string): Due date in YYYY-MM-DD. Convert from DD/MM/YYYY if needed.
- arrears (float): Arrears in Rs., 0.0 if none.

RULES:
1. If a field is not visible or unreadable, set it to null. Do not guess.
2. Amounts are in Indian Rupees. Do not include currency symbols in numeric fields.
3. Dates may be in DD/MM/YYYY format on the bill - always convert to ISO YYYY-MM-DD.
4. Bills contain Kannada text; extract numeric values regardless of language.
5. If not a MESCOM bill, set is_mescom_bill to false and other fields to null.
6. For GJ bills: the number after "Bill for Consumed Units" / "Sub-Total-1" is pre-subsidy. The number after "Gruha Jyothi Subsidy" / "Sub-Total-2" is the subsidy. "Current Bill Amt" or "Net Bill Amt" is what the consumer pays.

Return ONLY the JSON object."""
```

### 4.3 Validation rules

Validation is **structural**, not confidence-based. Gemini's self-reported `extraction_confidence` is logged as a soft signal but is never used as a gate — LLM self-confidence is unreliable, especially when hallucinating.

| Rule | Check | On failure |
|------|-------|-----------|
| R1 | `is_mescom_bill == true` | Abort with "bad_photo" |
| R2 | `billing_period_end >= "2025-04-01"` | Abort with "pre_april_2025" |
| R3 | `0 < units_consumed <= 10000` | Add to issues list |
| R4 | `0 < sanctioned_load_kw <= 50` | Add to issues list |
| R5 | `current_reading > previous_reading` | Add to issues list |
| R6 | `abs((current_reading - previous_reading) - units_consumed) <= 5` | Add to issues list |
| R7 | Bill math: `abs(subtotal_1 - (energy + fixed + pg + tax + fppca + other)) <= 5` | Add to issues list |
| R8 | GJ math (if GJ): `abs((subtotal_1 - gj_subsidy) - net_bill_amount) <= 5` | Add to issues list |

If R1 or R2 fail, abort immediately with the appropriate user-facing message. If R3–R8 accumulate issues, trigger retry.

### 4.4 Retry strategy

One retry only, with a stricter prompt that enumerates the specific failed fields:

```python
RETRY_PROMPT_TEMPLATE = """Your previous extraction of this MESCOM electricity bill had these issues:
{issues_list}

Please re-examine the bill image carefully, paying special attention to the fields listed above.
Return the complete JSON object again with corrected values.

If a field is genuinely unreadable, set it to null - do not guess.

Return ONLY the JSON object."""
```

After a second failure, the bill is rejected with the "bad photo" response. No third retry — the latency cost is too high for the demo.

### 4.5 Cached fallback mechanism

The file `demo_fallbacks.json` contains pre-generated `BillExtraction` objects keyed by demo phone number:

```json
{
  "+919876543210": {
    "persona": "nikhil",
    "extracted_at": "2026-04-16T18:00:00Z",
    "extraction": { /* full BillExtraction JSON */ }
  },
  "+919876543211": {
    "persona": "sunita",
    "extracted_at": "2026-04-16T18:00:00Z",
    "extraction": { /* full BillExtraction JSON */ }
  },
  "+919876543212": {
    "persona": "priya",
    "extracted_at": "2026-04-16T18:00:00Z",
    "extraction": { /* full BillExtraction JSON */ }
  }
}
```

Fallback trigger logic:

```python
def extract_with_fallback(image_bytes, phone_number):
    try:
        return extract_bill(image_bytes)
    except (GeminiError, TimeoutError) as e:
        logger.warning(f"Gemini failed: {e}. Attempting demo fallback.")
        fallback = DEMO_FALLBACKS.get(phone_number)
        if fallback:
            logger.info(f"Using cached extraction for {fallback['persona']}")
            return fallback["extraction"]
        raise
```

This preserves a valid demo on-stage even if Gemini has an outage at 14:30 IST on April 18. The fallback is deliberately scoped to demo phones only — production users see the "try again" error.

---

## 5. MESCOM Tariff Engine Specification

### 5.1 Verified KERC FY 2025-28 constants

All values below are from **KERC Tariff Order 2025, Order Dated 27th March 2025, Annexure 2**, Tariff Schedule LT-1 (Domestic).

| Component | FY 2025-26 | FY 2026-27 | FY 2027-28 | Notes |
|-----------|------------|------------|------------|-------|
| Fixed charge | Rs. 145/kW/month | Rs. 150/kW/month | **Rs. 160/kW/month** | Not Rs. 155 as some news reports stated |
| Energy charge | Rs. 5.80/unit (flat) | Rs. 5.80/unit | Rs. 5.75/unit | Single-slab structure per Clauses 19 and 30 |
| Solar rooftop fixed rebate | Rs. 25/kW/month | Rs. 25/kW/month | Rs. 25/kW/month | LT-1 Note (b), up to 10 kW |

Not in the KERC tariff schedule but applied to every bill (separate orders / authorities):

| Component | Value | Source |
|-----------|-------|--------|
| P&G surcharge | Rs. 0.36/unit (FY 2025-26) | KERC Separate Order, 18-Mar-2025 |
| Electricity tax | 9% of energy charges | Government of Karnataka |
| FPPCA | ~Rs. 0.50/unit (variable) | Monthly MESCOM adjustment order |

### 5.2 Bill formula (FY 2025-26 LT-1 Domestic)

```
energy_charges    = units_consumed × 5.80
fixed_charges     = sanctioned_load_kw × 145
pg_surcharge      = units_consumed × 0.36
electricity_tax   = energy_charges × 0.09
fppca             = units_consumed × fppca_rate  # ~0.50
subtotal_1        = energy_charges + fixed_charges + pg_surcharge
                  + electricity_tax + fppca

# Gruha Jyothi three-level cliff (per Karnataka Cabinet 18-Jan-2024,
# as enforced per CESC MD K.M. Munigopalraju, Nov 2025):
IF NOT gruha_jyothi_enrolled:
    net_bill      = subtotal_1

ELIF units_consumed > 200:
    # LEVEL 2 — monthly hard cliff: lose ENTIRE subsidy for this month
    gj_subsidy    = 0
    net_bill      = subtotal_1

ELIF units_consumed <= entitlement_units:
    # Under entitlement: full subsidy, zero bill
    gj_subsidy    = subtotal_1
    net_bill      = 0

ELSE:
    # LEVEL 1 — soft step: entitlement < units_consumed <= 200
    # Pay for excess units only, at standard tariff (~Rs. 7.18/unit all-in)
    excess_units  = units_consumed - entitlement_units
    net_bill      = excess_units × effective_per_unit_rate  # ≈ Rs. 7.18
    gj_subsidy    = subtotal_1 - net_bill

# LEVEL 3 — eligibility cliff — enforced separately by MESCOM on 10-month
# rolling average > 200 units. Not a per-bill computation; affects whether
# the consumer remains enrolled at all at the next review window.
```

### 5.3 Worked examples — three personas

#### Nikhil — 210 units, 3 kW sanctioned, non-GJ

| Line | Computation | Amount (Rs.) |
|------|-------------|--------------|
| Energy charges | 210 × 5.80 | 1,218.00 |
| Fixed charges | 3 × 145 | 435.00 |
| P&G surcharge | 210 × 0.36 | 75.60 |
| Electricity tax | 9% × 1,218 | 109.62 |
| FPPCA | 210 × 0.50 | 105.00 |
| **Sub-Total-1** | | **1,943.22** |
| GJ subsidy | — (not enrolled) | 0.00 |
| **Net bill** | | **1,943.22** |

#### Sunita — 280 units, 3 kW sanctioned, non-GJ

| Line | Computation | Amount (Rs.) |
|------|-------------|--------------|
| Energy charges | 280 × 5.80 | 1,624.00 |
| Fixed charges | 3 × 145 | 435.00 |
| P&G surcharge | 280 × 0.36 | 100.80 |
| Electricity tax | 9% × 1,624 | 146.16 |
| FPPCA | 280 × 0.50 | 140.00 |
| **Sub-Total-1** | | **2,445.96** |
| GJ subsidy | — | 0.00 |
| **Net bill** | | **2,445.96** |

#### Priya — 110 units, 2 kW sanctioned, GJ-enrolled (entitlement 115 units)

| Line | Computation | Amount (Rs.) |
|------|-------------|--------------|
| Energy charges | 110 × 5.80 | 638.00 |
| Fixed charges | 2 × 145 | 290.00 |
| P&G surcharge | 110 × 0.36 | 39.60 |
| Electricity tax | 9% × 638 | 57.42 |
| FPPCA | 110 × 0.50 | 55.00 |
| **Sub-Total-1** | | **1,080.02** |
| GJ subsidy (since 110 ≤ 115) | | 1,080.02 |
| **Net bill** | | **0.00** |

### 5.4 Validation logic

The engine recomputes the bill from first principles and compares to the extracted totals. A tolerance of ±Rs. 5 absorbs FPPCA rounding and any FAC-equivalent line items. Variance beyond Rs. 5 sets `bill_matches_calculation = false` and populates `variance_rupees`, which the consumer sees as a "bill verification" line in the response.

---

## 6. Fixed Charge Trap Detection Logic

### 6.1 Concept

The Fixed Charge Trap is an original analytical frame introduced by VidyutMitra. A consumer's sanctioned load (billed monthly at Rs. 145/kW) is often chosen at connection time based on expected maximum simultaneous appliance draw. In practice, actual peak demand is usually 40–60% of sanctioned. The consumer pays the full fixed charge regardless. A 3 kW sanctioned household whose actual peak demand is 1.5 kW overpays Rs. 145/month on 1 kW of unused capacity — or Rs. 1,740/year.

### 6.2 Peak demand heuristic

We cannot measure actual peak demand from monthly aggregate consumption. We estimate it using a simple envelope:

```
estimated_peak_kw = (units_consumed / (billing_period_days × 8)) × 1.67
```

Assumptions:

| Assumption | Value | Rationale |
|------------|-------|-----------|
| Active consumption hours per day | 8 | Typical household: morning (6–9), evening (6–10), some midday |
| Peak-to-average factor | 1.67 | Industry rule of thumb for residential loads |

For Nikhil (210 units, 30 days):
```
(210 / (30 × 8)) × 1.67 = 0.875 × 1.67 = 1.46 kW estimated peak
```

The engine labels this number as "estimated" in all user-facing responses and does not claim meter-grade accuracy.

### 6.3 Trigger threshold

The Fixed Charge Trap flag fires only when **both** conditions hold:

```
estimated_peak_kw  <  (sanctioned_load_kw - 1.0)
sanctioned_load_kw >= 2.0
```

The 1.0 kW buffer prevents false positives for households near the margin (e.g., 2.2 kW actual vs. 2 kW sanctioned). The 2 kW floor prevents recommending a 1 kW sanctioned load, which is impractical for most households.

### 6.4 Output structure

```python
fixed_charge_trap = {
    "fires": True,
    "sanctioned_load_kw": 3.0,
    "estimated_peak_demand_kw": 1.46,
    "recommended_load_kw": 2.0,
    "excess_monthly_cost": 145.00,         # (3 - 2) × 145
    "excess_annual_cost": 1740.00,         # × 12
    "reduction_process": "Requires MESCOM application and possibly a meter change. Contact MESCOM office or visit mescom.karnataka.gov.in",
    "disclaimer": "Peak demand is estimated from monthly consumption; your actual peak may differ."
}
```

### 6.5 At-scale framing

This is the pitch number. Computed on the fly for the hook:

```
MESCOM consumers:                        22,60,000
Fraction assumed overprovisioned by 1 kW:      10%
Affected households:                      2,26,000
Annual waste per household (Rs.):            1,740
Total annual waste (Rs.):           39,32,40,000
                                          ~Rs. 39.3 crore
```

This framing is explicitly conservative — the 10% assumption is below plausible reality — and the honest caveat ("reducing sanctioned load isn't a one-tap fix; it requires a MESCOM application") is volunteered in the pitch to preempt the strongest objection.

---

## 7. Subsidy Navigator Specification

The Navigator evaluates three separate subsidy programs. Each returns an eligibility verdict plus application path plus contextual notes. The Navigator never makes eligibility claims it cannot justify — when an input is unavailable, it returns `status: "insufficient_information"` with a note about what's needed.

### 7.1 PM Surya Ghar: Muft Bijli Yojana

Central government rooftop solar subsidy. Evaluation rules:

| Check | Condition | If failed |
|-------|-----------|-----------|
| Connection type | `tariff_category` starts with "LT-1" | Not eligible — "Scheme is for residential consumers" |
| Minimum consumption signal | `units_consumed >= 50` | Marginal — "Your consumption is very low; solar may not pay back" |
| Roof ownership | **Assumed** for v1; not extractable from bill | Flagged in response: "Eligibility also requires that you own your roof or have a long-term tenancy." |

Subsidy structure (tiered, capped at 3 kW):

| System size | Subsidy breakdown | Total |
|-------------|-------------------|-------|
| 1 kW | 1 × Rs. 30,000 | Rs. 30,000 |
| 2 kW | 2 × Rs. 30,000 | Rs. 60,000 |
| **3 kW** | 2 × Rs. 30,000 + 1 × Rs. 18,000 | **Rs. 78,000** |
| >3 kW | Capped at Rs. 78,000 | Rs. 78,000 |

The Navigator delegates actual system sizing to the Solar ROI Calculator and only asserts program eligibility.

### 7.2 Gruha Jyothi Visibility

The Gruha Jyothi Visibility sub-module has two purposes: (a) for enrolled beneficiaries, reveal the invisible subsidy they receive every month and warn them before any of three cliffs trigger; (b) for non-enrolled eligible households, surface the opportunity.

**Eligibility:** Any domestic (LT-1) consumer can apply. There is no BPL/APL requirement; the distinction between ration card colors does not gate eligibility for Gruha Jyothi. (This is a common misconception conflating Gruha Jyothi with Bhagyajyothi, a separate older scheme merged under Gruha Jyothi.)

**Entitlement calculation (per Karnataka Cabinet decision, 18 January 2024):**

```
historical_avg = FY 22-23 monthly average consumption for this connection
entitlement_units = min(historical_avg + 10, 200)
```

The original scheme (August 2023) used `historical_avg × 1.10`. The Cabinet switched to the flat `+10 units` formula on 18 January 2024 to benefit low-consumption households (most beneficiaries consume ≤53 units/month, for whom a 10% buffer was trivially small). Some MESCOM bills issued during the transition period (Dec 2024 – mid-2025) may still show `×1.10` computations; the Navigator tolerates both. The Navigator extracts `entitlement_units` directly from the bill when available rather than re-computing.

**The three-level cliff (this is what the bot's pitch hinges on).** Per Karnataka Gruha Jyothi scheme rules as enforced by CESC MD K.M. Munigopalraju (Star of Mysore, 23-Nov-2025), the cliff has three levels:

| Level | Trigger | Consequence | Recovery |
|-------|---------|-------------|----------|
| **0. Approaching entitlement** | Monthly consumption is close to personal entitlement (yellow at ≥75%, red at ≥90%) | Proactive warning before crossing entitlement | Clears automatically next month |
| **1. Soft step** | Monthly consumption > entitlement, but ≤ 200 units | Pay for excess units only (at standard tariff) | Automatic — next month resets |
| **2. Monthly hard cliff** | Monthly consumption > 200 units in any one month | **Pay the ENTIRE bill** for that month — no partial subsidy | Automatic — next month resets if under |
| **3. Eligibility cliff** | 10-month rolling average > 200 units | **Lose Gruha Jyothi enrollment.** One-month consumption drop does NOT restore it. | Requires re-qualification via a fresh 10-month review window |

Most GJ beneficiaries are aware of Level 1. Levels 2 and 3 are where VidyutMitra creates genuinely new value — **"almost nobody knows about the other two."**

**Warning logic:**

```python
def compute_gj_warnings(units_consumed, entitlement_units,
                        trailing_10m_avg, hypothetical_full_bill):
    entitlement_util = units_consumed / entitlement_units
    hard_cap_util    = units_consumed / 200.0
    eligibility_util = trailing_10m_avg / 200.0

    # Warning precedence: eligibility > monthly hard > approaching entitlement > soft step
    # Eligibility loss is the most severe outcome; approaching warning preserves early-action UX

    warnings = []

    # Level 3 check — eligibility at risk (most severe, flag first)
    if eligibility_util >= 0.95:
        warnings.append({
            "level": "red",
            "cliff": "eligibility",
            "message": (f"Your 10-month average is {trailing_10m_avg:.0f} units — "
                        f"just below the 200-unit disqualification limit. "
                        f"One high-consumption month could end your Gruha Jyothi "
                        f"enrollment entirely.")
        })
    elif eligibility_util >= 0.80:
        warnings.append({
            "level": "yellow",
            "cliff": "eligibility",
            "message": (f"Your 10-month average ({trailing_10m_avg:.0f} units) is "
                        f"trending toward the 200-unit eligibility limit.")
        })

    # Level 2 check — monthly hard cap (pay full bill this month)
    if hard_cap_util >= 0.95:
        warnings.append({
            "level": "red",
            "cliff": "monthly_hard",
            "message": (f"You've used {units_consumed} of 200 free units this month. "
                        f"Crossing 200 loses the ENTIRE subsidy for this month — "
                        f"you would pay Rs. {hypothetical_full_bill:,.0f}.")
        })
    elif hard_cap_util >= 0.80:
        warnings.append({
            "level": "yellow",
            "cliff": "monthly_hard",
            "message": (f"You've used {units_consumed} of 200 free units. "
                        f"Be cautious with AC and heavy appliances this billing cycle.")
        })

    # Level 0 check — approaching entitlement (proactive)
    if entitlement_util >= 0.90:
        warnings.append({
            "level": "red",
            "cliff": "approaching_entitlement",
            "message": (f"You've used {int(entitlement_util*100)}% of your "
                        f"{entitlement_units:.0f}-unit entitlement. "
                        f"Crossing entitlement starts chargeable units.")
        })
    elif entitlement_util >= 0.75:
        warnings.append({
            "level": "yellow",
            "cliff": "approaching_entitlement",
            "message": (f"You've used {int(entitlement_util*100)}% of your "
                        f"{entitlement_units:.0f}-unit entitlement. "
                        f"Keep usage in check this cycle.")
        })

    # Level 1 check — soft step (pay for excess only)
    if entitlement_util >= 1.00:
        # Already over entitlement, but still under 200
        excess_units = units_consumed - entitlement_units
        warnings.append({
            "level": "info",
            "cliff": "soft_step",
            "message": (f"You've used {excess_units:.0f} units above your "
                        f"{entitlement_units:.0f}-unit entitlement — "
                        f"you'll pay for those excess units.")
        })
    # No warnings? Full green.
    if not warnings:
        return [{"level": "green", "cliff": None, "message": None}]

    return warnings
```

**Output: the "invisible subsidy made visible" moment, with cliff intelligence.**

```python
gj_visibility = {
    "is_gj_beneficiary": True,

    # The visibility win — what Priya doesn't know she's getting
    "monthly_subsidy_received": 1080.02,
    "enrollment_date": "2023-08-26",
    "months_since_enrollment": 32,
    "estimated_total_subsidy_received": 34560.64,
    "annualized_subsidy": 12960.24,

    # Entitlement state
    "entitlement_units": 115.0,
    "units_consumed": 110,
    "entitlement_utilization_pct": 95.6,

    # The three-level cliff state
    "cliffs": {
        "approaching_entitlement": {
            "triggered": True,
            "distance_units": 5,    # entitlement - units_consumed
        },
        "soft_step": {
            "triggered": False,
            "distance_units": 5,    # entitlement - units_consumed
        },
        "monthly_hard": {
            "triggered": False,
            "distance_units": 90,   # 200 - units_consumed
            "hypothetical_full_bill_if_triggered": 2000,
        },
        "eligibility": {
            "at_risk": False,
            "trailing_10m_average": 115,
            "distance_units": 85,   # 200 - trailing_10m_avg
        }
    },

    # Composite warnings for the response composer
    "warnings": [
        {
            "level": "red",
            "cliff": "approaching_entitlement",
            "message": "You've used 96% of your 115-unit entitlement. Crossing entitlement starts chargeable units."
        }
    ],
    "overall_risk": "red",

    # The explanation most GJ beneficiaries have never heard
    "cliff_explanation": (
        "Gruha Jyothi has three separate cliffs. "
        "(1) Cross your entitlement: pay for excess units. "
        "(2) Cross 200 units in any month: pay the ENTIRE bill. "
        "(3) 10-month average above 200 units: lose the scheme entirely. "
        "Most beneficiaries know about #1. Very few know about #2 and #3."
    )
}
```

### 7.3 Solar water heater rebate

A simple rule, useful as a secondary talking point:

| Rule | Value |
|------|-------|
| Discount | Rs. 0.25 per unit on energy charges |
| Fixed-charge rebate | Rs. 25/kW/month, up to 10 kW |
| Condition | Requires BIS-certified solar water heater installation |
| Applicable tariffs | LT-1 Domestic only |

For a 210-unit household, monthly energy-charge savings = 210 × 0.25 = Rs. 52.50. Over a year, ~Rs. 630 — modest but real, and pairs well with a separate rooftop solar system on the same roof.

---

## 8. Solar ROI Calculation Methodology

### 8.1 Mangalore-specific constants

| Constant | Value | Source |
|----------|-------|--------|
| Solar irradiance (peak sun hours) | 5.55 kWh/m²/day | Global Solar Atlas, 12.87°N 74.88°E |
| Specific yield | 1,400 kWh/kWp/year | Irradiance × 365 × PR 0.69 ≈ 1,400 |
| Performance ratio assumption | 69% | Conservative for coastal humidity |
| Net metering export rate (2–3 kW) | Rs. 2.48/unit | KERC Solar Tariff Order, effective 01-Jul-2025 |
| **Grid emission factor** | **0.710 kg CO₂/kWh** | **CEA CO₂ Baseline Database Version 21.0, December 2025, FY 2024-25 weighted average** |
| Trees absorption | 30 kg CO₂/tree/year | Widely cited urban-tree benchmark for public communication |
| System cost (market average) | Rs. 55,000/kW | 2026 vendor benchmarks (market range Rs. 53,000–Rs. 72,000/kW) |
| Annual tariff escalation | ~3%/year | Historical Karnataka trend, KERC MYT orders 2015-2025 |

### 8.2 System sizing heuristic

```
annual_consumption_kwh = units_consumed × 12
target_generation_kwh  = annual_consumption_kwh × 1.1   # 10% buffer for weather variance
recommended_system_kw  = ceil(target_generation_kwh / 1400)
recommended_system_kw  = min(recommended_system_kw, 3)  # cap at subsidy ceiling
```

For Nikhil (210 units/month → 2,520 kWh/year):
```
2,520 × 1.1 / 1,400 = 1.98 → ceil = 2 kW
```

For Sunita (280 units/month → 3,360 kWh/year):
```
3,360 × 1.1 / 1,400 = 2.64 → ceil = 3 kW
```

For Priya (110 units/month → 1,320 kWh/year):
```
1,320 × 1.1 / 1,400 = 1.04 → ceil = 2 kW
```

In practice we recommend 3 kW for Nikhil too, because (a) his sanctioned load is 3 kW and (b) the PM Surya Ghar subsidy is maximized at 3 kW. This is noted as "sized to sanctioned load to maximize subsidy" in the response.

### 8.3 PM Surya Ghar subsidy (tiered)

```python
def pm_surya_ghar_subsidy(system_kw: int) -> int:
    if system_kw <= 2:
        return system_kw * 30_000
    elif system_kw == 3:
        return 60_000 + 18_000   # 2 × 30k + 1 × 18k = Rs. 78,000
    else:
        return 78_000            # Capped
```

### 8.4 Monthly benefit calculation

The monthly benefit has three components:

| Component | Computation |
|-----------|-------------|
| Grid bill displaced (variable) | `energy_charges + pg_surcharge + electricity_tax + fppca` that the consumer would otherwise pay on their actual consumption |
| Export credit | `export_kwh × 2.48` where export_kwh = max(0, generation − consumption) |
| Solar rooftop fixed-charge rebate | `system_kw × 25` per month |

Fixed charges are **not** fully displaced by solar — the consumer remains grid-connected and still pays reduced fixed charges.

For Nikhil's 3 kW system (210 units consumption, 350 units generation, 140 units exported):

| Component | Amount (Rs./month) |
|-----------|-------------------|
| Grid bill displaced (variable) | 1,508.22 |
| Export credit (140 × 2.48) | 347.20 |
| Solar rooftop rebate (3 × 25) | 75.00 |
| **Total monthly benefit** | **1,930.42** |

### 8.5 Payback and lifetime

```
cost_after_subsidy  = system_cost - pm_surya_ghar_subsidy
                    = 1,65,000 - 78,000 = Rs. 87,000

payback_months      = cost_after_subsidy / monthly_benefit
                    = 87,000 / 1,930.42 = 45.07 months ≈ 3.8 years
```

**Nikhil verified payback: 45 months ≈ 3.8 years.**

25-year lifetime (two scenarios):

```
Scenario A — flat tariffs (conservative, defensive pitch number):
  gross_savings        = 25 × 12 × monthly_benefit = Rs. 5,79,126
  less: system cost                                 -  87,000
  less: panel degradation (avg 6% over life)        -  36,000
  less: one inverter replacement (year 12-15)       -  25,000
                                                    ──────────
  net_25yr_savings                                 ≈ Rs. 4,31,126
                                                    ~Rs. 4.3 lakh

Scenario B — 3% annual tariff escalation (realistic, Karnataka historical trend):
  gross_savings        = 1,930 × 12 × ((1.03^25 - 1) / 0.03)
                       ≈ Rs. 8,44,000
  less: system cost + degradation + inverter        -  1,48,000
                                                    ──────────
  net_25yr_savings                                 ≈ Rs. 6,96,000
                                                    ~Rs. 6.9 lakh
```

**Pitch-time framing:** lead with Rs. 4.3 lakh (conservative, flat tariffs), note Rs. 6.9 lakh as the realistic upside factoring in the ~3% annual tariff escalation Karnataka has actually seen over the last decade. This preempts the smart judge who asks "but tariffs rise every year."

### 8.6 CO₂ offset

```
annual_generation_kwh × 0.710 kg/kWh / 1000 = tonnes_CO2_per_year
4,200 × 0.710 / 1000 = 2.98 tonnes/year

trees_equivalent = annual_CO2_kg / 30 kg/tree/year
                 = 2,982 / 30 ≈ 99 trees/year (~100)
```

Emission factor source: CEA CO₂ Baseline Database Version 21.0, December 2025, FY 2024-25 weighted average. Tree absorption rate: 30 kg CO₂/tree/year for a conservative, widely-cited urban-tree equivalent.

### 8.7 GJ beneficiary special case

For Gruha Jyothi-enrolled households with `units_consumed / entitlement_units < 0.9`, the Calculator returns `recommendation: "not_recommended"` with this reasoning:

```
Your grid electricity is effectively free under Gruha Jyothi. Solar displaces
something you aren't paying for, making the investment much slower to pay back.

Consider solar when you're approaching the three-level cliff:
• Monthly consumption trending toward 200 units
• 10-month rolling average approaching 200 units
• Already paying for excess units above your entitlement

At that point, solar stops competing with "free" grid electricity and starts
competing with a looming full-bill scenario (Rs. 1,500-2,500/month if you cross
200 units, plus the risk of losing enrollment entirely).
```

This is an honest outcome that VidyutMitra will surface rather than hide — and it models the intellectual discipline the pitch emphasizes. The recommendation also doubles as a prompt for the consumer to watch their consumption trajectory, which is the Gruha Jyothi Visibility module's core value proposition.

### 8.8 Output structure

```python
solar_roi = {
    "recommended_system_kw": 3,
    "recommendation": "recommended",      # recommended / marginal / not_recommended
    "recommendation_reason": "Non-GJ household with full bill liability",
    "system_cost_before_subsidy": 1_65_000,
    "pm_surya_ghar_subsidy": 78_000,
    "cost_after_subsidy": 87_000,
    "specific_yield_kwh_per_kwp_year": 1400,
    "annual_generation_kwh": 4200,
    "monthly_generation_kwh": 350,
    "monthly_self_consumption_kwh": 210,
    "monthly_export_kwh": 140,
    "monthly_grid_bill_displaced": 1508.22,
    "monthly_export_credit": 347.20,
    "monthly_solar_fixed_rebate": 75,
    "monthly_total_benefit": 1930.42,
    "payback_months": 45,
    "payback_years": 3.8,
    "lifetime_years": 25,
    "lifetime_gross_savings_flat_tariffs": 5_79_126,
    "lifetime_net_savings_flat_tariffs": 4_31_000,
    "lifetime_gross_savings_3pct_escalation": 8_44_000,
    "lifetime_net_savings_3pct_escalation": 6_96_000,
    "co2_offset_tonnes_per_year": 2.98,
    "trees_equivalent_per_year": 100,
    "net_metering_export_rate": 2.48,
    "emission_factor_source": "CEA CO2 Baseline Database v21.0, December 2025",
    "assumptions": [
        "System cost Rs. 55,000/kW (market avg; vendor range Rs. 53K-Rs. 72K/kW)",
        "Specific yield 1,400 kWh/kWp/year (Global Solar Atlas for Mangalore, 12.87degN 74.88degE)",
        "Performance ratio ~69% baked into specific yield (coastal humidity)",
        "Grid emission factor 0.710 kg CO2/kWh (CEA v21 Database, Dec 2025, FY 2024-25 weighted average)",
        "Tree absorption 30 kg CO2/tree/year (widely-cited urban benchmark)",
        "Net metering export Rs. 2.48/unit for 2-3 kW systems (KERC Solar Order, 01-Jul-2025)",
        "Solar rooftop fixed-charge rebate Rs. 25/kW/month (KERC LT-1 Note (b))",
        "25-year degradation ~6% cumulative; one inverter replacement at year 12-15",
        "Flat-tariff lifetime is conservative; Karnataka's historical 3%/year escalation (2015-2025) gives the realistic upside figure"
    ]
}
```

---

## 9. DPDPA Compliance Design

The Digital Personal Data Protection Act, 2023 (DPDPA) governs personal data processing in India. MESCOM bills contain PII: consumer name, address (implicit from RR), consumption history. VidyutMitra treats DPDPA compliance as a first-class feature, not a compliance checkbox.

### 9.1 Consent flow

No bill data is processed without explicit opt-in.

```
State: user does not exist in `users` table
  → Any inbound message → Consent message sent, users row inserted with consent_given = false
  → User replies "START" → consent_given = true
  → User replies "STOP" → row deleted, no data ever persisted
  → User sends bill photo → "Please reply START to accept consent" — image NEVER sent to Gemini
```

Consent is version-agnostic in v1. A future v2 could attach a `consent_version` column and require re-consent on policy updates.

### 9.2 Data minimization

Three architectural choices enforce minimization:

| Choice | Implementation |
|--------|----------------|
| Raw bill images are never written to disk | Image bytes are read from Twilio into a Python `bytes` variable, passed to Gemini, then the variable goes out of scope. No `open(..., 'wb')` call exists anywhere in the path. |
| Only extracted text fields persist | The `bills` table schema has no `bill_image`, `bill_url`, or similar column. |
| No cross-user analytics with PII | The admin dashboard queries aggregate views only (`COUNT`, `AVG`, `GROUP BY tariff_category`). Individual phone numbers and consumer names never appear in any dashboard chart or API response. |

### 9.3 STOP command semantics

```sql
-- STOP handler
BEGIN;
DELETE FROM users WHERE phone_number = :phone_number;
-- ON DELETE CASCADE on bills.user_id removes all bill records
COMMIT;
```

Properties:

- **Immediate**: executes before any other processing of the message
- **Hard delete**: not a soft delete, no `deleted_at` column, no recovery possible
- **Irreversible**: confirmation message in Kannada and English
- **Pre-consent safe**: if the user never sent START, the STOP deletes only the placeholder `users` row and replies "no data was ever processed"

### 9.4 Retention policy

For v1, there is no time-based retention purge. Users retain their data until they send STOP. A v2 addition would be a scheduled job that deletes bills older than 24 months, retaining only a 12-month consumption average in an anonymized analytics table.

### 9.5 Admin dashboard protections

The Streamlit admin dashboard is the one place where aggregate analysis runs. To avoid it becoming a PII exposure vector:

| Protection | Implementation |
|------------|----------------|
| Aggregate queries only | Every SQL query in the dashboard uses `GROUP BY`, `COUNT`, `AVG`, `SUM`. No query returns individual user rows. Enforced by code review. |
| No PII in output | No chart, table, or export contains `phone_number`, `consumer_name`, or `rr_number`. |
| Password-protected URL | Streamlit deployment uses HTTP basic auth via a reverse proxy (Railway built-in, or Nginx for self-host). Single password in env var, rotated after demo day. |
| Not indexed | Dashboard URL is not listed anywhere public; a `robots.txt` disallows indexing. |

### 9.6 Cross-border data transfer

For the hackathon prototype, Supabase's default region is used (US-East). Production deployment would use `ap-south-1` (Mumbai) for data residency. This is acknowledged as a known gap and is the correct v2 fix; it is not a blocker for the demo.

---

## 10. Database Schema

```sql
-- =============================================================
-- USERS
-- One row per phone number that has interacted with VidyutMitra
-- =============================================================
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    consent_given BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    CONSTRAINT phone_number_format CHECK (phone_number ~ '^\+[1-9]\d{6,14}$')
);

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_users_consent ON users(consent_given) WHERE consent_given = TRUE;

-- Trigger to update updated_at on any row modification
CREATE OR REPLACE FUNCTION update_modified_column() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE update_modified_column();

-- =============================================================
-- BILLS
-- One row per analyzed bill. DELIBERATELY no bill_image column.
-- =============================================================
CREATE TABLE bills (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,

    -- Billing period
    billing_period_start DATE,
    billing_period_end DATE NOT NULL,
    billing_period_days INTEGER,

    -- Consumer & connection
    tariff_category TEXT,           -- "LT-1" after normalization
    rr_number TEXT,                  -- Consumer account number
    sanctioned_load_kw REAL,

    -- Consumption
    previous_reading INTEGER,
    current_reading INTEGER,
    units_consumed INTEGER NOT NULL,

    -- Pre-subsidy charges (Sub-Total-1 components)
    energy_charges REAL,
    fixed_charges REAL,
    pg_surcharge REAL,
    electricity_tax REAL,
    fppca REAL,
    other_charges REAL,
    subtotal_1 REAL,

    -- Gruha Jyothi (nullable for non-GJ)
    is_gj_beneficiary BOOLEAN DEFAULT FALSE NOT NULL,
    gj_registration_date DATE,
    historical_avg_baseline REAL,
    entitlement_units REAL,
    units_eligible_for_subsidy REAL,
    units_chargeable REAL,
    gj_subsidy_amount REAL,

    -- Final bill
    net_bill_amount REAL,

    -- Full analysis blob — denormalized for dashboard speed
    analysis_result JSONB,

    -- Metadata
    extraction_confidence REAL,     -- Gemini's self-reported signal, for audit
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Data quality constraints
    CONSTRAINT units_positive CHECK (units_consumed > 0 AND units_consumed <= 10000),
    CONSTRAINT load_positive CHECK (sanctioned_load_kw > 0 AND sanctioned_load_kw <= 50),
    CONSTRAINT period_post_april CHECK (billing_period_end >= DATE '2025-04-01')
);

CREATE INDEX idx_bills_user ON bills(user_id);
CREATE INDEX idx_bills_gj ON bills(is_gj_beneficiary) WHERE is_gj_beneficiary = TRUE;
CREATE INDEX idx_bills_period ON bills(billing_period_end);
CREATE INDEX idx_bills_user_period ON bills(user_id, billing_period_end DESC);
```

### 10.1 Column rationale

| Column | Why |
|--------|-----|
| `users.phone_number UNIQUE` | Phone is the natural identity key |
| `users.consent_given` | Hard gate; checked on every inbound message |
| **Absence of `bills.bill_image`** | **Core DPDPA feature.** Raw bill images are never stored. This is deliberate and visible in the schema for auditability. |
| `bills.analysis_result JSONB` | Denormalized analysis payload for dashboard speed; avoids re-running analysis when rendering history |
| `bills.is_gj_beneficiary INDEX` | Partial index; only indexes the GJ subset for fast "how many GJ users do we have" queries |
| `bills.period_post_april CHECK` | Enforces the "v1 only handles post-April 2025 bills" policy at the database level |
| `ON DELETE CASCADE` | STOP command deletes user; cascade removes all bills in one transaction |

---

## 11. API Surface

The backend exposes a minimal Flask API. Only the Twilio webhook is publicly reachable; health and admin are internal.

### 11.1 `POST /whatsapp` — Twilio webhook

Consumed by Twilio WhatsApp Sandbox. Form-encoded body.

| Field | Type | Example | Source |
|-------|------|---------|--------|
| `From` | string | `whatsapp:+919876543210` | User's WhatsApp ID |
| `To` | string | `whatsapp:+14155238886` | Our sandbox number |
| `Body` | string | `START` or `STOP` or free text | User message |
| `NumMedia` | integer | `0` or `1` | Number of attached media |
| `MediaUrl0` | string | `https://api.twilio.com/.../ME...` | First media URL (if any) |
| `MediaContentType0` | string | `image/jpeg` | MIME type |

Response: TwiML XML. Example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>
        <Body>⏳ Analyzing your bill...</Body>
    </Message>
</Response>
```

The main response (text, voice, infographic) is sent via **out-of-band** Twilio REST API calls after processing completes, not in the webhook response — because processing takes 8–12 seconds and Twilio expects webhook responses in <15 seconds with a preference for <5.

### 11.2 `GET /health` — Liveness probe

```json
{
  "status": "ok",
  "timestamp": "2026-04-17T14:30:00Z",
  "version": "1.0.0",
  "gemini_reachable": true,
  "supabase_reachable": true
}
```

### 11.3 `POST /upload` — Web fallback UI (internal only)

Used only when Twilio/WhatsApp is down. A minimal HTML form that accepts a phone number + image file, runs the same extraction pipeline, and returns the analysis as an HTML page. Not exposed in the public demo flow; kept as insurance.

### 11.4 Streamlit admin dashboard

Separate Streamlit app at `/admin` (or a different subdomain). Not a Flask endpoint. Queries Supabase directly via `supabase-py` client, using aggregate SQL only.

---

## 12. Environment and Deployment

### 12.1 Environment variables

```bash
# .env — NEVER committed to the repository

# Gemini
GEMINI_API_KEY=<Google AI Studio key>

# Twilio
TWILIO_ACCOUNT_SID=<Twilio Account SID>
TWILIO_AUTH_TOKEN=<Twilio Auth Token>
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Supabase
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_KEY=<anon public key>

# Google Cloud Text-to-Speech
GOOGLE_APPLICATION_CREDENTIALS=<path to service account JSON>
GCP_PROJECT_ID=<project id>
KANNADA_VOICE_ID=<Kannada voice id>

The implementation should use the AWS SDK default credential chain in production if available, and return MP3 audio for WhatsApp delivery.

# Admin dashboard auth
ADMIN_PASSWORD=<strong random string>

# App
FLASK_ENV=production
PUBLIC_BASE_URL=https://vidyutmitra.up.railway.app
```

### 12.2 Hosting

| Component | Host | Rationale |
|-----------|------|-----------|
| Flask backend | Railway (primary) / Render (backup) | Node.js-free Python hosting; git-based deploy; built-in HTTPS |
| Twilio webhook URL | `https://vidyutmitra.up.railway.app/whatsapp` | Set in Twilio Sandbox configuration |
| Supabase Postgres | Supabase Cloud (default region for v1, `ap-south-1` for v2) | Managed Postgres with REST API; adequate free tier |
| Streamlit admin dashboard | Streamlit Community Cloud | Free tier; built-in auth via `st.secrets` |
| Demo fallback JSON | Bundled into Flask repo | Zero external dependency for the critical fallback path |

### 12.3 Local development setup

```bash
# Clone
git clone git@github.com:team-cube/vidyutmitra.git
cd vidyutmitra

# Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Environment
cp .env.example .env
# Fill in actual keys

# Database migrations (one-time)
python scripts/init_supabase_schema.py

# Run Flask locally
flask run --port 5001

# In another terminal, expose via ngrok for Twilio testing
ngrok http 5001
# Paste the ngrok URL into the Twilio Sandbox webhook configuration

# Run Streamlit admin
streamlit run admin/dashboard.py
```

### 12.4 Dependencies

```txt
# requirements.txt
flask==3.0.0
google-generativeai==0.8.3
twilio==9.0.0
supabase==2.5.0
google-cloud-texttospeech==2.16.0
Pillow==10.2.0
python-dotenv==1.0.0
streamlit==1.32.0
requests==2.31.0
```

---

## 13. Error Handling and Fallback Ladder

### 13.1 Error-to-message mapping

| Condition | User-facing message |
|-----------|---------------------|
| Unconsented user, any message | "I need your consent before analyzing bills. Please reply START to accept the privacy terms, or STOP to opt out." |
| STOP from consented user | "✅ All your data has been permanently deleted. Send any message to start fresh." |
| STOP from unconsented user | "Understood, no data was ever processed. Feel free to return anytime." |
| Non-MESCOM bill / unreadable | "❌ I couldn't read that as a MESCOM bill. Tips: flat surface, good lighting, full bill in frame, not blurry. 📸 Please try again." |
| Pre-April 2025 bill | "📅 This bill is from before April 2025. KERC updated the tariff structure in April 2025. I currently analyze bills from April 2025 onward. 📸 Please send a more recent bill." |
| Gemini timeout/5xx | "⚠️ I'm having trouble analyzing your bill right now. Please try again in a minute. / ದಯವಿಟ್ಟು ಒಂದು ನಿಮಿಷ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ." |
| Twilio media fetch fails | "Couldn't retrieve your photo. Please send it again." |
| Supabase write fails | (Log error; still respond to user with analysis — best-effort persistence) |
| User sends >2 follow-ups without new bill | "📸 Send a new bill photo for a fresh analysis, or visit mescom.karnataka.gov.in for more information." |

### 13.2 Demo day fallback ladder

These are rehearsed in order. Each step is roughly 2 seconds of on-stage narration while the teammate executes the transition in the background.

```
LEVEL 1 — HAPPY PATH
  Demo phone → Twilio sandbox → live Gemini call → response in 8-12 sec.

LEVEL 2 — GEMINI FAILURE
  Gemini times out or returns 5xx.
  Script: "Our system caches every extraction — here's what it returned 10 minutes ago in our last test."
  System: extract_with_fallback() loads demo_fallbacks.json entry for the demo phone.
  Response still renders normally.

LEVEL 3 — TWILIO/WHATSAPP FAILURE
  Sandbox unreachable, or session window expired, or rate-limited.
  Script: "Let me show you our web fallback — same engine, different channel."
  Wasih switches to the /upload web form, uploads the same bill, gets the same analysis rendered on the page.

LEVEL 4 — EVERYTHING FAILS
  Script: "Let me show you the full end-to-end flow from a demo we recorded this morning."
  Pre-recorded 90-second demo video plays full-screen on the laptop. Wasih narrates over it in real time.

LEVEL 5 — ABSOLUTE FLOOR
  If nothing above works — laptop dead, phone dead, network dead — Wasih walks through printed screenshots of the three persona flows.
```

Every judge question must land inside Level 1 or 2. Levels 3–5 exist so that if the live demo dies, the pitch doesn't.

---

## 14. Scalability Considerations

### 14.1 MESCOM → all Karnataka ESCOMs

The architecturally important fact: **KERC issues a single Combined Tariff Order covering BESCOM, MESCOM, CESC, HESCOM, and GESCOM.** Base rates (fixed charges, energy charges, P&G surcharge, solar rebate) are identical across all five. What differs:

- Bill format templates
- Tariff code conventions ("2LT1" vs "LT-1" vs "LT-2A" depending on ESCOM)
- Minor format variations for Gruha Jyothi presentation
- Customer-facing portal URLs
- SRTPV portal URLs

Migration path: **config changes only, no code changes.**

```python
# config/escoms.py
ESCOM_CONFIGS = {
    "MESCOM": {
        "name": "Mangalore Electricity Supply Company",
        "districts": ["Dakshina Kannada", "Udupi", "Chikmagalur", "Shivamogga"],
        "consumer_portal": "mescom.karnataka.gov.in",
        "srtpv_portal": "srtpv.mesco.in",
        "tariff_code_variants": ["2LT1", "LT-1", "LT1"],
        "bill_format_hints": {
            "gj_subsection_keyword": "Gruha Jyothi Subsidy",
            "subtotal_label_primary": "Sub-Total-1",
            "subtotal_label_secondary": "Sub-Total-2",
        }
    },
    "BESCOM": {
        "name": "Bangalore Electricity Supply Company",
        "districts": ["Bangalore Urban", "Bangalore Rural", "Tumkur", "Chitradurga", "Davanagere", "Ramanagara"],
        "consumer_portal": "bescom.karnataka.gov.in",
        "tariff_code_variants": ["LT-2(a)", "LT2A"],
        # ...
    },
    # HESCOM, GESCOM, CESC ...
}

TARIFF_CONSTANTS_FY_2025_26 = {
    # Shared across all Karnataka ESCOMs per KERC Combined Tariff Order
    "fixed_charge_per_kw": 145.0,
    "energy_charge_per_unit": 5.80,
    "pg_surcharge_per_unit": 0.36,
    "electricity_tax_pct": 0.09,
    "solar_fixed_rebate_per_kw": 25.0,
}
```

Files that need changes to add a new Karnataka ESCOM:

| File | Change |
|------|--------|
| `config/escoms.py` | Add ESCOM entry |
| `extraction/gemini_prompt.py` | Add ESCOM name to prompt (one line) |
| `tests/sample_bills/<escom>/` | Add 3–5 sample bills for test coverage |

Files that do **not** need changes:

| File | Why |
|------|-----|
| `analysis/tariff_engine.py` | Shared tariff constants apply unchanged |
| `analysis/subsidy_navigator.py` | PM Surya Ghar and Gruha Jyothi are state/central, not ESCOM-specific |
| `analysis/solar_roi.py` | Solar irradiance varies slightly by region, but formula is shared; add per-ESCOM irradiance as a config value |
| `db/schema.sql` | Same |

**Time estimate for adding a new Karnataka ESCOM: 2–3 hours** (mostly test coverage).

### 14.2 Karnataka → all-India

Other states have different regulatory commissions (TNERC, MERC, APERC, etc.) with different tariff structures, different surcharge orders, different rooftop-solar policies. This is **code changes, not config changes**.

Migration approach:

| Step | What it requires |
|------|------------------|
| Add a new state | New `TARIFF_CONSTANTS` module; new Gemini prompt tuned to that state's bill format |
| State-specific analysis | Some modules (`fixed_charge_trap`) generalize; others (`gruha_jyothi_visibility`) are Karnataka-specific and become `state_subsidy_visibility` with a state-specific strategy pattern |
| Language support | Each state has its own language(s); TTS endpoints expand; prompt templates duplicate per-language |
| Vendor/portal links | Per-state lookup table |

**Time estimate per new state: 2–3 weeks** for a small team.

VidyutMitra's v1 positioning is deliberately MESCOM-only. The "we're MESCOM-calibrated, not generic" framing is both product strength and technical strength — going national is a future milestone, not a pitch claim.

---

## 15. Known Limitations and Future Work

V1 is honest about what it does not do. These limitations are acknowledged in the pitch so judges cannot weaponize them.

| Limitation | Why excluded from v1 | Path to addressing |
|------------|---------------------|--------------------|
| **No Kannada speech-to-text (Bhashini STT)** | Voice is one-way (TTS out only). Users must type follow-ups. Integrating Bhashini adds 6–8 hours and has marginal demo impact. | v2: Integrate Bhashini STT for voice-reply support. Enables true feature-phone-adjacent UX. |
| **No commercial tariff support (LT-2 / LT-3 / LT-4)** | LT-3 Commercial has different fixed charges (Rs. 215/kW) and energy rates (Rs. 7.00/unit) with no Gruha Jyothi analog. Demands a separate analysis engine. | v2: Add LT-3 Commercial as a second tariff config; flag appropriate subsidies (MSME schemes, not Gruha Jyothi). |
| **Conversational follow-up limited to 2 turns** | Full NLU would require LLM-based intent parsing; adds latency and complexity; not needed for the core insight delivery. | v2: Add Gemini-based intent classifier for free-form follow-up questions; cap at 5 turns to prevent abuse. |
| **No feature phone support** | WhatsApp-first by design; feature phones can't run WhatsApp. | v3: IVR-based version using exotel or KooKoo for users without smartphones. |
| **No payment integration** | PhonePe, GPay, Paytm all handle MESCOM bill payments well. Not our differentiator. | Permanent: redirect users to existing payment apps via deep links. |
| **No vendor marketplace** | Recommending specific solar installers creates liability. We link to the MESCOM-empaneled vendor list instead. | v2: Partner with MESCOM for a vetted vendor directory with reviews. |
| **Pre-April 2025 bills not supported** | Bill structure and rates are fundamentally different. Supporting both doubles the tariff configuration burden. | Won't fix. Pre-April 2025 bills are increasingly historical; we gracefully redirect users to send recent bills. |
| **Gemini extraction confidence not measured against ground truth** | v1 relies on structural validation (bill math must sum correctly). A proper F1 evaluation against 200+ labeled bills is future work. | v2: Build a labeled test set of 200 diverse MESCOM bills; measure extraction F1; iterate on prompt. |
| **No multi-bill trend analysis** | Rendered as a pre-made chart in the admin dashboard for demo purposes; not live. | v2: Compute month-over-month delta in the per-user response. ~2 hours of additional work. |
| **Data residency uses Supabase default region (US-East)** | Hackathon prototype convenience; DPDPA allows transfer with consent. | v2: Migrate to Supabase `ap-south-1` (Mumbai); add data residency note to consent message. |
| **Single-language response (Kannada + English)** | Coastal Karnataka speaks Tulu, Konkani, Beary in addition to Kannada. Not addressed in v1. | v3: Expand TTS to Tulu and Konkani via Bhashini; English fallback for Beary speakers. |

Each of these limitations has a thought-through path forward. The pitch position: *"We scoped tightly so we could ship something that works, not widely so we could claim everything."*

---

**End of Technical Specification.**

For implementation details and persona math, see `VidyutMitra_Verified_Tariff_v3.md` and `VidyutMitra_PRD_v3.md`. For pitch materials and rehearsal notes, see `VidyutMitra_Briefing_Document_v2.md` (to be updated to reflect this spec).
