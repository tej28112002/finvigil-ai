-- Migration 007 — Trade Analysis Results (AI Journaling LLM pipeline)
--
-- DOCUMENTATION ONLY. This table was already created directly in Supabase
-- before this migration file was written. The SQL below reproduces exactly
-- what is live (verified column-by-column, including constraints and
-- indexes, against information_schema/pg_constraint/pg_indexes on the real
-- project) so the schema is captured in version control. Do NOT re-run
-- this file against a database where the table already exists.

CREATE TABLE public.trade_analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    trade_count INT NOT NULL DEFAULT 0,
    analysis_type VARCHAR(20) NOT NULL DEFAULT 'weekly',
    analysis_json JSONB NOT NULL,
    raw_llm_output TEXT,
    compared_with_id UUID REFERENCES public.trade_analysis_results(id),
    llm_model VARCHAR(50) DEFAULT 'llama-3.3-70b-versatile',
    prompt_version VARCHAR(10) DEFAULT 'v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trade_analysis_user_date
    ON public.trade_analysis_results (user_id, week_start DESC);
