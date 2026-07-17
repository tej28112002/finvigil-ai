CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TYPE tax_persona_enum AS ENUM ('ITR-3', 'ITR-4');
CREATE TYPE subscription_plan_enum AS ENUM ('free', 'pro_monthly', 'pro_annual', 'premium_monthly', 'premium_annual');
CREATE TYPE subscription_status_enum AS ENUM ('active', 'past_due', 'canceled', 'grace');
CREATE TYPE broker_enum AS ENUM ('zerodha', 'groww', 'upstox', 'wazirx', 'coindcx', 'csv');
CREATE TYPE broker_status_enum AS ENUM ('active', 'disconnected', 'syncing', 'error');
CREATE TYPE instrument_type_enum AS ENUM ('equity', 'fno', 'mf', 'crypto');
CREATE TYPE trade_type_enum AS ENUM ('buy', 'sell');
CREATE TYPE lot_status_enum AS ENUM ('open', 'partial', 'closed');
CREATE TYPE ais_match_status_enum AS ENUM ('matched', 'mismatch', 'unresolved');
CREATE TYPE harvest_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE job_status_enum AS ENUM ('pending', 'processing', 'completed', 'failed');

CREATE TABLE public.user_tax_personas (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    tax_persona tax_persona_enum NOT NULL DEFAULT 'ITR-3',
    ay_overrides_remaining INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_id subscription_plan_enum NOT NULL DEFAULT 'free',
    status subscription_status_enum NOT NULL DEFAULT 'active',
    is_active BOOLEAN DEFAULT TRUE,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email_enabled BOOLEAN DEFAULT TRUE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    in_app_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.instruments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    isin VARCHAR(20) UNIQUE,
    symbol VARCHAR(50) NOT NULL,
    type instrument_type_enum NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(symbol, type)
);

CREATE TABLE public.broker_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    broker_name broker_enum NOT NULL,
    status broker_status_enum NOT NULL DEFAULT 'active',
    -- BYOK (Phase 16): each user supplies their own broker app credentials.
    -- api_key is a client identifier, not a secret (Kite Connect's own docs
    -- say as much) -- stored plain. The other three are genuine secrets and
    -- live in Supabase Vault, referenced here by their vault.secrets UUID.
    api_key VARCHAR(255),
    api_secret_kms_id VARCHAR(255),
    access_token_kms_id VARCHAR(255),
    totp_secret_kms_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, broker_name)
);

CREATE TABLE public.trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    broker_connection_id UUID NOT NULL REFERENCES public.broker_connections(id) ON DELETE CASCADE,
    instrument_id UUID NOT NULL REFERENCES public.instruments(id) ON DELETE RESTRICT,
    broker_trade_id VARCHAR(255) NOT NULL,
    trade_type trade_type_enum NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL CHECK (quantity > 0),
    price NUMERIC(18, 8) NOT NULL CHECK (price >= 0),
    execution_time TIMESTAMPTZ NOT NULL,
    idempotency_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(broker_connection_id, broker_trade_id)
);

CREATE TABLE public.holding_lots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    broker_connection_id UUID NOT NULL REFERENCES public.broker_connections(id) ON DELETE CASCADE,
    instrument_id UUID NOT NULL REFERENCES public.instruments(id) ON DELETE RESTRICT,
    source_trade_id UUID REFERENCES public.trades(id) ON DELETE SET NULL,
    quantity_bought NUMERIC(18, 8) NOT NULL CHECK (quantity_bought > 0),
    quantity_remaining NUMERIC(18, 8) NOT NULL CHECK (quantity_remaining >= 0),
    buy_price NUMERIC(18, 8) NOT NULL CHECK (buy_price >= 0),
    buy_date TIMESTAMPTZ NOT NULL,
    status lot_status_enum NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (quantity_remaining <= quantity_bought)
);

CREATE TABLE public.charges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trade_id UUID REFERENCES public.trades(id) ON DELETE CASCADE,
    charge_type VARCHAR(50) NOT NULL,
    amount NUMERIC(18, 8) NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.tds_credit_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_trade_id UUID REFERENCES public.trades(id) ON DELETE SET NULL,
    amount NUMERIC(18, 8) NOT NULL CHECK (amount >= 0),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.corporate_action_adjustments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    instrument_id UUID NOT NULL REFERENCES public.instruments(id) ON DELETE RESTRICT,
    action_type VARCHAR(50) NOT NULL,
    ratio NUMERIC(18, 8) NOT NULL CHECK (ratio >= 0),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.ais_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    assessment_year VARCHAR(9) NOT NULL,
    version INT NOT NULL,
    is_latest BOOLEAN NOT NULL DEFAULT FALSE,
    raw_json JSONB,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, assessment_year, version)
);

CREATE TABLE public.ais_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ais_upload_id UUID NOT NULL REFERENCES public.ais_uploads(id) ON DELETE CASCADE,
    section_code VARCHAR(50) NOT NULL,
    description TEXT,
    reported_amount NUMERIC(18, 8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.ais_match_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    ais_upload_id UUID NOT NULL REFERENCES public.ais_uploads(id) ON DELETE CASCADE,
    ais_line_id UUID NOT NULL REFERENCES public.ais_lines(id) ON DELETE CASCADE,
    holding_lot_id UUID REFERENCES public.holding_lots(id) ON DELETE SET NULL,
    match_status ais_match_status_enum NOT NULL,
    mismatch_type VARCHAR(50),
    resolution_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.harvest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    assessment_year VARCHAR(9) NOT NULL,
    status harvest_status_enum NOT NULL DEFAULT 'pending',
    total_tax_saved_estimate NUMERIC(18, 8) NOT NULL CHECK (total_tax_saved_estimate >= 0) DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.harvest_recommendation_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    harvest_run_id UUID NOT NULL REFERENCES public.harvest_runs(id) ON DELETE CASCADE,
    holding_lot_id UUID NOT NULL REFERENCES public.holding_lots(id) ON DELETE CASCADE,
    quantity_to_sell NUMERIC(18, 8) NOT NULL CHECK (quantity_to_sell > 0),
    simulated_stcg_ltcg NUMERIC(18, 8) NOT NULL,
    savings_amount NUMERIC(18, 8) NOT NULL CHECK (savings_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.replay_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    parameters JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.replay_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    replay_scenario_id UUID NOT NULL REFERENCES public.replay_scenarios(id) ON DELETE CASCADE,
    result_data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    transcript TEXT NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.journal_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    journal_entry_id UUID NOT NULL REFERENCES public.journal_entries(id) ON DELETE CASCADE,
    tag_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(journal_entry_id, tag_name)
);

CREATE TABLE public.ca_share_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.ca_export_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status job_status_enum NOT NULL DEFAULT 'pending',
    s3_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID NOT NULL REFERENCES auth.users(id),
    target_user_id UUID NOT NULL REFERENCES auth.users(id),
    action VARCHAR(255) NOT NULL,
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.dashboard_projections (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    total_equity_value NUMERIC(18, 8) NOT NULL DEFAULT 0 CHECK (total_equity_value >= 0),
    total_crypto_value NUMERIC(18, 8) NOT NULL DEFAULT 0 CHECK (total_crypto_value >= 0),
    day_pnl NUMERIC(18, 8) NOT NULL DEFAULT 0,
    unrealized_pnl NUMERIC(18, 8) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);