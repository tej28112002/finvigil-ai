# FinVigil AI — Project Status

## Completed Phases (36/45 — 80%)
Phase 1    Architecture Design
Phase 2    Database Schema
Phase 2.5  Supabase Deployment
Phase 3.1  Backend Foundation
Phase 3.2  ORM Models
Phase 3.3  Repository Layer
Phase 3.4  Service Layer Foundation
Phase 3.5  FIFO Engine
Phase 4.1  Broker Connection Endpoints
Phase 4.2  Trade Ingestion Endpoints
Phase 4.3  Holding Lot Endpoints
Phase 4.4  Dashboard Endpoints
Phase 4.5  Zerodha OAuth
Phase 4.6  CSV Import
Phase 4.7  Live Price Feed
Phase 5.1  Portfolio Reconstruction
Phase 5.2  STCG/LTCG Classification
Phase 5.3  F&O P&L Engine
Phase 5.4  Crypto/VDA Tax Engine
Phase 6.1  Tax Engine Core
Phase 6.2  CA-Readable Tax Export
Phase 6.3  Corporate Action Adjustments
Phase 7    Tax-Loss Harvesting Engine
Phase 8    Portfolio Replay Engine
Phase 9    Monte Carlo Simulation
Phase 11.2 Real Authentication (ES256)
Phase 13 Stage 1  Frontend Foundation
Phase 13 Stage 2A Design System
Phase 13 Stage 2B All App Pages
Phase 13 Stage 2C Marketing Homepage
Phase 13 Stage 2D Polish Pass
AIS        AIS Reconciliation (upload, parse, auto-match, resolve — FR-AIS-01 to 04)
FR-AIS-05  Schema-driven ITR-3 JSON Export (Admin Panel schema upload, no-code annual update)
Phase 11.1 CA Export ZIP Bundle (ITR-3 schedules + CSV + harvest data + README, in-memory zip)
Phase 12a  Razorpay Billing (subscription model, webhook handler w/ HMAC verification, entitlement enforcement, grace period)
Phase 12c  Razorpay real-credential integration (plan IDs, API keys, webhook secret configured; create/cancel/webhook all verified against Razorpay's real test-mode API — not just self-signed local tests)
Phase 10   Voice Journal Pipeline (Groq Whisper STT, fixed psychology taxonomy, text-entry fallback, cascade delete — FR-JRN-01 to 03)
Phase 14   Admin Panel (role-based access: user/support/admin; user management; feature flags; scoped read-only impersonation + broker resync; full audit log — FR-ADM-01/02)

## Remaining Phases (9/45 — 20%)
Phase 12b  Celery + Redis (no scheduled jobs exist yet — grace-period downgrade is lazy/read-triggered via GET /billing/subscription, not proactive; also blocks FR-HAR-03's daily 06:00 IST harvest job)
Phase 15   Testing + CA Validation
Phase 16   Closed Beta
Phase 17   Production Launch

## Known Billing Limitations (Phase 12c)
- `subscriptions.razorpay_subscription_id` (VARCHAR(255), indexed) now exists and is populated by create_subscription() and read by cancel_subscription() — verified end-to-end against Razorpay's real test API: create returned a real `sub_...` ID + `short_url` checkout link, and cancel actually called Razorpay (not just the local DB).
- Webhook correlation is still via `notes.finvigil_user_id` (set at creation), not a `WHERE razorpay_subscription_id = ...` lookup — both would work now that the column exists; not changed since correctness doesn't depend on it and re-plumbing wasn't asked for.
- RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET / RAZORPAY_PLAN_PRO_MONTHLY / RAZORPAY_PLAN_PRO_ANNUAL / RAZORPAY_PLAN_PREMIUM_MONTHLY / RAZORPAY_PLAN_PREMIUM_ANNUAL are all set in backend/.env (test-mode). create-subscription, cancel-subscription, and the webhook signature+event flow were all verified against Razorpay's real test API, not just local self-signed tests.
- Still open: no Celery job to proactively downgrade an expired-grace subscription (lazy/read-triggered only — see Phase 12b above); webhooks are correlated by notes, not the new ID column.

## Known Journal Limitations (Phase 10)
- GROQ_API_KEY is now set in backend/.env and POST /journal/entries/audio was verified against Groq's REAL Whisper API — a synthesized speech WAV file was transcribed and the returned text matched the source audio exactly, word for word. The text-entry path (POST /journal/entries/text) was also fully tested (create, tag, list, ownership isolation, cascade delete).
- The 12-tag psychology taxonomy in app/core/journal_taxonomy.py (fear, greed, fomo, revenge_trading, overconfidence, hesitation, impatience, discipline, patience, regret, anxiety, boredom) is this build's own reasonable default — the BRD names "Fixed psychology taxonomy" as a requirement but doesn't enumerate the actual tags. Easy to revise; every tag name is checked against this one list in JournalService.add_tags().
- No AI-based auto-tag-suggestion or LLM coaching feedback was built — BRD's locked FR-JRN-01/02/03 text only requires transcription + fixed tagging + cascade delete; an older informal project doc mentioned "linked to trades" and AI coaching, but that's not in the locked BRD, so it wasn't built.

## Known Admin Panel Limitations (Phase 14)
- "Impersonation" is deliberately NOT a real session swap. There's no SUPABASE_SERVICE_ROLE_KEY in this project to mint a session as another user, and building that would be a materially bigger, more security-sensitive feature than what was scoped. Instead, GET /admin/users/{id}/impersonate-view returns a read-only data summary (profile, subscription, broker connections, dashboard totals) queried on the admin's behalf — the admin never "becomes" the user. The one write BRD FR-ADM-02 explicitly permits (broker resync) is a separate endpoint, always attributed to the admin's own action in admin_audit_logs, never disguised as the target user acting.
- "User notified" (also FR-ADM-02) is NOT implemented — no notification system (FR-NOT-*) exists yet in this project to notify a user that their account was viewed.
- Role model is a single `role` column (user/support/admin) on user_tax_personas, not a separate roles/permissions table — sufficient for the 3-tier hierarchy asked for for this phase. The original `is_admin` boolean is kept on the table (backfilled to role='admin' where TRUE) but is no longer read by any code path.
- DPDP data export on request (FR-ADM-03) was NOT built this phase — only FR-ADM-01 (feature flags) and FR-ADM-02 (impersonation, scoped as above) were in the explicit build list.
- Feature flags are checked via AdminService.check_feature_flag() but nothing in the app calls it yet — the mechanism exists and is tested (global default + per-user override precedence verified against the real DB), but no existing feature (Monte Carlo, Harvest, etc.) has been wired to actually consult a flag.

## Marketing Pages (Pricing, About)
- New `frontend/app/(marketing)/` route group with a shared layout (nav + footer), `pricing/page.tsx`, and `about/page.tsx`. Nav SOON badges removed — Pricing/About are real links now.
- Bug found and fixed while building this: `frontend/proxy.ts` (middleware) only allowlisted "/" and "/login" as public routes — any other path, including the new /pricing and /about, redirected a logged-out visitor straight to /login. Fixed to allowlist all three marketing pages for logged-out access, while still bouncing a LOGGED-IN user away from "/" and "/login" only (not from /pricing or /about, since a logged-in user should still be able to view those).
- `docs/todo.md` created — tracks deferred About-page sections (problem story, founder section, FAQ, etc.) and other cross-phase TODOs.

## Architecture Rules
- flush() in repositories, never commit()
- commit() only in get_db() in session.py
- Decimal(str()) for all money math
- get_current_user_id() on all endpoints
- Import get_assessment_year from app.core.tax_utils
- pool_size=5, max_overflow=1 in session.py
- All endpoints need Depends(get_current_user_id)
  EXCEPT /brokers/zerodha/callback

## Test Constants
user_id = 765984b3-fd6b-4091-8d24-6808d8680b3a
broker_connection_id = b5ea19b2-3232-4eac-80af-107a6a5d67a4
RELIANCE instrument_id = 0e622c58-467d-40bc-9291-d9e11f3f9205
