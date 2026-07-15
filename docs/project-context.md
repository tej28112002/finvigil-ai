# FinVigil AI — Project Status

## Completed Phases (34/45 — 76%)
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

## Remaining Phases (11/45 — 24%)
Phase 10   Voice Journal Pipeline
Phase 12b  Celery + Redis (no scheduled jobs exist yet — grace-period downgrade is lazy/read-triggered via GET /billing/subscription, not proactive; also blocks FR-HAR-03's daily 06:00 IST harvest job)
Phase 14   Admin Panel (role-based access — is_admin guard now on /admin/itr-schemas WRITE endpoints only; full RBAC/impersonation/feature-flags still unbuilt)
Phase 15   Testing + CA Validation
Phase 16   Closed Beta
Phase 17   Production Launch

## Known Billing Limitations (Phase 12a)
- No razorpay_subscription_id column on `subscriptions` — webhook events are correlated to a FinVigil user via `notes.finvigil_user_id` set at subscription creation, not a stored Razorpay ID. Cancel-subscription only updates FinVigil's local row; does NOT call Razorpay's cancel API (nothing to call it with) — a real paid subscription keeps being charged by Razorpay until also canceled in their dashboard.
- POST /billing/create-subscription and the webhook flow are untested against real Razorpay (no test-mode credentials exist yet — see backend/.env TODOs). Signature verification and the full webhook state-machine ARE tested locally (self-signed HMAC payloads).
- RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET / RAZORPAY_WEBHOOK_SECRET / RAZORPAY_PLAN_* are empty placeholders in backend/.env.

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
