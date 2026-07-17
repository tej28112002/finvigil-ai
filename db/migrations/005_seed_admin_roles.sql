-- Migration 005: Seed admin roles for tejaspawar2811tej@gmail.com (and Aniket's email once known).
-- Run this in the Supabase SQL editor after deploying Phase 17.
--
-- Sets the named user to role='admin' in user_tax_personas.
-- Uses INSERT … ON CONFLICT so it's safe to run multiple times.
-- For every other existing user, does nothing (they default to 'user').

-- Teja (owner)
INSERT INTO user_tax_personas (user_id, tax_persona, role, ay_overrides_remaining, is_admin)
SELECT id, 'ITR-3', 'admin', 1, true
FROM auth.users
WHERE email = 'tejaspawar2811tej@gmail.com'
ON CONFLICT (user_id) DO UPDATE SET role = 'admin', is_admin = true;

-- Aniket — replace the placeholder email below once identified.
-- To find his email: run `SELECT id, email FROM auth.users ORDER BY created_at;`
-- in the Supabase SQL editor and look for his account.
--
-- INSERT INTO user_tax_personas (user_id, tax_persona, role, ay_overrides_remaining, is_admin)
-- SELECT id, 'ITR-3', 'admin', 1, true
-- FROM auth.users
-- WHERE email = 'aniket@example.com'   -- << replace
-- ON CONFLICT (user_id) DO UPDATE SET role = 'admin', is_admin = true;
