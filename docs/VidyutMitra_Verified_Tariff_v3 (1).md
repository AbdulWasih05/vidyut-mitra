# VidyutMitra — Verified Tariff & Persona Math (v3)

**Supersedes:** Verified Tariff v2 (April 17, 2026 AM) — v2 had a stale CO₂ emission factor and an oversimplified Gruha Jyothi cliff model. Everything else from v2 holds.

**Primary sources:**
- KERC Tariff Order 2025, dated 27 March 2025, Annexure 2 (Combined Tariff Order governing BESCOM / MESCOM / CESC / HESCOM / GESCOM)
- KERC Solar Tariff Order, effective 01 July 2025
- CEA CO₂ Baseline Database Version 21.0, published December 2025
- Karnataka Gruha Jyothi Scheme guidelines as clarified by CESC MD K.M. Munigopalraju, November 2025

**Effective:** From first meter reading date on or after 01.04.2025
**Demo vintage:** FY 2025-26 rates on March 2026 bills

> **What changed from v2.**
> (1) Grid emission factor updated from a stale 0.82 kg CO₂/kWh to the current **0.710 kg/kWh** per CEA v21 (Dec 2025). CO₂ offset for Nikhil's 3 kW system accordingly drops from 3.44 to **2.98 tonnes/year**.
> (2) Trees equivalent reframed at 30 kg CO₂/tree/year (widely-cited urban-tree benchmark) → **~100 trees/year**.
> (3) Gruha Jyothi cliff model replaced with the correct **three-level cliff**: soft step at entitlement, hard cliff at 200 units/month, eligibility cliff on 10-month rolling average.
> (4) Gruha Jyothi entitlement formula origin clarified — the switch from `×1.10` to `+10 flat units` happened in the **January 2024 Cabinet meeting**, not October 2025.
> (5) 25-year solar savings now presented as two numbers: **Rs. 4.3 lakh at flat tariffs** (conservative) and **Rs. 6.9 lakh at 3% annual escalation** (realistic for Karnataka's last-decade trend).
> Every other number is unchanged.

---

## Part 1: KERC LT-1 Domestic Tariff (FY 2025-26)

### Verified from KERC PDF

| Component | FY 2025-26 | FY 2026-27 | FY 2027-28 | Source |
|-----------|-----------|-----------|-----------|--------|
| **Fixed Charge** | **Rs. 145/kW/month** | Rs. 150/kW | **Rs. 160/kW** | KERC Order 27-Mar-2025, Annexure 2, LT-1 |
| **Energy Charge** | **Rs. 5.80/unit (flat)** | Rs. 5.80/unit | Rs. 5.75/unit | Same; single-slab structure per Clauses 19 and 30 |
| **Solar rooftop rebate** | Rs. 25/kW/month on fixed | Same | Same | LT-1 Note (b), up to 10 kW installations |

### Not in the KERC tariff schedule (separate orders / authorities)

| Component | Value | Source | Notes |
|-----------|-------|--------|-------|
| **P&G surcharge** | Rs. 0.36/unit | KERC Order, 18-Mar-2025 | KPTCL/ESCOM pension & gratuity; GJ beneficiaries exempt |
| **Electricity Tax** | 9% of energy charges | Government of Karnataka | Verified from real Dec 2024 MESCOM bill; treat as current-best |
| **FPPCA** | ~Rs. 0.48–Rs. 0.50/unit | Variable monthly | Use Rs. 0.50/unit for all demo calculations |

### Legal structure — no slabs

The order is explicit. LT-1 tariff schedule for FY 2025-26 lists one fixed charge rate and one energy charge rate. Clause 19 of the General Conditions: *"In view of introduction of single slab for energy charges, the LT consumers may avail multiple connections to their premises."* Clause 30 confirms the same: *"In view of the introduction of single slab system for energy charges to LT consumers..."*

Pre-April 2025 bills show the old slab structure. VidyutMitra is post-April-2025-only; older bills get a graceful decline.

### PM Surya Ghar Solar Tariffs (KERC Solar Order, effective July 1, 2025 – June 30, 2026)

| System Size | Export Rate (Rs./unit) |
|-------------|-----------------------|
| 1–2 kW | Rs. 2.30 |
| **2–3 kW** | **Rs. 2.48** |
| Above 3 kW | Rs. 2.93 |
| Non-subsidized domestic (1–10 kW) | Rs. 3.86 |

### PM Surya Ghar Central Subsidy (MNRE)

| System Size | Subsidy |
|-------------|---------|
| 1 kW | Rs. 30,000 |
| 2 kW | Rs. 60,000 |
| 3 kW | Rs. 78,000 (capped) |

### Solar ROI Constants

| Constant | Value | Source |
|----------|-------|--------|
| Specific yield (Mangalore) | 1,400 kWh/kWp/year | Global Solar Atlas, 12.87°N 74.88°E |
| Solar irradiance (Mangalore) | 5.55 kWh/m²/day | Global Solar Atlas |
| System cost | Rs. 55,000/kW (market avg, range Rs. 53K–Rs. 72K) | 2026 vendor benchmarks |
| Performance ratio | ~69% (coastal humidity) | Industry standard |
| **Grid emission factor** | **0.710 kg CO₂/kWh** | **CEA v21, December 2025, FY 2024-25 weighted average** |
| Trees absorption | 30 kg CO₂/tree/year | Widely-cited urban-tree benchmark |
| Annual tariff escalation (Karnataka avg) | ~3% | Historical last-decade trend |

### Gruha Jyothi (Karnataka State Subsidy) — Updated Rules

**Eligibility:** Any domestic (LT-1) consumer can apply. No BPL/APL requirement. Enrolled via Seva Sindhu portal / Karnataka One centres.

**Rule change history:** Originally launched August 2023 with entitlement = `historical_FY22-23_avg × 1.10`. Cabinet meeting on **January 18, 2024** switched to `historical_avg + 10 units` flat. Public re-communications in late 2025 (notably Star of Mysore, 23 November 2025) clarified the tightening of enforcement; no formula change in 2025.

**Current entitlement calculation:**
```
entitlement_units = min(historical_FY22-23_avg + 10, 200)
```

Where `historical_FY22-23_avg` is the consumer's average monthly consumption during April 2022 – March 2023 (the baseline reference year).

**The three-level cliff (this is the pitch upgrade):**

| Level | Trigger | Consequence |
|-------|---------|-------------|
| **1. Soft step** | Monthly consumption > entitlement but ≤ 200 units | Pay for the excess units only (at standard tariff) |
| **2. Monthly hard cliff** | Monthly consumption > 200 units in any single month | **Pay the ENTIRE bill** for that month — no partial subsidy, no credit for the first 200 units |
| **3. Eligibility cliff** | 10-month rolling average > 200 units | **Lose Gruha Jyothi eligibility.** Reducing consumption in one month does not restore eligibility — reviews happen over 10-month windows. |

Per CESC MD K.M. Munigopalraju (Nov 2025): *"If a person has an average consumption of 100 units per month and tries to increase usage up to 200 units to claim the scheme benefits, he or she will not be eligible. The bill is calculated strictly on average consumption. The 10-month average must remain below 200 units, with a grace concession of 10 units... Even for eligible consumers, if monthly usage exceeds the calculated average, the difference must be paid. And if consumption crosses 200 units in any month, the entire bill becomes payable."*

**Product implication:** The three-level cliff is central to VidyutMitra's value for GJ beneficiaries. Most are aware of cliff #1 (the soft step). Very few know about cliff #2 (one-month total loss) or cliff #3 (rolling-average disqualification). Warning consumers before they trigger any of these is genuinely new value — not available through any existing tool.

---

## Part 2: The Three Personas — Full Math

### Persona 1: Nikhil Shetty — The Fixed Charge Trap hero

| Attribute | Value |
|-----------|-------|
| Age | 27 |
| Location | Parents in Surathkal, Dakshina Kannada |
| Connection | LT-1 Domestic, 3 kW sanctioned |
| Gruha Jyothi | **Not enrolled** (parents never applied) |
| Monthly consumption | 210 units |
| Actual peak demand (estimated) | ~1.5 kW |
| Billing period used | March 2026 (FY 2025-26 rates) |

#### Bill calculation

```
Energy charges:     210 × Rs. 5.80  = Rs. 1,218.00
Fixed charges:        3 × Rs. 145   =   Rs. 435.00
P&G surcharge:      210 × Rs. 0.36  =    Rs. 75.60
Electricity tax:    9% × Rs. 1,218  =   Rs. 109.62
FPPCA:              210 × Rs. 0.50  =   Rs. 105.00
                                    ─────────────
TOTAL BILL                          = Rs. 1,943.22 → Rs. 1,943
```

#### Fixed Charge Trap

```
Current fixed charge:      3 kW × Rs. 145 = Rs. 435/month
Reduced to 2 kW:           2 kW × Rs. 145 = Rs. 290/month
───────────────────────────────────────────
Monthly saving: Rs. 145  |  Annual saving: Rs. 1,740
```

**At MESCOM scale:**
- 22,60,000 consumers × 10% overprovisioned by 1 kW = 2,26,000 households
- Annual waste: 2,26,000 × Rs. 1,740 = **Rs. 39.3 crore/year**

#### Solar ROI (3 kW system)

```
System cost:           3 × Rs. 55,000     = Rs. 1,65,000
PM Surya Ghar subsidy:                      Rs. 78,000
Net consumer cost:                           Rs. 87,000

Monthly generation:    4,200 / 12         = 350 kWh
Monthly consumption:                         210 kWh
Monthly export:                              140 kWh

Grid bill displaced (energy + P&G + tax + FPPCA):  Rs. 1,508.22
Export credit (140 × Rs. 2.48):                     Rs. 347.20
Solar rooftop rebate (3 × Rs. 25):                   Rs. 75.00
                                                  ──────────────
Total monthly benefit:                              Rs. 1,930.42

Payback:  Rs. 87,000 / Rs. 1,930.42 = 45.1 months ≈ 3.8 years
```

**25-year savings:**

| Assumption | Lifetime savings |
|------------|------------------|
| Flat electricity tariffs (conservative) | **~Rs. 4.3 lakh** |
| 3% annual tariff escalation (realistic — Karnataka's 10-year trend) | **~Rs. 6.9 lakh** |

For pitch: lead with conservative, mention realistic as the honest upside.

#### Environmental impact

```
Annual generation:  4,200 kWh
Grid emission factor (CEA v21):  0.710 kg CO₂/kWh
Annual CO₂ offset:  4,200 × 0.710 = 2,982 kg ≈ 2.98 tonnes/year
Trees equivalent:   2,982 / 30 = ~99 trees/year (rounds to ~100 trees/year)
```

---

### Persona 2: Sunita Bhat — The Solar ROI hero

| Attribute | Value |
|-----------|-------|
| Age | 45 |
| Location | Chikmagalur town |
| Connection | LT-1 Domestic, 3 kW sanctioned |
| Gruha Jyothi | **Eligible but not enrolled** (honest reflection of 0.2% awareness gap) |
| Monthly consumption | 280 units |
| Actual peak demand | ~2 kW (appropriately sized — no Fixed Charge Trap) |
| Roof | Own house, south-facing, ~30 m² usable |

#### Bill calculation

```
Energy charges:     280 × Rs. 5.80  = Rs. 1,624.00
Fixed charges:        3 × Rs. 145   =   Rs. 435.00
P&G surcharge:      280 × Rs. 0.36  =   Rs. 100.80
Electricity tax:    9% × Rs. 1,624  =   Rs. 146.16
FPPCA:              280 × Rs. 0.50  =   Rs. 140.00
                                    ─────────────
TOTAL BILL                          = Rs. 2,445.96 → Rs. 2,446
```

#### Solar ROI (3 kW system)

```
System cost:           3 × Rs. 55,000     = Rs. 1,65,000
PM Surya Ghar subsidy:                      Rs. 78,000
Net consumer cost:                           Rs. 87,000

Monthly generation:                         350 kWh
Monthly consumption:                        280 kWh
Monthly export:                              70 kWh

Grid bill displaced:                      Rs. 2,011.00
Export credit (70 × Rs. 2.48):             Rs. 173.60
Solar rooftop rebate (3 × Rs. 25):          Rs. 75.00
                                         ──────────────
Total monthly benefit:                    Rs. 2,259.60

Payback: Rs. 87,000 / Rs. 2,260 = 38.5 months ≈ 3.2 years
```

**25-year savings:**

| Assumption | Lifetime savings |
|------------|------------------|
| Flat tariffs | **~Rs. 5.3 lakh** |
| 3% annual escalation | **~Rs. 8.5 lakh** |

#### Environmental impact

```
Annual generation:  4,200 kWh  (same — 3 kW system, same insolation)
Annual CO₂ offset:  2.98 tonnes/year
Trees equivalent:   ~100 trees/year
```

#### Why Sunita is the solar hero

Higher consumption = more grid units displaced = faster breakeven. Every unit her panels produce offsets a unit she would otherwise have bought at the full Rs. 7.18 all-in rate. Her 3.2-year payback beats Nikhil's 3.8-year by a meaningful margin.

---

### Persona 3: Priya Nayak — The Gruha Jyothi Visibility hero

| Attribute | Value |
|-----------|-------|
| Age | 20 |
| Location | Family home in Manipal, Udupi district |
| Connection | LT-1 Domestic, 2 kW sanctioned |
| Gruha Jyothi | **Enrolled since August 2023** |
| Monthly consumption | 110 units |
| FY22-23 historical average | 105 units |
| Entitlement | min(105 + 10, 200) = **115 units** |
| Units chargeable | 0 (110 ≤ 115) |
| **Net bill paid** | **Rs. 0.00** |

#### What the bill computes (but Priya doesn't pay)

```
Sub-Total-1 (what it would cost):
  Energy charges:    110 × Rs. 5.80  =  Rs. 638.00
  Fixed charges:       2 × Rs. 145   =  Rs. 290.00
  P&G surcharge:     110 × Rs. 0.36  =   Rs. 39.60
  Electricity tax:   9% × Rs. 638    =   Rs. 57.42
  FPPCA:             110 × Rs. 0.50  =   Rs. 55.00
                                    ─────────────
  Sub-Total-1:                      = Rs. 1,080.02

Sub-Total-2 (Gruha Jyothi Subsidy):   Rs. 1,080.02
                                    ─────────────
  Net bill:                              Rs. 0.00
```

#### The subsidy visibility pitch

- **Monthly subsidy Priya's family receives:** Rs. 1,080
- **Annual subsidy received:** Rs. 12,960/year
- **Total since enrollment (Aug 2023 to now, ~32 months):** ~Rs. 34,500

Most households don't know this number. The bill shows "Net: Rs. 0" with the subsidy buried in a Sub-Total-2 line most consumers never read. VidyutMitra extracts it, surfaces it, and converts an invisible benefit into a concrete win.

#### Three-level cliff check for Priya

| Cliff | Priya's status | Warning |
|-------|---------------|---------|
| Approaching entitlement (entitlement = 115) | 110 units used, 96% utilization | RED |
| Soft step (entitlement = 115) | 110 units used, below entitlement | GREEN |
| Monthly hard cliff (200 units) | 110 units, 55% of cap | GREEN |
| Eligibility cliff (10-month avg ≤ 200) | ~115 unit trailing average | GREEN — no risk |

The bot surfaces all three. Summer months with AC use are the critical watch window — if a single month exceeds 200, Priya's family loses that month's subsidy entirely. If the 10-month average creeps toward 200, their enrollment is at risk at the next review.

#### Why no solar for Priya?

Her effective grid cost is Rs. 0. A 2 kW system at Rs. 1,20,000 − Rs. 60,000 subsidy = Rs. 60,000 net cost, saving her nothing she wasn't already saving via Gruha Jyothi. Solar makes sense for Priya's family only if their consumption is trending toward or above 200 units/month — i.e., if they're at real risk of triggering a cliff.

The bot says this honestly: *"Because you're currently fully covered by Gruha Jyothi, solar payback for your household is longer than for unsubsidized households. Consider solar only if your consumption is trending above 200 units/month."*

---

## Part 3: What Each Persona Exercises

| Module | Nikhil | Sunita | Priya |
|--------|--------|--------|-------|
| Bill extraction (MUST M1) | ✅ Non-GJ bill | ✅ Non-GJ bill | ✅ GJ bill (double sub-total) |
| Tariff calculator (M2) | ✅ Full bill validation | ✅ Full bill validation | ✅ Validates Sub-Total-1 math |
| **Fixed Charge Trap (part of M2)** | **✅ HERO** — 3 kW on 1.5 kW peak | ❌ Appropriate load | ❌ Appropriate load |
| **GJ Visibility — 3-level cliff (M3)** | ❌ Not applicable | ❌ Not applicable | **✅ HERO** — Rs. 34,500 revealed, 3 cliffs explained |
| Subsidy Navigator (M4) | ✅ PM Surya Ghar eligible; flag Gruha Jyothi eligible-not-enrolled | ✅ Same | ⚠️ Flag eligibility-at-risk monitoring |
| **Solar ROI (M5)** | ✅ 3.8 yr payback | **✅ HERO** — 3.2 yr payback, Rs. 8.5 lakh at realistic escalation | ❌ Not recommended at current usage |

**Each persona anchors exactly one hero module. This is the demo choreography.**

---

## Part 4: Source Citations Card (for Q&A defense)

Print this as a physical laminated card. When a judge challenges a number, glance and respond.

| Claim | Source |
|-------|--------|
| Fixed charge Rs. 145/kW FY 2025-26 | KERC Tariff Order 2025, Annexure 2, LT-1, dated 27-Mar-2025 |
| Energy charge Rs. 5.80/unit flat, no slabs | Same order. Clauses 19 and 30 confirm single-slab structure |
| Fixed charge forward rates Rs. 150 / Rs. 160 | Same order. FY 26-27 and FY 27-28 columns |
| P&G surcharge Rs. 0.36/unit | KERC Separate Order, 18-Mar-2025 |
| Electricity tax 9% | Government of Karnataka (verified from real MESCOM bill) |
| PM Surya Ghar subsidy Rs. 78,000 for 3 kW | MNRE, pmsuryaghar.gov.in |
| Export rate Rs. 2.48/unit for 2-3 kW | KERC Solar Tariff Order, effective 01-Jul-2025 |
| Solar rooftop rebate Rs. 25/kW/month | KERC Tariff Order 2025, LT-1 Note (b) |
| Karnataka 1.1% PMSGMBY conversion | Mercom India, April 2025 |
| MESCOM coastal 0.2% awareness | Daijiworld, August 2024 |
| MESCOM consumer count 22.6 lakh | MESCOM annual report 2023-24 |
| Specific yield 1,400 kWh/kWp/year | Global Solar Atlas, 12.87°N 74.88°E |
| **Grid emission factor 0.710 kg CO₂/kWh** | **CEA CO₂ Baseline Database Version 21.0, December 2025, FY 2024-25 weighted average** |
| Trees absorption 30 kg CO₂/tree/year | Widely-cited urban-tree benchmark |
| **Gruha Jyothi entitlement formula (historical avg + 10 units, capped at 200)** | **Karnataka Cabinet decision, 18-Jan-2024; enforcement clarified by CESC MD K.M. Munigopalraju, 23-Nov-2025** |
| **Gruha Jyothi three-level cliff** | Star of Mysore, 23-Nov-2025 quoting CESC managing director |
| Residential solar payback 3-5 years | Kondaas Automation 2026, Orient Solar 2025, industry consensus across 8+ sources |
| Karnataka tariff escalation ~3%/year | Historical analysis of KERC MYT orders, 2015-2025 |

---

## Part 5: What's Out — Module Graveyard

| Feature | Why killed |
|---------|-----------|
| Slab Optimization Engine | KERC removed slabs in FY 2025-26. No optimization targets exist. |
| "Reducing by 11 units saves Rs. 380/month" (old pitch) | Wrong math. Real saving is Rs. 7.18/unit flat, linear. |
| Slab-based bill breakdown in extraction schema | Bills no longer show slab breakdown for domestic LT-1 |
| Pre-April 2025 bill support | Scoped out; those bills get a graceful decline message |
| Commercial (LT-3) tariff handling | Scoped out; v1 is LT-1 Domestic only |
| Four-slab API contract (Rs. 4.10/5.55/7.30/8.55) | Fictional rates from briefing doc — never existed |
| Single-cliff Gruha Jyothi model | Replaced with three-level cliff (v3 finding) |
| CO₂ factor 0.82 / CEA 2023 | Stale. Use 0.710 per CEA v21, Dec 2025. |

---

## Part 6: Assumptions Still Requiring Field Verification

None is blocking; all can be firmed up during real-user testing.

1. **Electricity tax rate** — we have 9% from a Dec 2024 bill. If Karnataka changed this rate in FY 2025-26, bill math is off by a few rupees. Low risk.
2. **FPPCA current rate** — varies monthly. Our Rs. 0.50/unit is a demo-day placeholder. Real bills will show actual.
3. **Tariff code on post-April 2025 MESCOM bills** — the Dec 2024 bill showed "2LT1". KERC calls it "LT-1". Our Gemini extraction accepts both.
4. **Gruha Jyothi enforcement consistency** — some real bills may still show `×1.10` computations if ESCOM systems haven't fully migrated. Our extractor tolerates both formulas during transition.
5. **Whether P&G surcharge appears as a line on GJ bills** — Dec 2024 sample predates the P&G order. A post-April 2025 GJ bill will tell us whether the state absorbs the P&G surcharge for beneficiaries.

---

## Part 7: Version Log

- **v1 (April 17 AM):** Built against pre-April 2025 rates and BESCOM-calculator-inferred slab structure. Wrong on energy slabs and LT-2(a) classification.
- **v2 (April 17 mid-day):** Rebuilt against KERC Tariff Order 2025 PDF. Flat rates, no slabs, LT-1 classification, Gruha Jyothi introduced as first-class module with a single-cliff model.
- **v3 (this doc, April 17 PM):** CO₂ factor updated to 0.710 per CEA v21. Gruha Jyothi cliff rebuilt as three-level with eligibility-at-risk monitoring. Tariff escalation scenarios added for 25-year savings. **This is the source of truth until v4 supersedes it.**
