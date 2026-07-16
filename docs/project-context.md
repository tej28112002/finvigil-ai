# FinVigil AI — Project Status

## Completed Phases (37/45 — 82%)
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
Phase 12b  Celery + Redis (proactive grace-period downgrade + FR-HAR-03's daily 06:00 IST harvest job — see below)

## Remaining Phases (8/45 — 18%)
Phase 15   Testing + CA Validation
Phase 16   Closed Beta
Phase 17   Production Launch

## Known Billing Limitations (Phase 12c)
- `subscriptions.razorpay_subscription_id` (VARCHAR(255), indexed) now exists and is populated by create_subscription() and read by cancel_subscription() — verified end-to-end against Razorpay's real test API: create returned a real `sub_...` ID + `short_url` checkout link, and cancel actually called Razorpay (not just the local DB).
- Webhook correlation is still via `notes.finvigil_user_id` (set at creation), not a `WHERE razorpay_subscription_id = ...` lookup — both would work now that the column exists; not changed since correctness doesn't depend on it and re-plumbing wasn't asked for.
- RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET / RAZORPAY_PLAN_PRO_MONTHLY / RAZORPAY_PLAN_PRO_ANNUAL / RAZORPAY_PLAN_PREMIUM_MONTHLY / RAZORPAY_PLAN_PREMIUM_ANNUAL are all set in backend/.env (test-mode). create-subscription, cancel-subscription, and the webhook signature+event flow were all verified against Razorpay's real test API, not just local self-signed tests.
- Proactive grace-period downgrade now exists (Phase 12b, below) — the lazy/read-triggered path via GET /billing/subscription is unchanged and still runs too, both call the same SubscriptionService.reconcile_expired_grace(). Webhooks are still correlated by notes, not the new ID column (unchanged from Phase 12c).

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

## Phase 12b — Celery + Redis
- Broker/backend: Upstash Redis over TLS. `REDIS_URL` in `backend/.env` MUST use `rediss://` not `redis://` — verified directly against kombu's source (the library Celery's Redis transport is built on): `rediss://` is what switches kombu to `redis.SSLConnection`, `redis://` stays on a plain unencrypted connection. Confirmed live: PING, SET/GET round-trip, and explicit `connection_class` introspection all passed against the real Upstash instance.
- `backend/app/core/celery_app.py` — `celery_app.conf.timezone = "Asia/Kolkata"`. Verified against Celery's own `schedules.py` source that crontab's `now()` resolves through `app.timezone`, so `crontab(hour=6, minute=0)` genuinely fires at 06:00 IST wall-clock, not 06:00 UTC — no manual UTC-offset math needed in the schedule itself.
- **Job 1 — proactive grace downgrade** (`app/tasks/grace_period_tasks.py`, hourly): reuses `SubscriptionService.reconcile_expired_grace()` as-is — no state-machine logic duplicated. New `SubscriptionRepository.list_grace_eligible()` narrows the scan to `status IN ('past_due', 'grace')` rather than every subscription row. Not wired to any notification (Day 0/3/6 grace emails, BRD §10) — FR-NOT-* doesn't exist yet in this project.
- **Job 2 — daily 06:00 IST harvest scan** (`app/tasks/harvest_tasks.py`, FR-HAR-03): discovered `harvest_runs` / `harvest_recommendation_lines` tables already existed in `db/schema.sql` (BRD §14's data model) and were already deployed live on Supabase, but nothing in app code had ever touched them — `HarvestingService` was, and remains, pure compute-on-demand with no persistence. Built `app/models/harvest_run.py`, `harvest_recommendation_line.py`, `app/repositories/harvest_run_repository.py`, and `app/services/harvest_cache_service.py` (`HarvestCacheService`) to read/write those existing tables — no migration needed, the schema was already there.
  - `harvest_recommendation_lines` deliberately doesn't duplicate symbol/buy_price/buy_date — those are read back through the `holding_lot_id` FK at query time. `current_value` is reconstructed by exact arithmetic (`buy_price * qty + stored simulated_stcg_ltcg`), not a fresh live-price fetch, so a cache hit costs zero calls to `PriceService`. `is_price_estimate` is always `False` for a persisted row by construction: `HarvestingService` only ever includes a lot when `unrealized_loss < 0`, and its own cost-basis fallback can never itself produce a loss.
  - Tier-aware in `app/api/v1/harvesting.py`: Free tier is untouched, still calls `HarvestingService` directly, always live, never caches (FR-HAR-03: "Free on-demand only"). Pro/Premium reads through `HarvestCacheService`, which serves a completed run created since the most recent 06:00 IST boundary, or computes live and persists on a cache miss (first-ever call before the daily job has run, or a prior failed run) — so the 60s-polling requirement in FR-HAR-03 doesn't re-run a full FIFO+live-price scan every poll.
  - "Portfolio-change" as a third refresh trigger (also named in FR-HAR-03, alongside the daily job and 60s polling) was NOT built this phase — only the scheduled daily scan and the cache-miss fallback exist as refresh paths.
- `requirements.txt` gained `celery==5.6.3`, `redis==8.0.1`, and their transitive dependencies.
- **Not started**: no `celery worker` / `celery beat` process has been run — deliberately left for the user to test separately before it goes anywhere near production. All verification so far calls the service layer directly (`HarvestCacheService`, `SubscriptionService`) against the real DB using the project's documented test user, never the actual `@celery_app.task`-decorated functions — those iterate every matching row in the database, not a single scoped case, so they're intentionally excluded from this project's testing process now.

## Google OAuth Sign-In
- `frontend/app/auth/callback/route.ts` added — exchanges the PKCE `code` for a session via the server Supabase client, redirects to `/dashboard` on success. Handles provider failure via the `?error=<code>` query param GoTrue forwards on this redirect (not a guessed param name — this is GoTrue's documented server-side redirect behavior): `access_denied` when the user cancels on Google's consent screen (Google returns this per RFC 6749), `oauth_failed` for anything else (missing/malformed code, exchange throws, expired code).
- `frontend/app/login/page.tsx` — Google button's `redirectTo` now points at `/auth/callback` (was `/dashboard`, which skipped the code exchange entirely and never set a session cookie). Reads `?error=` on mount, shows "Sign-in was canceled." for `access_denied` or a generic retry message otherwise through the existing `role="alert"` error slot, then strips the param via `router.replace` so a refresh doesn't re-show a stale error.
- Bug found and fixed while building this: `frontend/proxy.ts` didn't allowlist `/auth/callback` as a public route, so the OAuth provider's unauthenticated redirect (carrying `code`/`error`) got bounced straight to `/login` before the route handler could ever run — added to the public-route list alongside `/`, `/pricing`, `/about`, `/login`.
- `NEXT_PUBLIC_GOOGLE_LOGIN_ENABLED=true` set in `frontend/.env.local`.
- Tested live end-to-end: button → Google consent → callback → session cookie set → `/dashboard`, and the cancel path → `/login` showing "Sign-in was canceled."

## Architecture Rules
- Always run `npm run dev` from the main repo folder (`frontend/`), never a `.claude\worktrees\*` folder — those are temporary per-task checkouts and don't persist.
- Never execute a Celery `@celery_app.task`-decorated function during testing/verification, even by calling it directly in-process (no broker/worker needed to do this, which makes it easy to do by accident) — those functions iterate every matching row in the real database, not a scoped test case. Test the underlying service/business logic directly instead (e.g. call `HarvestCacheService`/`SubscriptionService` methods against one known test user), the same way the connection and cache-hit/miss behavior were verified in Phase 12b.
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
