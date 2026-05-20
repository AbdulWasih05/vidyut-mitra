# VidyutMitra — Product Requirements Document (v2)

**Version:** 2.0 | **Date:** April 17, 2026 | **Team:** Cube (2 developers)
**Hackathon:** Hackfest'26, NMAMIT Nitte | **Track:** Sustainable Development
**Build window:** 36 hours | **Demo:** 5 minutes
**Source of truth for numbers:** `VidyutMitra_Verified_Tariff_v2.md`

> **Scope rule:** If it isn't MUST-tier, it gets zero engineering time until every MUST item is green. No exceptions.
> **What changed from v1:** Slab Optimizer module killed (KERC removed slabs in FY 2025-26). Replaced with Gruha Jyothi Visibility module. Persona 2 replaced (Fathima commercial → Sunita domestic solar hero). Tariff code is LT-1, not LT-2(a). Energy rate is flat ₹5.80/unit. Electricity tax is 9%. Pre-April 2025 bills are gracefully declined.
>
> **What changed from v2 → v3 (April 17 PM):** Grid emission factor 0.82 → 0.710 kg CO₂/kWh (CEA v21, Dec 2025). CO₂ offset 3.44 → 2.98 tonnes/year; trees 115 → ~100 (30 kg CO₂/tree/year benchmark). Gruha Jyothi single-cliff model replaced with three-level cliff (soft step / monthly hard cliff / eligibility cliff). 25-year solar savings now presented as flat-tariff (Rs. 4.3 lakh) and 3%-escalation (Rs. 6.9 lakh) scenarios.

---

## 1. User Personas

Each persona anchors exactly one hero module, so the three-demo-scenario demo maps cleanly to the three analytical modules.

### Persona 1: Nikhil Shetty — The Remote Son (Fixed Charge Trap hero)

| Field | Detail |
|---|---|
| **Age** | 27 |
| **Location** | Works in Bengaluru, parents in Surathkal (Dakshina Kannada) |
| **Connection** | LT-1 Domestic, 3 kW sanctioned |
| **Gruha Jyothi** | Not enrolled |
| **Monthly consumption** | 210 units |
| **Actual peak demand (estimated)** | ~1.5 kW |
| **Current bill** | ₹1,943/month |

**Current pain:** Pays his parents' MESCOM bill via PhonePe every month. Doesn't know their 3 kW sanctioned load is ~2× their actual peak demand, costing them ₹1,740/year in unnecessary fixed charges. Has heard about PM Surya Ghar but doesn't know if it applies.

**What VidyutMitra does:** Forwards the bill photo his mother sends him. Bot flags the Fixed Charge Trap with the ₹1,740/year number, verifies PM Surya Ghar eligibility (3 kW system, ₹78K subsidy, 3.8-year payback), returns Kannada voice summary.

---

### Persona 2: Sunita Bhat — The Homemaker (Solar ROI hero)

| Field | Detail |
|---|---|
| **Age** | 45 |
| **Location** | Chikmagalur town |
| **Connection** | LT-1 Domestic, 3 kW sanctioned |
| **Gruha Jyothi** | Eligible but **not enrolled** (honest reflection of 0.2% awareness gap) |
| **Monthly consumption** | 280 units |
| **Actual peak demand** | ~2 kW (appropriately sized — no Fixed Charge Trap) |
| **Current bill** | ₹2,446/month |

**Current pain:** Family of five (coffee-estate-manager husband, two school kids, mother-in-law). Bill has been climbing. Eligible for Gruha Jyothi via Karnataka One portal but has never applied — her husband thinks "it's for poor people." Own south-facing roof, neighbor just installed solar, she's curious but doesn't know where to start.

**What VidyutMitra does:** Computes solar ROI for 3 kW system: ₹87K net cost after subsidy, ₹2,260 monthly savings, 3.2-year payback, ₹5.3 lakh 25-year savings at flat tariffs (₹8.5 lakh at 3% annual escalation), 2.98 tonnes/year CO₂ offset. Also flags that she's eligible for Gruha Jyothi and explains the application path.

---

### Persona 3: Priya Nayak — The College Student (Gruha Jyothi Visibility hero)

| Field | Detail |
|---|---|
| **Age** | 20 |
| **Location** | College at Manipal, family home in Udupi district |
| **Connection** | LT-1 Domestic, 2 kW sanctioned |
| **Gruha Jyothi** | **Enrolled since August 2023** |
| **Monthly consumption** | 110 units (entitlement: 115 units) |
| **Current bill** | **₹0.00/month** (Sub-Total-1: ₹1,080, fully subsidized) |

**Current pain:** Her family thinks "electricity is free because we applied for the Congress scheme" — they don't know they're receiving ₹12,960/year in state subsidy, or that a single month over 200 units would cost them the whole subsidy for that month. Priya is tech-savvy, has never looked closely at the bill.

**What VidyutMitra does:** Extracts the Sub-Total-1 / Sub-Total-2 structure, reveals the invisible subsidy (~₹34,500 since enrollment), warns about three separate cliffs (pay for excess above entitlement, lose whole month's subsidy above 200 units, lose eligibility if 10-month average exceeds 200), explains what would happen if consumption exceeds entitlement (a ~₹2,000 bill, not ₹0). Solar is explicitly **not** recommended for her family (honest).

---

## 2. User Journey Map

### 2.1 First-Time User Flow (Non-GJ Consumer — e.g., Nikhil)

```
STEP 1 — FIRST CONTACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User sends:  "Hi"

Bot replies:
┌─────────────────────────────────────────────┐
│ 🔌 VidyutMitra — MESCOM Bill Advisor        │
│                                             │
│ Welcome! I help you understand your MESCOM  │
│ electricity bill, find savings, and check   │
│ government subsidy eligibility.             │
│                                             │
│ 🔒 Privacy Notice / ಗೌಪ್ಯತೆ ಸೂಚನೆ:         │
│ • I extract data from your bill photo       │
│   (units, charges, sanctioned load)         │
│ • I store ONLY extracted text data — your   │
│   bill image is NEVER saved                 │
│ • Your data is linked to your phone number  │
│ • Send STOP at any time to permanently      │
│   delete all your data                      │
│                                             │
│ ನಿಮ್ಮ ಬಿಲ್ ಫೋಟೋದಿಂದ ಮಾಹಿತಿ ಮಾತ್ರ          │
│ ತೆಗೆಯಲಾಗುತ್ತದೆ. ಚಿತ್ರವನ್ನು ಉಳಿಸಲಾಗುವುದಿಲ್ಲ. │
│ STOP ಕಳುಹಿಸಿ ಎಲ್ಲಾ ಡೇಟಾ ಅಳಿಸಲು.            │
│                                             │
│ Reply START to continue / STOP to opt out.  │
└─────────────────────────────────────────────┘

System: users row created, consent_given = false
```

```
STEP 2 — CONSENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User sends:  "START"

Bot replies:
┌─────────────────────────────────────────────┐
│ ✅ Thank you! You're all set.               │
│                                             │
│ 📸 Send a photo of your MESCOM electricity  │
│ bill (from April 2025 or later) and I'll    │
│ analyze it for you.                         │
│                                             │
│ ನಿಮ್ಮ MESCOM ವಿದ್ಯುತ್ ಬಿಲ್ ಫೋಟೋ ಕಳುಹಿಸಿ.  │
└─────────────────────────────────────────────┘

System: consent_given = true
```

```
STEP 3 — BILL PROCESSING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User sends:  [MESCOM bill photo — Nikhil's parents' March 2026 bill]

Bot replies (acknowledgment):
┌─────────────────────────────────────────────┐
│ ⏳ Analyzing your bill...                   │
│    ನಿಮ್ಮ ಬಿಲ್ ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ...       │
└─────────────────────────────────────────────┘

System: Image bytes → Gemini 2.5 Flash
        → Validated JSON
        → Check billing period ≥ 2025-04 (else: pre-April-2025 decline)
        → Check is_gruha_jyothi_beneficiary branch
        → Run analysis modules (M2, M3, M4, M5)
        → Discard image bytes
        → Write extracted+analysis to Supabase
```

```
STEP 4 — NON-GJ ANALYSIS RESPONSE (Nikhil's flow)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────┐
│ 📊 VidyutMitra Bill Report                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━                 │
│ 📅 Period: Mar 2026                         │
│ ⚡ Units consumed: 210                       │
│ 🔌 Sanctioned load: 3 kW                   │
│ 💰 Total bill: ₹1,943                      │
│                                             │
│ ━━ Bill Verification ━━                     │
│ ✅ Energy charges match KERC tariff         │
│   (210 units × ₹5.80 flat rate)             │
│                                             │
│ ━━ ⚠️ Fixed Charge Alert ━━                 │
│ Your sanctioned load is 3 kW but typical    │
│ usage suggests ~1.5 kW peak demand.         │
│ You may be paying ₹145/month extra in       │
│ fixed charges — that's ₹1,740/year.         │
│                                             │
│ Reducing to 2 kW requires a MESCOM          │
│ application and possibly a meter change.    │
│                                             │
│ ━━ Subsidy Eligibility ━━                   │
│ ☀️ PM Surya Ghar: ELIGIBLE                  │
│   → 3 kW system, ₹78,000 subsidy            │
│   → Payback: ~3.8 years                     │
│   → Apply: pmsuryaghar.gov.in               │
│                                             │
│ 🏠 Gruha Jyothi: ELIGIBLE but not enrolled  │
│   → Covers bills up to 200 units/month      │
│   → Apply via Karnataka One / Seva Sindhu   │
│                                             │
│ ━━ Solar ROI (3 kW system) ━━               │
│ 🔋 Annual generation: ~4,200 kWh            │
│ 💰 Monthly savings: ~₹1,930                 │
│ ⏱️ Payback: 3.8 years                       │
│ 🎯 25-year net savings: ~₹4.3 lakh          │
│ 🌱 CO₂ offset: 2.98 tonnes/year             │
│                                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━                 │
│ Reply:                                      │
│ 1️⃣ SOLAR — detailed solar breakdown         │
│ 2️⃣ FIXED — explain my fixed charges         │
│ Or send another bill photo anytime.         │
└─────────────────────────────────────────────┘

Bot also sends: [Kannada voice note via Google
TTS summarizing: bill amount, Fixed Charge
Trap flag, solar payback]

Bot also sends: [Pre-rendered infographic with
Nikhil's specific numbers substituted]
```

### 2.2 GJ Beneficiary Flow (Priya's family bill)

```
STEP 4b — GJ ANALYSIS RESPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────────────────────────────────────┐
│ 📊 VidyutMitra Bill Report                  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━                 │
│ 📅 Period: Mar 2026                         │
│ ⚡ Units consumed: 110                       │
│ 🔌 Sanctioned load: 2 kW                   │
│ 💰 You paid: ₹0                            │
│                                             │
│ ━━ 🎁 Gruha Jyothi Benefit ━━               │
│ This month the Karnataka government         │
│ paid ₹1,080 on your behalf:                 │
│                                             │
│   Energy charges:         ₹638              │
│   Fixed charges:          ₹290              │
│   Taxes & surcharges:     ₹152              │
│   ━━━━━━━━━━━━━━━━━━━                       │
│   Subsidy received:     ₹1,080              │
│                                             │
│ 📅 Enrolled since: Aug 2023                 │
│ 💰 Total subsidy received: ~₹34,500         │
│    Annual rate: ~₹12,960/year               │
│                                             │
│ ━━ ⚠️ Entitlement Cliff Warning ━━          │
│ Your monthly entitlement is 115 units.      │
│ This month you used 110 units (96%).        │
│                                             │
│ You're in the RED approaching zone          │
│ (>=90% of entitlement). Crossing 115        │
│ starts chargeable units immediately.        │
│                                             │
│ If any single month exceeds 200 units,      │
│ you lose the ENTIRE subsidy for that        │
│ month — not just on the excess. A bill      │
│ like yours would then cost ~₹2,000.         │
│                                             │
│ Watch consumption during summer (AC) or     │
│ when guests stay.                           │
│                                             │
│ ━━ Solar recommendation ━━                  │
│ 🔄 Because your bill is already ₹0,         │
│ solar payback for your household is         │
│ longer than for unsubsidized families.      │
│ Consider solar only if your consumption     │
│ is trending above 200 units/month.          │
│                                             │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━                 │
│ Reply:                                      │
│ 1️⃣ SUBSIDY — how Gruha Jyothi works         │
│ 2️⃣ CLIFF — what triggers losing subsidy     │
│ Or send another bill photo anytime.         │
└─────────────────────────────────────────────┘
```

### 2.3 Follow-Up Turns (2-turn limit)

```
User sends:  "SOLAR"  (Nikhil flow, turn 1 of 2)

Bot replies (detailed solar breakdown):
┌─────────────────────────────────────────────┐
│ ☀️ Solar Eligibility Detail                 │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━                 │
│ Based on 210 units/month consumption:       │
│                                             │
│ Recommended system: 3 kW                    │
│ System cost: ₹1,65,000                      │
│ PM Surya Ghar subsidy: -₹78,000             │
│ Your net cost: ₹87,000                      │
│                                             │
│ Monthly benefit:                            │
│   Grid bill eliminated: ₹1,508              │
│   Export credit (140 units × ₹2.48): ₹347   │
│   Solar fixed-charge rebate: ₹75            │
│   ━━━━━━━━━━━━━━━━━━━━━━━                   │
│   Total: ₹1,930/month                       │
│                                             │
│ Payback: ~45 months (~3.8 years)            │
│ 25-year net savings: ~₹4.3 lakh             │
│                                             │
│ Next steps:                                 │
│ 1. Apply at pmsuryaghar.gov.in              │
│ 2. Choose MESCOM-empaneled vendor           │
│ 3. MESCOM SRTPV portal: srtpv.mesco.in     │
│                                             │
│ Send another bill photo for a fresh         │
│ analysis.                                   │
└─────────────────────────────────────────────┘

System: follow_up_count = 1
```

### 2.4 Error States

```
ERROR: PRE-APRIL 2025 BILL
━━━━━━━━━━━━━━━━━━━━━━━━━━
System: Extracted billing_period < 2025-04

Bot replies:
┌─────────────────────────────────────────────┐
│ 📅 This bill is from before April 2025.     │
│                                             │
│ KERC updated the tariff structure in        │
│ April 2025. I currently only analyze bills  │
│ from April 2025 onward to give you          │
│ accurate advice.                            │
│                                             │
│ 📸 Please send a more recent bill.          │
└─────────────────────────────────────────────┘
```

```
ERROR: NOT A MESCOM BILL / BAD PHOTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System: is_mescom_bill=false OR validation failed twice

Bot replies:
┌─────────────────────────────────────────────┐
│ ❌ I couldn't read that as a MESCOM bill.   │
│                                             │
│ Tips:                                       │
│ • Place bill on a flat surface              │
│ • Good lighting, no shadows                 │
│ • Capture the full bill in frame            │
│ • Avoid blurry or angled shots              │
│                                             │
│ 📸 Please try again.                        │
└─────────────────────────────────────────────┘
```

```
ERROR: GEMINI API FAILURE
━━━━━━━━━━━━━━━━━━━━━━━━━
System: Gemini returns 5xx, timeout, rate limit

Bot replies:
┌─────────────────────────────────────────────┐
│ ⚠️ I'm having trouble analyzing your bill   │
│ right now. Please try again in a minute.    │
│                                             │
│ ದಯವಿಟ್ಟು ಒಂದು ನಿಮಿಷ ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ. │
└─────────────────────────────────────────────┘

Demo-only: If phone_number matches a known
demo user, load cached extraction for their
sample bill from demo_fallbacks.json.
```

```
ERROR: UNCONSENTED USER SENDS PHOTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bot replies:
┌─────────────────────────────────────────────┐
│ I need your consent before analyzing bills. │
│ Please reply START to accept the privacy    │
│ terms, or STOP to opt out.                  │
└─────────────────────────────────────────────┘

System: Image is NOT sent to Gemini.
```

```
STOP COMMAND
━━━━━━━━━━━━━
User sends:  "STOP"

System:
  If consent_given was false:
    DELETE FROM users WHERE phone_number = $1
    Reply: "Understood, no data was ever processed.
            Feel free to return anytime."
  If consent_given was true:
    DELETE FROM users WHERE phone_number = $1
    (CASCADE deletes bills)
    Reply: "✅ All your data has been permanently
            deleted. Send any message to start fresh."
```

---

## 3. Functional Requirements

### 3.1 MUST — Demo Breaks Without It

| # | Component | Owner | Hours | Done When |
|---|-----------|-------|-------|-----------|
| M1 | **Gemini extraction** — Image → validated JSON (non-GJ + GJ schemas) | Wasih | 4h | 3 bill types extract cleanly: non-GJ full bill, GJ ₹0 bill, pre-April 2025 bill (detected + declined) |
| M2 | **Tariff calculator + Fixed Charge Trap** — validates bill math, flags overcharge, flags overprovisioned sanctioned load | Teammate | 4h | Nikhil's ₹1,943 bill validates within ±₹5; Fixed Charge Trap fires correctly for him, not for Sunita |
| M3 | **Gruha Jyothi Visibility** — computes subsidy received, annualized total, Level 0 approaching-entitlement warning, and three-level cliff warnings (soft step + monthly hard cliff + eligibility-at-risk) | Teammate | 2h | Priya's bill returns "₹1,080 this month, ₹34,500 total, 96% of entitlement used, RED approaching warning" |
| M4 | **Subsidy Navigator** — PM Surya Ghar + Gruha Jyothi + solar water heater rebate eligibility | Wasih | 3h | Returns correct eligibility for all 3 personas |
| M5 | **Solar ROI** — System sizing + cost + subsidy + monthly benefit + payback + lifetime + CO₂ | Wasih | 3h | Sunita returns 3 kW / ₹87K / 3.2 yr; Nikhil returns 3 kW / ₹87K / 3.8 yr; Priya returns "not recommended at current usage" |
| M6 | **WhatsApp bot (Twilio webhook)** — message routing, media handling, response dispatch | Wasih | 4h | End-to-end: photo in → full analysis out on demo phone |
| M7 | **Supabase persistence** — users + bills tables, consent-aware, no raw images | Wasih | 2h | Records appear in Supabase after bill submission, STOP hard-deletes |
| M8 | **DPDPA consent flow** — START/STOP gate, no-image-storage, hard-delete | Teammate | 1.5h | Unconsented user cannot trigger extraction; STOP deletes all rows |
| M9 | **Kannada TTS** — Google Cloud Text-to-Speech, voice note via WhatsApp | Wasih | 4h | Kannada audio plays in WhatsApp, reviewed by native speaker |
| M10 | **Streamlit admin dashboard** — aggregate stats only (no PII) | Teammate | 3h | Dashboard loads aggregate data from Supabase; password-protected |

**Total: 30.5h** (leaves 5.5h buffer in a 36h hackathon)

### 3.2 FAKE — Pre-rendered for demo

| # | Component | What's actually built |
|---|-----------|----------------------|
| F1 | Multi-bill trend chart | Pre-rendered matplotlib image showing 3 months of consumption for a fake user; displayed in admin dashboard |
| F2 | Infographic | One Canva/Figma template with placeholder variables (units, savings, subsidy); Python script swaps values and sends as image |
| F3 | Conversational follow-up beyond 2 turns | Only persona-specific keywords handled (SOLAR, FIXED for non-GJ; SUBSIDY, CLIFF for GJ). Everything else redirects to "send a new bill photo" |

### 3.3 WON'T — Explicitly out of scope

| # | Feature | Why |
|---|---------|-----|
| W1 | Slab optimizer | KERC removed slabs in FY 2025-26 — there's nothing to optimize |
| W2 | Pre-April 2025 bill support | Tariff structure was fundamentally different; out of scope for v1 |
| W3 | Commercial / LT-3 tariff | Domestic-only in v1; "first scalability axis" pitch line |
| W4 | Bhashini STT (Kannada speech-to-text) | ~6-8h integration, marginal demo value; voice is one-way out |
| W5 | Multi-DISCOM support (BESCOM / HESCOM / CESC / GESCOM) | Same KERC tariff but different bill formats; scalability pitch, not build |
| W6 | Payment integration | Already solved by PhonePe / GPay — not our problem |
| W7 | Vendor marketplace | Recommending installers creates liability; link to MESCOM-empaneled list only |
| W8 | Granular consent toggles | DPDPA MVP = START/STOP; granular toggles are enterprise scope |
| W9 | Audit logging, download-your-data | Below DPDPA threshold for hackathon prototype |

---

## 4. API Contracts

All modules are Python functions with typed dicts. Interface-level separation enables parallel development.

### 4.1 Gemini Bill Extraction

```python
# --- OUTPUT: BillExtraction ---
{
    # Identification
    "is_mescom_bill": true,
    "extraction_confidence": 0.91,         # Soft signal, not a hard gate

    # Consumer info
    "consumer_name": "SHETTY RAGHUNATH K",
    "rr_number": "MNG-1234567",
    "tariff_category": "LT-1",             # Or "2LT1" as sometimes printed; normalize to LT-1

    # Billing period (pre-April 2025 check)
    "billing_period_start": "2026-02-15",  # ISO YYYY-MM-DD
    "billing_period_end": "2026-03-15",
    "billing_period_days": 30,

    # Consumption & load
    "sanctioned_load_kw": 3.0,
    "previous_reading": 45230,
    "current_reading": 45440,
    "units_consumed": 210,

    # Pre-subsidy bill components (always populated)
    "energy_charges": 1218.00,             # units × ₹5.80
    "fixed_charges": 435.00,               # kW × ₹145
    "pg_surcharge": 75.60,                 # units × ₹0.36
    "electricity_tax": 109.62,             # 9% of energy charges
    "fppca": 105.00,                       # units × variable FPPCA rate
    "other_charges": 0.00,
    "subtotal_1_before_subsidy": 1943.22,  # Sum of above

    # Gruha Jyothi fields (null for non-GJ bills)
    "is_gruha_jyothi_beneficiary": false,
    "gjs_registration_date": null,         # YYYY-MM-DD or null
    "historical_avg_baseline": null,        # From FY 22-23 average, used for entitlement
    "entitlement_units": null,              # min(baseline + 10, 200) — but verify with bill
    "units_eligible_for_subsidy": null,    # 0 if non-GJ
    "units_chargeable": null,               # Only for GJ: what consumer actually pays for
    "gruha_jyothi_subsidy_amount": null,   # Sub-Total-2 equivalent

    # Final net bill
    "net_bill_amount": 1943.22,            # Sub-Total-1 − Sub-Total-2 (= Sub-Total-1 for non-GJ)

    # Metadata
    "due_date": "2026-04-15",
    "arrears": 0.00
}
```

**Validation (structural, not self-reported confidence):**
- `is_mescom_bill` must be true → else reject
- `billing_period_end` must be ≥ `2025-04-01` → else pre-April 2025 decline
- `units_consumed` in (0, 10000] range
- `sanctioned_load_kw` in (0, 50] range
- `current_reading > previous_reading`
- `units_consumed ≈ current_reading - previous_reading` (tolerance ±5)
- Bill math check: `subtotal_1_before_subsidy ≈ energy + fixed + pg + tax + fppca + other` (tolerance ±₹5)
- For GJ bills: `net_bill_amount ≈ max(0, subtotal_1 − gj_subsidy)` (tolerance ±₹5)

**Retry:** On validation failure, retry once with stricter prompt citing the specific issues.

### 4.2 Tariff Calculator + Fixed Charge Trap

```python
# --- INPUT ---
{
    "units_consumed": 210,
    "sanctioned_load_kw": 3.0,
    "billing_period_days": 30,
    "tariff_category": "LT-1",
    "fy": "2025-26",
    "extracted_bill": { ... BillExtraction ... }
}

# --- OUTPUT: TariffResult ---
{
    # Expected bill from KERC rates
    "expected_energy_charges": 1218.00,    # 210 × ₹5.80
    "expected_fixed_charges": 435.00,      # 3 × ₹145
    "expected_pg_surcharge": 75.60,        # 210 × ₹0.36
    "expected_electricity_tax": 109.62,    # 9% × energy
    "expected_fppca": 105.00,              # 210 × ₹0.50 (placeholder)
    "expected_subtotal_1": 1943.22,

    # Bill validation
    "bill_matches_calculation": true,
    "variance_rupees": 0,
    "overcharge_flag": false,

    # Fixed Charge Trap
    "fixed_charge_trap": {
        "fires": true,                     # false for Sunita, Priya
        "sanctioned_load_kw": 3.0,
        "estimated_peak_demand_kw": 1.46,  # Heuristic below
        "recommended_load_kw": 2.0,
        "excess_monthly_cost": 145.00,
        "excess_annual_cost": 1740.00,
        "reduction_process": "Requires MESCOM application and possibly meter change"
    },

    # Consumption reduction (replaces slab optimizer)
    "per_unit_marginal_cost": 7.18,        # ₹5.80 + 0.36 + 0.52 + 0.50
    "reduction_tip": {
        "scenario_moderate": {
            "units_cut": 30,
            "monthly_saving": 215.40,
            "annual_saving": 2584.80
        }
    }
}
```

**Peak demand heuristic:**
```
estimated_peak_kw = (units_consumed / (billing_period_days × 8)) × 1.67
```
Assumes 8 hours of meaningful consumption per day, 1.67× peak factor. Heuristic only — the response explicitly flags this as an estimate.

**Fixed Charge Trap fires when:** `estimated_peak_kw < (sanctioned_load_kw − 1.0)` AND `sanctioned_load_kw ≥ 2.0`.

### 4.3 Gruha Jyothi Visibility Module (replaces slab optimizer)

```python
# --- INPUT ---
{
    "extracted_bill": { ... BillExtraction ... },
    "trailing_10m_avg_units": 115.0  # From bills table; null for first-time users
}

# --- OUTPUT: GJVisibilityResult ---
{
    "is_gj_beneficiary": true,              # Short-circuit for non-GJ

    # --- The visibility win (what Priya doesn't know she's getting) ---
    "monthly_subsidy_received": 1080.02,
    "enrollment_date": "2023-08-26",
    "months_since_enrollment": 32,
    "estimated_total_subsidy_received": 34560.64,  # monthly × months
    "annualized_subsidy": 12960.24,

    # --- Entitlement state ---
    "entitlement_units": 115.0,
    "units_consumed": 110,
    "entitlement_utilization_pct": 95.6,

    # --- LEVEL 0 + THREE-LEVEL CLIFF (central to pitch) ---
    "cliffs": {
        "approaching_entitlement": {
            "triggered": true,             # red if util >= 90%, yellow if util >= 75%
            "distance_units": 5,           # entitlement - units_consumed (or 0)
            "description": "Approaching personal entitlement. RED at >=90%, YELLOW at >=75%."
        },
        "soft_step": {
            "triggered": false,             # true if units_consumed > entitlement
            "distance_units": 5,            # entitlement - units_consumed (or 0)
            "description": "If consumption exceeds entitlement but stays under 200, pay for excess units only"
        },
        "monthly_hard": {
            "triggered": false,             # true if units_consumed > 200
            "distance_units": 90,           # 200 - units_consumed (or 0)
            "hypothetical_full_bill": 2000, # What Priya would pay if she crossed 200
            "description": "If consumption exceeds 200 units in any month, LOSE ENTIRE SUBSIDY for that month"
        },
        "eligibility": {
            "at_risk": false,               # true if trailing_10m_avg > 200
            "trailing_10m_avg": 115.0,
            "distance_units": 85,           # 200 - trailing_10m_avg
            "description": "If 10-month rolling average exceeds 200, LOSE GJ ENROLLMENT. One-month drop does not restore."
        }
    },

    # --- Composite warnings (for response composer) ---
    "warnings": [
        {
            "level": "red",
            "cliff": "approaching_entitlement",
            "message": "You've used 96% of your 115-unit entitlement. Crossing entitlement starts chargeable units."
        }
    ],
    "overall_risk": "red",                  # green / yellow / red

    # --- The pitch line (embedded in GJ response template) ---
    "cliff_explanation": (
        "Gruha Jyothi has three separate cliffs. "
        "(1) Cross your entitlement: pay for excess units. "
        "(2) Cross 200 units in any month: pay the ENTIRE bill, not just excess. "
        "(3) 10-month average above 200 units: lose the scheme entirely. "
        "Most beneficiaries know about #1. Very few know about #2 and #3."
    )
}
```

**Warning precedence rule:** When multiple cliffs have warnings, order them in the composed response by severity: `eligibility > monthly_hard > soft_step`. The eligibility cliff is the worst outcome (loss of enrollment going forward, not recoverable by one-month consumption drop), so flag it first.

**Formula origin note:** The entitlement formula is `min(historical_FY22-23_avg + 10, 200)` per Karnataka Cabinet decision dated 18 January 2024 (replacing the original `× 1.10` formula from August 2023). The Navigator extracts `entitlement_units` directly from the bill when available; only computes it from `historical_avg_baseline` if the bill doesn't report it. Some ESCOM billing systems during the 2024-2025 transition period may still use the old `× 1.10` formula — the extractor tolerates both.

### 4.4 Subsidy Navigator

```python
# --- INPUT: SubsidyInput ---
{
    "units_consumed": 210,
    "sanctioned_load_kw": 3.0,
    "tariff_category": "LT-1",
    "is_gj_beneficiary": false,
    "entitlement_units": null
}

# --- OUTPUT: SubsidyResult ---
{
    "pm_surya_ghar": {
        "eligible": true,
        "reason": "Domestic LT-1 with sanctioned load suitable for rooftop solar",
        "subsidy_amount": 78000,
        "system_size_kw": 3,
        "subsidy_breakdown": "₹30,000 × 2 + ₹18,000 × 1 = ₹78,000",
        "apply_url": "https://pmsuryaghar.gov.in",
        "mescom_srtpv_url": "https://srtpv.mesco.in"
    },
    "gruha_jyothi": {
        "status": "eligible_not_enrolled",   # eligible_not_enrolled / enrolled / ineligible
        "reason": "Domestic LT-1 consumer, not currently enrolled",
        "how_to_apply": "Apply via sevasindhu.karnataka.gov.in or Karnataka One portal",
        "note": "Subsidy covers bills up to 200 units/month for domestic consumers"
    },
    "solar_water_heater_rebate": {
        "eligible": true,
        "discount": "25 paise per unit on energy charges",
        "monthly_saving_estimate": 52.50,
        "condition": "Requires BIS-certified solar water heater installation"
    }
}
```

### 4.5 Solar ROI Calculator

```python
# --- INPUT: SolarInput ---
{
    "monthly_units_consumed": 210,
    "sanctioned_load_kw": 3.0,
    "tariff_category": "LT-1",
    "is_gj_beneficiary": false,
    "entitlement_units": null,
    "location": "coastal_karnataka"   # For irradiance lookup
}

# --- OUTPUT: SolarROI ---
{
    "recommended_system_kw": 3,
    "sizing_logic": "ceil(annual_kWh / 1400 × 1.1)",

    # If GJ beneficiary with consumption well within entitlement:
    # "recommendation": "not_recommended"
    "recommendation": "recommended",        # recommended / marginal / not_recommended
    "recommendation_reason": "Non-GJ household with full bill liability — clear ROI case",

    # Costs
    "system_cost_before_subsidy": 165000,   # 3 × ₹55,000
    "pm_surya_ghar_subsidy": 78000,
    "cost_after_subsidy": 87000,

    # Generation
    "specific_yield_kwh_per_kwp_year": 1400,
    "annual_generation_kwh": 4200,
    "monthly_generation_kwh": 350,
    "monthly_self_consumption_kwh": 210,
    "monthly_export_kwh": 140,

    # Financial benefit
    "monthly_grid_bill_displaced": 1508,     # Energy + P&G + E-tax + FPPCA (not fixed)
    "monthly_export_credit": 347.20,         # 140 × ₹2.48
    "monthly_solar_fixed_rebate": 75,        # 3 × ₹25
    "monthly_total_benefit": 1930.20,

    # Payback & lifetime
    "payback_months": 45,
    "payback_years": 3.8,
    "lifetime_years": 25,
    "lifetime_gross_savings_flat_tariffs": 579060,      # 25 × 12 × 1930.20
    "lifetime_net_savings_flat_tariffs": 431000,        # Minus system cost + degradation + inverter replacement
    "lifetime_gross_savings_3pct_escalation": 844000,   # Karnataka historical tariff trend
    "lifetime_net_savings_3pct_escalation": 696000,     # Realistic upside

    # Environmental
    "co2_offset_tonnes_per_year": 2.98,      # 4200 × 0.710 / 1000
    "trees_equivalent_per_year": 100,        # At 30 kg CO₂/tree/year (widely-cited urban benchmark)

    # Tariff references
    "net_metering_export_rate": 2.48,        # KERC Solar Order, 2-3 kW bracket
    "assumptions": [
        "System cost ₹55,000/kW (market avg, range ₹53K-₹72K by vendor)",
        "Specific yield 1,400 kWh/kWp/year (Global Solar Atlas for Mangalore)",
        "Performance ratio ~69% baked into specific yield (coastal humidity)",
        "Grid emission factor 0.710 kg CO₂/kWh (CEA CO₂ Baseline Database v21, Dec 2025, FY 2024-25)",
        "Tree absorption 30 kg CO₂/tree/year (widely-cited urban benchmark)",
        "25-year degradation ~6% cumulative; one inverter replacement at year 12-15",
        "Flat-tariff lifetime is conservative; Karnataka's historical 3%/year escalation gives realistic upside"
    ]
}
```

---

## 5. Gemini Extraction Prompt

```python
EXTRACTION_PROMPT = """You are an expert at reading Indian electricity bills. Analyze this image of a MESCOM (Mangalore Electricity Supply Company) electricity bill.

Extract the following fields and return ONLY a valid JSON object. No markdown, no explanation, no preamble.

IDENTIFICATION:
- is_mescom_bill (boolean): Is this a MESCOM electricity bill? Set false if different utility, non-bill document, or unreadable.
- extraction_confidence (float 0.0–1.0): Your self-reported confidence.
- consumer_name (string): Consumer name as printed.
- rr_number (string): RR Number / Account Number / Consumer Number.
- tariff_category (string): Tariff code (e.g., "LT-1", "2LT1", "LT-2(a)"). Normalize "2LT1" to "LT-1".

BILLING PERIOD:
- billing_period_start (string): Period start in YYYY-MM-DD.
- billing_period_end (string): Period end in YYYY-MM-DD. Dates on bills may be in DD/MM/YYYY format — convert to ISO.
- billing_period_days (integer): Number of days in billing period.

CONSUMPTION & LOAD:
- sanctioned_load_kw (float): Sanctioned load in kW. Bills may say "2.99KW+0HP" etc. — extract the kW value.
- previous_reading (integer): Previous meter reading.
- current_reading (integer): Current meter reading.
- units_consumed (integer): Units consumed in this period.

PRE-SUBSIDY BILL COMPONENTS (Sub-Total-1 on the bill):
- energy_charges (float): Energy/consumption charges in ₹.
- fixed_charges (float): Fixed charges in ₹.
- pg_surcharge (float): P&G surcharge in ₹. Set 0.0 if not present.
- electricity_tax (float): Electricity tax / tax @ 9% in ₹.
- fppca (float): FPPCA (Fuel & Power Purchase Cost Adjustment) in ₹. Set 0.0 if not present.
- other_charges (float): Sum of any other line items (arrears, adjustments) in ₹.
- subtotal_1_before_subsidy (float): Total of all pre-subsidy charges. On GJ bills this is Sub-Total-1.

GRUHA JYOTHI (CRITICAL):
MESCOM bills with Gruha Jyothi show the bill TWICE — once as pre-subsidy (Sub-Total-1) and once as subsidy amount (Sub-Total-2). Net bill = Sub-Total-1 − Sub-Total-2.

- is_gruha_jyothi_beneficiary (boolean): True if the bill has a "Gruha Jyothi Subsidy" / "GJ" section with a Sub-Total-2.
- gjs_registration_date (string): GJS Reg Date in YYYY-MM-DD, or null.
- historical_avg_baseline (float): "Average (FY XX-XX)" field showing historical consumption baseline, or null.
- entitlement_units (float): "Entitlement Unit" field — the subsidized unit allowance, or null.
- units_eligible_for_subsidy (float): Units covered by subsidy this month, or null.
- units_chargeable (float): Units the consumer actually pays for (0 if fully covered), or null.
- gruha_jyothi_subsidy_amount (float): Sub-Total-2 amount in ₹, or null.

NET BILL:
- net_bill_amount (float): What the consumer actually pays. For non-GJ = Sub-Total-1. For GJ = Sub-Total-1 − Sub-Total-2 (usually ₹0).
- due_date (string): Due date in YYYY-MM-DD. Convert from DD/MM/YYYY if needed.
- arrears (float): Arrears in ₹, 0.0 if none.

RULES:
1. If a field is not visible or unreadable, set it to null. Do not guess.
2. Amounts are in Indian Rupees. Do not include currency symbols in numeric fields.
3. Dates may be in DD/MM/YYYY format on the bill — always convert to ISO YYYY-MM-DD.
4. Bills contain Kannada text; extract numeric values regardless of language.
5. If not a MESCOM bill, set is_mescom_bill to false and other fields to null.
6. For GJ bills, the number after "Bill for Consumed Units" / "Sub-Total-1" is pre-subsidy. The number after "Gruha Jyothi Subsidy" / "Sub-Total-2" is the subsidy. "Current Bill Amt" or "Net Bill Amt" is what the consumer pays.

Return ONLY the JSON object."""
```

### Validation function (structural, not confidence-based)

```python
def validate_extraction(data: dict) -> tuple[bool, list[str]]:
    issues = []

    if not data.get("is_mescom_bill"):
        return False, ["Not identified as MESCOM bill"]

    # Pre-April 2025 gate
    end_date = data.get("billing_period_end")
    if end_date and end_date < "2025-04-01":
        return False, ["pre_april_2025"]  # Special error code — graceful decline

    # Range checks
    units = data.get("units_consumed")
    if units is None or units <= 0 or units > 10000:
        issues.append("units_consumed out of range")

    load = data.get("sanctioned_load_kw")
    if load is None or load <= 0 or load > 50:
        issues.append("sanctioned_load_kw out of range")

    # Meter consistency
    prev = data.get("previous_reading")
    curr = data.get("current_reading")
    if prev is not None and curr is not None:
        if curr <= prev:
            issues.append("current_reading <= previous_reading")
        elif units is not None and abs((curr - prev) - units) > 5:
            issues.append("units_consumed doesn't match meter readings")

    # Bill math
    subtotal = data.get("subtotal_1_before_subsidy")
    components = sum([
        data.get("energy_charges", 0) or 0,
        data.get("fixed_charges", 0) or 0,
        data.get("pg_surcharge", 0) or 0,
        data.get("electricity_tax", 0) or 0,
        data.get("fppca", 0) or 0,
        data.get("other_charges", 0) or 0,
    ])
    if subtotal is not None and abs(subtotal - components) > 5:
        issues.append(f"subtotal_1 ({subtotal}) doesn't match component sum ({components})")

    # GJ bill math
    if data.get("is_gruha_jyothi_beneficiary"):
        net = data.get("net_bill_amount", 0)
        subsidy = data.get("gruha_jyothi_subsidy_amount", 0)
        if subtotal is not None and subsidy is not None:
            if abs((subtotal - subsidy) - net) > 5:
                issues.append(f"GJ math: net ({net}) != subtotal - subsidy ({subtotal - subsidy})")

    return len(issues) == 0, issues
```

---

## 6. Success Criteria — The 7 Demo Moments

| # | Moment | What Judges See | Proves | Fallback |
|---|--------|----------------|--------|----------|
| 1 | **The Hook** | "22.6 lakh consumers... 1.1% PMSGMBY conversion... 1 in 500 households..." | Problem is real, data-backed, local | Memorized — no fallback needed |
| 2 | **The Fixed Charge Trap** | Nikhil's worked example: 3 kW → 1.5 kW peak, ₹1,740/yr, ₹39 cr at MESCOM scale | Original analytical thinking | Memorized |
| 3 | **Live Bill Scan (Nikhil)** | Wasih sends Nikhil's March 2026 bill on WhatsApp. Live Gemini extraction. Full analysis returns in 8-12 sec. | Core tech works | Cached extraction + "here's what it returned 10 min ago" |
| 4 | **The Fixed Charge Alert fires** | In the analysis response, Nikhil's overprovisioned load is flagged with the ₹1,740/yr number | Intelligence layer, not just OCR | Response template, hard to fail |
| 5 | **The GJ Visibility moment (Priya)** | Wasih switches to Priya's bill (₹0 net). Bot reveals "Karnataka paid ₹1,080 this month, ₹34,500 total since Aug 2023." | Novel insight, no one else does this | Fully templated |
| 6 | **Kannada voice note** | Audio message plays on speaker. Sounds natural. | Accessibility is real | Pre-recorded clip |
| 7 | **The Close** | "We'd rather solve one step well than claim to solve five steps badly." Hand out judge QR cards. | Discipline + memorable exit | Memorized |

**Note the choreography change:** the demo now has **two bills**, not one. Nikhil's for the Fixed Charge Trap anchor, Priya's for the GJ Visibility angle. This is the single biggest shift from PRD v1. Sunita is a reserve — if a judge asks "what about someone who's actually a great solar candidate?", Wasih pulls out her bill as the third exhibit.

### Winning looks like

- Every transition feels rehearsed but natural
- Live Gemini calls complete in under 15 seconds
- At least one judge asks about Gruha Jyothi Visibility (it's the novel insight)
- No number is challenged without an immediate KERC citation
- DPDPA-by-design talking point lands
- First hostile question answered with one of the three memorized defense lines
- Judge walks away remembering two things: "Fixed Charge Trap" and "Karnataka paid ₹1,080 on your behalf"

---

## Appendix A: Supabase Schema

```sql
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    consent_given BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bills (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Billing period
    billing_period_start DATE,
    billing_period_end DATE,

    -- Core fields
    tariff_category TEXT,
    units_consumed INTEGER,
    sanctioned_load_kw REAL,

    -- Charges (pre-subsidy)
    energy_charges REAL,
    fixed_charges REAL,
    pg_surcharge REAL,
    electricity_tax REAL,
    fppca REAL,
    subtotal_1 REAL,

    -- Gruha Jyothi
    is_gj_beneficiary BOOLEAN DEFAULT FALSE,
    gj_registration_date DATE,
    entitlement_units REAL,
    units_chargeable REAL,
    gj_subsidy_amount REAL,

    -- Final
    net_bill_amount REAL,

    -- Full analysis blob
    analysis_result JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_bills_user ON bills(user_id);
CREATE INDEX idx_bills_gj ON bills(is_gj_beneficiary) WHERE is_gj_beneficiary = TRUE;
```

## Appendix B: Q&A Defense Table

| Judge Says | You Say |
|------------|---------|
| "Why MESCOM only?" | "That's the trade-off they won't make. We made it." |
| "Not solving the real bottleneck (financing/vendors)" | "We'd rather solve one step well than claim to solve five steps badly." |
| "₹1,740/year isn't life-changing money" | "The trap isn't the size of the loss per family — it's that 22.6 lakh families don't even know it exists." |
| "How's this different from Bijli Bachao / calculators?" | "None of them are MESCOM-calibrated, Kannada-first, or on the channel rural Karnataka actually opens. And none of them show you your Gruha Jyothi subsidy visibility." |
| "What about data privacy?" | "DPDPA-compliant by design. Explicit consent, no image storage, one-word STOP. We treated this as a feature, not a checkbox." |
| "How does my grandmother use this?" | "She probably doesn't — but her grandson does. We built for him, so he can serve her better." |
| "What if Gemini gets it wrong?" | "Structural validation. Bill math has to add up. If the components don't sum to the total within ₹5, we retry with a stricter prompt. The user also verifies the extracted numbers before we make recommendations." |
| "Has this been tested with real users?" | "We tested with 5 users in Mangaluru. Three of them didn't know what their sanctioned load meant. One didn't realize she was receiving Gruha Jyothi subsidy. That confirmed our problem." *(After real-user testing is done.)* |
| "How do you make money?" | "DISCOM partnership — we're a consumer engagement tool MESCOM can white-label. Solar installer referral commission as secondary. But this is a civic utility first, business model second." |
| "Why is payback 3.8 years and not 15 months like some pitches?" | "Because 15 months is impossible math — we ran the numbers honestly. A 3 kW system for a 210-unit household pays back in 3.8 years. Still one of the best residential investments available." |
| "Why ₹39 crore when BESCOM's a bigger DISCOM?" | "MESCOM-specific. BESCOM scale would be higher. We chose depth over breadth." |
| "What if someone games Gruha Jyothi to stay under entitlement?" | "That's actually the product working — our cliff warning is designed to make households consumption-aware. More awareness = better behavior. That's the first-mile win." |
