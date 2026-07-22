-- ============================================================================
-- 006_backtest_tables.sql
-- Strategy Backtester — strategy definitions, legs, and run results.
--
-- Three tables: backtest_strategies (one row per saved strategy),
-- backtest_legs (1..10 legs per strategy, replaced wholesale on every
-- save — see BacktestRepository.upsert_legs), backtest_runs (one row per
-- simulation, result stored as JSONB so the shape can evolve without a
-- migration once real F&O historical data lands).
--
-- The simulation engine itself is deliberately simplified for this phase:
-- it runs against the user's existing realized_gains (equity only). Any
-- strategy with an options leg returns status='insufficient_data' with an
-- honest "coming soon" message instead of fabricating options P&L.
--
-- Run this once in the Supabase SQL editor.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strategy_type_enum') THEN
        CREATE TYPE strategy_type_enum AS ENUM ('intraday', 'btst', 'positional');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'underlying_from_enum') THEN
        CREATE TYPE underlying_from_enum AS ENUM ('cash', 'futures');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'square_off_enum') THEN
        CREATE TYPE square_off_enum AS ENUM ('partial', 'complete');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trail_apply_enum') THEN
        CREATE TYPE trail_apply_enum AS ENUM ('all', 'sl_legs');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sl_target_type_enum') THEN
        CREATE TYPE sl_target_type_enum AS ENUM ('points', 'percentage', 'trailing');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reentry_type_enum') THEN
        CREATE TYPE reentry_type_enum AS ENUM
            ('re_asap', 're_asap_reverse', 're_momentum', 're_momentum_reverse');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'overall_sl_target_type_enum') THEN
        CREATE TYPE overall_sl_target_type_enum AS ENUM ('mtm', 'premium_pct');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'strike_type_enum') THEN
        CREATE TYPE strike_type_enum AS ENUM (
            'atm', 'otm', 'itm', 'premium_range', 'closest_premium',
            'premium_gte', 'straddle_width', 'pct_of_atm',
            'synthetic_future', 'atm_premium_pct'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'expiry_type_enum') THEN
        CREATE TYPE expiry_type_enum AS ENUM ('weekly', 'next_weekly', 'monthly', 'next_monthly');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'segment_enum') THEN
        CREATE TYPE segment_enum AS ENUM ('futures', 'options');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leg_position_enum') THEN
        CREATE TYPE leg_position_enum AS ENUM ('buy', 'sell');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'option_type_enum') THEN
        CREATE TYPE option_type_enum AS ENUM ('CE', 'PE');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'backtest_status_enum') THEN
        CREATE TYPE backtest_status_enum AS ENUM
            ('pending', 'running', 'completed', 'failed', 'insufficient_data');
    END IF;
END $$;

-- ============================================================================
-- Table 1: Strategy definitions
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.backtest_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL DEFAULT 'My Strategy',

    -- Section 1: Instrument
    instrument VARCHAR(50) NOT NULL DEFAULT 'NIFTY',
    underlying_from underlying_from_enum NOT NULL DEFAULT 'cash',

    -- Section 2: Entry settings
    strategy_type strategy_type_enum NOT NULL DEFAULT 'intraday',
    entry_time TIME NOT NULL DEFAULT '09:20',
    exit_time TIME NOT NULL DEFAULT '15:15',
    no_reentry_after_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    no_reentry_after_time TIME,
    overall_momentum_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    overall_momentum_direction VARCHAR(10),
    overall_momentum_type VARCHAR(15),
    overall_momentum_value NUMERIC(10, 2),

    -- Section 3: Legwise settings
    square_off square_off_enum NOT NULL DEFAULT 'partial',
    trail_sl_to_breakeven BOOLEAN NOT NULL DEFAULT FALSE,
    trail_sl_apply_to trail_apply_enum DEFAULT 'all',

    -- Section 5: Overall SL
    overall_sl_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    overall_sl_type overall_sl_target_type_enum,
    overall_sl_value NUMERIC(12, 2),
    overall_sl_reentry_type reentry_type_enum,
    overall_sl_max_reentries INT DEFAULT 1,

    -- Section 5: Overall Target
    overall_target_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    overall_target_type overall_sl_target_type_enum,
    overall_target_value NUMERIC(12, 2),
    overall_target_reentry_type reentry_type_enum,
    overall_target_max_reentries INT DEFAULT 1,

    -- Section 5: Lock Profit
    lock_profit_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    lock_profit_trigger NUMERIC(12, 2),
    lock_profit_lock_at NUMERIC(12, 2),

    -- Section 5: Lock & Trail
    lock_and_trail_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    lock_and_trail_trigger NUMERIC(12, 2),
    lock_and_trail_lock_at NUMERIC(12, 2),
    lock_and_trail_trail_by_gain NUMERIC(12, 2),
    lock_and_trail_trail_by_amount NUMERIC(12, 2),

    -- Section 5: Overall Trail SL
    overall_trail_sl_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    overall_trail_sl_type overall_sl_target_type_enum,
    overall_trail_sl_gain NUMERIC(12, 2),
    overall_trail_sl_move NUMERIC(12, 2),

    -- Section 6: Duration
    start_date DATE NOT NULL DEFAULT '2024-01-01',
    end_date DATE NOT NULL DEFAULT CURRENT_DATE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_strategies_user
    ON public.backtest_strategies(user_id);

-- ============================================================================
-- Table 2: Individual legs
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.backtest_legs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES public.backtest_strategies(id) ON DELETE CASCADE,
    leg_order INT NOT NULL DEFAULT 1,
    segment segment_enum NOT NULL DEFAULT 'options',
    position leg_position_enum NOT NULL DEFAULT 'sell',
    quantity_lots INT NOT NULL DEFAULT 1,

    -- Options-only fields (null for futures)
    option_type option_type_enum,
    expiry expiry_type_enum,
    strike_type strike_type_enum DEFAULT 'atm',
    strike_value NUMERIC(10, 2),
    strike_value2 NUMERIC(10, 2),

    -- Per-leg risk
    sl_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    sl_type sl_target_type_enum,
    sl_value NUMERIC(10, 2),
    target_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    target_type sl_target_type_enum,
    target_value NUMERIC(10, 2),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT max_10_legs CHECK (leg_order BETWEEN 1 AND 10)
);

CREATE INDEX IF NOT EXISTS idx_backtest_legs_strategy
    ON public.backtest_legs(strategy_id);

-- ============================================================================
-- Table 3: Backtest run results
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.backtest_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES public.backtest_strategies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status backtest_status_enum NOT NULL DEFAULT 'pending',
    result_json JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
    ON public.backtest_runs(strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_user
    ON public.backtest_runs(user_id);

-- ============================================================================
-- RLS — tenant isolation (consistent with 001_initial_hardening.sql /
-- 002_fno_pnl_entries.sql). The app connects as the postgres role, which
-- bypasses RLS; these policies protect the tables if/when access moves to
-- the authenticated role.
-- ============================================================================
ALTER TABLE public.backtest_strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtest_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.backtest_runs ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'backtest_strategies'
          AND policyname = 'tenant_isolation_policy'
    ) THEN
        EXECUTE 'CREATE POLICY "tenant_isolation_policy" ON public.backtest_strategies FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'backtest_runs'
          AND policyname = 'tenant_isolation_policy'
    ) THEN
        EXECUTE 'CREATE POLICY "tenant_isolation_policy" ON public.backtest_runs FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);';
    END IF;

    -- Legs have no user_id column of their own — access is inherited
    -- through the owning strategy.
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'backtest_legs'
          AND policyname = 'legs_via_strategy'
    ) THEN
        EXECUTE 'CREATE POLICY "legs_via_strategy" ON public.backtest_legs FOR ALL USING (EXISTS (SELECT 1 FROM public.backtest_strategies s WHERE s.id = strategy_id AND s.user_id = auth.uid()));';
    END IF;
END $$;

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- 1. Confirm all three tables + columns exist
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('backtest_strategies', 'backtest_legs', 'backtest_runs')
ORDER BY table_name, ordinal_position;

-- 2. Confirm indexes
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN ('backtest_strategies', 'backtest_legs', 'backtest_runs')
ORDER BY tablename, indexname;

-- 3. Confirm RLS enabled + policies
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('backtest_strategies', 'backtest_legs', 'backtest_runs');

SELECT tablename, policyname, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('backtest_strategies', 'backtest_legs', 'backtest_runs')
ORDER BY tablename;
