-- ============================================================================
-- 003_crypto_vda.sql
-- Phase 5.4 — Crypto / VDA tax engine
--
-- Adds an income_type discriminator to realized_gains so equity capital gains
-- and crypto VDA income can coexist in one table but be taxed by different
-- engines. Crypto VDA has NO STCG/LTCG holding classification, so gain_type
-- becomes nullable (crypto rows store NULL).
--
--   income_type = 'equity_capital_gains' -> STCG/LTCG, set-off, LTCG exemption
--   income_type = 'crypto_vda'           -> flat 30%, no set-off, 1% TDS
--   income_type = 'fno_business_income'  -> reserved (F&O uses fno_pnl_entries,
--                                           not realized_gains)
--
-- The tds_credit_ledger table already exists (schema.sql) — no change needed.
-- Run once in the Supabase SQL editor.
-- ============================================================================

-- 1. income_type enum (guarded — CREATE TYPE has no IF NOT EXISTS)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'income_type_enum') THEN
        CREATE TYPE income_type_enum AS ENUM (
            'equity_capital_gains',
            'fno_business_income',
            'crypto_vda'
        );
    END IF;
END $$;

-- 2. income_type column on realized_gains. DEFAULT backfills existing equity
--    rows correctly, so the existing equity insert path keeps working unchanged.
ALTER TABLE public.realized_gains
    ADD COLUMN IF NOT EXISTS income_type income_type_enum
    NOT NULL DEFAULT 'equity_capital_gains';

CREATE INDEX IF NOT EXISTS idx_realized_gains_user_income_type
    ON public.realized_gains(user_id, income_type);

-- 3. gain_type becomes nullable — crypto VDA rows have no STCG/LTCG.
ALTER TABLE public.realized_gains
    ALTER COLUMN gain_type DROP NOT NULL;

-- ============================================================================
-- VALIDATION
-- ============================================================================
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'realized_gains'
  AND column_name IN ('income_type', 'gain_type')
ORDER BY column_name;

SELECT income_type, COUNT(*) FROM public.realized_gains GROUP BY income_type;
