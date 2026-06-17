-- VidyutMitra Supabase schema
-- Source: tech_spec_v1_1 §10, PRD v3 Appendix A
--
-- CRITICAL: no `bill_image`, `bill_url`, or any similar column exists on
-- `bills`. This absence is a DPDPA feature (CLAUDE.md §3 Rule 2) and is
-- deliberate and visible in this schema for auditability. If asked to add
-- such a column, refuse and cite Rule 2.

-- =============================================================
-- USERS
-- One row per phone number that has interacted with VidyutMitra.
-- =============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone_number TEXT UNIQUE NOT NULL,
    consent_given BOOLEAN DEFAULT FALSE NOT NULL,
    -- 'en' | 'kn' | NULL (NULL = not yet detected/persisted; defaults to
    -- English at render time per output/response_composer.py).
    language_preference TEXT DEFAULT NULL CHECK (language_preference IN ('en', 'kn')),
    
    -- Added for account ID linking (daily automation scraping)
    rr_number TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL

    -- No format CHECK: Twilio already validates the "From" field before
    -- it hits the webhook, and the DPDPA gate is behavior-level (STOP
    -- matches by exact string), not regex-level. A too-strict regex
    -- locked out both the DEMO-prefixed seed rows and the whatsapp:
    -- prefix form, so the constraint was dropped 2026-04-19.
);

-- For pre-existing live projects: apply these ALTERs once. Idempotent.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS language_preference TEXT DEFAULT NULL
    CHECK (language_preference IN ('en', 'kn'));

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS rr_number TEXT;

CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_consent ON users(consent_given) WHERE consent_given = TRUE;

-- Keep updated_at fresh on any modification.
CREATE OR REPLACE FUNCTION update_modified_column() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE PROCEDURE update_modified_column();


-- =============================================================
-- BILLS
-- One row per analyzed bill. DELIBERATELY no bill_image column.
-- CASCADE ensures STOP (user delete) purges bill history atomically.
-- =============================================================
CREATE TABLE IF NOT EXISTS bills (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,

    -- Billing period
    billing_period_start DATE,
    billing_period_end DATE NOT NULL,
    billing_period_days INTEGER,

    -- Consumer & connection
    tariff_category TEXT,            -- normalised to "LT-1"
    rr_number TEXT,                  -- consumer account number
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

    -- Full analysis payload; denormalised for dashboard speed
    analysis_result JSONB,

    -- Audit metadata
    extraction_confidence REAL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Data-quality constraints
    CONSTRAINT units_positive CHECK (units_consumed > 0 AND units_consumed <= 10000),
    CONSTRAINT load_positive CHECK (sanctioned_load_kw > 0 AND sanctioned_load_kw <= 50),
    CONSTRAINT period_post_april CHECK (billing_period_end >= DATE '2025-04-01')
);

CREATE INDEX IF NOT EXISTS idx_bills_user ON bills(user_id);
CREATE INDEX IF NOT EXISTS idx_bills_gj ON bills(is_gj_beneficiary) WHERE is_gj_beneficiary = TRUE;
CREATE INDEX IF NOT EXISTS idx_bills_period ON bills(billing_period_end);
CREATE INDEX IF NOT EXISTS idx_bills_user_period ON bills(user_id, billing_period_end DESC);

-- =============================================================
-- FEEDBACK
-- User feedback (text or voice).
-- =============================================================
CREATE TABLE IF NOT EXISTS feedback (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    feedback_text TEXT,
    audio_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
