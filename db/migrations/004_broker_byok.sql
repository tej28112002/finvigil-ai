-- ============================================================================
-- 004_broker_byok.sql
-- Phase 16 (BYOK) — bring-your-own-broker-API-key model
--
-- Replaces the single shared Zerodha app key (env vars) with per-user
-- credentials stored on broker_connections. credentials_kms_id previously
-- held only the Vault UUID for the OAuth access token; renamed to
-- access_token_kms_id now that api_secret and totp_secret get their own
-- Vault-backed columns alongside it.
--
--   api_key             — plain column. Not secret (Kite Connect's own docs:
--                          "your API KEY can be distributed on the client
--                          app but your API SECRET should be stored on your
--                          backend server").
--   api_secret_kms_id    — Vault secret UUID (Zerodha, Upstox).
--   access_token_kms_id  — Vault secret UUID (renamed from credentials_kms_id;
--                          the daily/session access token, all brokers).
--   totp_secret_kms_id   — Vault secret UUID (Groww's TOTP-flow credential).
--
-- Run once in the Supabase SQL editor.
-- ============================================================================

ALTER TABLE public.broker_connections
    ADD COLUMN IF NOT EXISTS api_key VARCHAR(255);

ALTER TABLE public.broker_connections
    ADD COLUMN IF NOT EXISTS api_secret_kms_id VARCHAR(255);

ALTER TABLE public.broker_connections
    ADD COLUMN IF NOT EXISTS totp_secret_kms_id VARCHAR(255);

-- Guarded rename: only rename if the old name still exists and the new
-- one doesn't (safe to re-run).
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'broker_connections'
          AND column_name = 'credentials_kms_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'broker_connections'
          AND column_name = 'access_token_kms_id'
    ) THEN
        ALTER TABLE public.broker_connections
            RENAME COLUMN credentials_kms_id TO access_token_kms_id;
    END IF;
END $$;

-- ============================================================================
-- VALIDATION
-- ============================================================================
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'broker_connections'
ORDER BY ordinal_position;
