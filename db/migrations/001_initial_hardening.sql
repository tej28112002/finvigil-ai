-- ============================================================================
-- FIX 1: Foreign Key Safety & Constraints (trades.user_id)
-- ============================================================================

-- Safely ensure user_id cannot be null for data integrity, raising meaningful error on failure
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM public.trades WHERE user_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Cannot set NOT NULL: public.trades.user_id contains NULL values. Migration aborted.';
    ELSE
        -- Safe to alter since we just proved the data is clean
        ALTER TABLE public.trades 
            ALTER COLUMN user_id SET NOT NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conrelid = 'public.trades'::regclass AND conname = 'trades_user_id_fkey'
    ) THEN
        ALTER TABLE public.trades 
            -- CHANGED: Using RESTRICT instead of CASCADE.
            -- Deleting a user with financial history will now safely fail, forcing an explicit soft-delete strategy or archival process instead of vanishing audit data.
            ADD CONSTRAINT trades_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================================================
-- FIX 2: Add Column (Safe) to holding_lots + Index
-- ============================================================================
ALTER TABLE public.holding_lots 
    ADD COLUMN IF NOT EXISTS source_trade_id UUID REFERENCES public.trades(id);

-- Add index for audit/debug performance
CREATE INDEX IF NOT EXISTS idx_holding_lots_source_trade_id 
    ON public.holding_lots(source_trade_id);

-- ============================================================================
-- FIX 3: Soft Delete Columns
-- ============================================================================
ALTER TABLE public.ais_uploads 
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

ALTER TABLE public.harvest_runs 
    ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

-- ============================================================================
-- FIX 4: Performance Index on Trades
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_trades_user_instrument 
    ON public.trades(user_id, instrument_id);

-- ============================================================================
-- FIX 5: Partition Strategy (Comment Only)
-- ============================================================================
COMMENT ON TABLE public.trades 
    IS 'trades should be partitioned monthly by execution_time';

-- ============================================================================
-- FIX 6: 🔥 RLS (CRITICAL - MUST BE PERFECT)
-- ============================================================================
DO $$
DECLARE
    t_name text;
BEGIN
    FOR t_name IN 
        SELECT unnest(ARRAY[
            'trades', 
            'holding_lots', 
            'ais_uploads', 
            'ais_match_results', 
            'harvest_runs', 
            'harvest_recommendation_lines', 
            'replay_scenarios', 
            'replay_runs', 
            'journal_entries', 
            'journal_tags', 
            'broker_connections',
            'dashboard_projections'
        ])
    LOOP
        -- 1. Enable RLS
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t_name);
        
        -- 2. Create policy ONLY IF NOT EXISTS
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE schemaname = 'public' 
              AND tablename = t_name 
              AND policyname = 'tenant_isolation_policy'
        ) THEN
            EXECUTE format(
                'CREATE POLICY "tenant_isolation_policy" ON public.%I FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);', 
                t_name
            );
        END IF;
    END LOOP;
END $$;

-- ============================================================================
-- VALIDATION QUERIES
-- ============================================================================

-- 1. Verify RLS is enabled on all target tables
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN (
    'trades', 'holding_lots', 'ais_uploads', 'ais_match_results', 
    'harvest_runs', 'harvest_recommendation_lines', 'replay_scenarios', 
    'replay_runs', 'journal_entries', 'journal_tags', 'broker_connections', 'dashboard_projections'
  )
ORDER BY tablename;

-- 2. Verify all RLS policies exist and map exactly to FOR ALL access mappings
SELECT tablename, policyname, roles, cmd, qual, with_check 
FROM pg_policies 
WHERE schemaname = 'public' 
  AND tablename IN (
    'trades', 'holding_lots', 'ais_uploads', 'ais_match_results', 
    'harvest_runs', 'harvest_recommendation_lines', 'replay_scenarios', 
    'replay_runs', 'journal_entries', 'journal_tags', 'broker_connections', 'dashboard_projections'
  )
  AND policyname = 'tenant_isolation_policy'
ORDER BY tablename;

-- 3. Verify Indexes exist (Trades Composite & Holding Lots FK)
SELECT tablename, indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public' 
  AND (
    (tablename = 'trades' AND indexname = 'idx_trades_user_instrument') OR
    (tablename = 'holding_lots' AND indexname = 'idx_holding_lots_source_trade_id')
  )
ORDER BY tablename, indexname;

-- 4. Verify newly added columns & NOT NULL checks exist in the catalog
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND (
    (table_name = 'holding_lots' AND column_name = 'source_trade_id') OR 
    (table_name IN ('ais_uploads', 'harvest_runs') AND column_name = 'is_deleted') OR
    (table_name = 'trades' AND column_name = 'user_id')
  )
ORDER BY table_name, column_name;
