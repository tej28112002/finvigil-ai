-- ============================================================================
-- 002_fno_pnl_entries.sql
-- Phase 5.3 — F&O P&L Engine
--
-- Creates the fno_pnl_entries table. F&O P&L is BUSINESS INCOME (PGBP),
-- kept completely separate from realized_gains (which is equity capital
-- gains only — STCG/LTCG). This separation is deliberate: F&O has no
-- holding-period classification, no LTCG exemption, and is taxed as
-- speculative (intraday) or non-speculative (positional) business income.
--
-- Each row is one FIFO-matched buy↔sell leg. Unmatched sells (expired /
-- shorted contracts) are stored with buy_trade_id NULL, buy_price 0, and
-- profit_loss = sell_price × quantity. Open positions (unmatched buys) are
-- NOT stored — they are derived from trades on demand by the service.
--
-- Run this once in the Supabase SQL editor.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.fno_pnl_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE RESTRICT,
    instrument_id UUID NOT NULL REFERENCES public.instruments(id) ON DELETE RESTRICT,
    buy_trade_id UUID REFERENCES public.trades(id) ON DELETE SET NULL,
    sell_trade_id UUID NOT NULL REFERENCES public.trades(id) ON DELETE CASCADE,
    symbol VARCHAR(255) NOT NULL,
    quantity NUMERIC(18, 8) NOT NULL CHECK (quantity > 0),
    buy_price NUMERIC(18, 8) NOT NULL CHECK (buy_price >= 0),
    sell_price NUMERIC(18, 8) NOT NULL CHECK (sell_price >= 0),
    buy_time TIMESTAMPTZ,
    sell_time TIMESTAMPTZ NOT NULL,
    profit_loss NUMERIC(18, 8) NOT NULL,
    is_intraday BOOLEAN NOT NULL DEFAULT FALSE,
    assessment_year VARCHAR(9) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fno_pnl_entries_user
    ON public.fno_pnl_entries(user_id);
CREATE INDEX IF NOT EXISTS idx_fno_pnl_entries_user_ay
    ON public.fno_pnl_entries(user_id, assessment_year);
CREATE INDEX IF NOT EXISTS idx_fno_pnl_entries_instrument
    ON public.fno_pnl_entries(instrument_id);

-- ============================================================================
-- RLS — tenant isolation (consistent with 001_initial_hardening.sql).
-- The app connects as the postgres role, which bypasses RLS; this policy
-- protects the table if/when access moves to the authenticated role.
-- ============================================================================
ALTER TABLE public.fno_pnl_entries ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'fno_pnl_entries'
          AND policyname = 'tenant_isolation_policy'
    ) THEN
        EXECUTE 'CREATE POLICY "tenant_isolation_policy" ON public.fno_pnl_entries FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);';
    END IF;
END $$;

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- 1. Confirm table + columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'fno_pnl_entries'
ORDER BY ordinal_position;

-- 2. Confirm indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'fno_pnl_entries'
ORDER BY indexname;

-- 3. Confirm RLS enabled + policy
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public' AND tablename = 'fno_pnl_entries';
