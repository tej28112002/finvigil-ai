# FinVigil AI BRD

**India-only portfolio intelligence SaaS**: Consolidate, Replay, Journal, Harvest.
**Read-only integrations**. Deterministic tax/harvest engine first; AI layers second.
**Classification**: Internal / Confidential — for engineering, CA validation, and legal review.

## 1. Document Control

| Field | Value |
| :--- | :--- |
| **Product name** | FinVigil AI (Vigil AI) |
| **BRD version** | 1.0 (locked) |
| **Primary market** | India — retail traders & investors |
| **Assessment Year (MVP default)** | AY 2026–27 / FY 2025–26 |
| **CBDT alignment** | Official ITR-3 / ITR-4 JSON schema (pin utility build in Appendix A) |
| **Stack (reference)** | Next.js 15, FastAPI, PostgreSQL (Supabase), Railway, Celery + Redis |
| **Data residency** | Supabase ap-south-1 (Mumbai) — mandatory MVP |

## 2. Executive Summary

FinVigil AI is an AI-powered portfolio intelligence platform for Indian retail traders. It consolidates multi-broker holdings and AIS data, supports portfolio replay with Monte Carlo simulations, journals trades with voice logging and psychology flags, and surfaces tax-loss harvesting opportunities with exact sell simulations — all read-only with no trade execution.

Target users are active Indian traders (25–45) burdened by Excel workflows, missed tax savings, and lack of structured review. Four modules drive value: Multi-platform Consolidate → Portfolio Replay → Trading Journal / coach → Tax Harvest.

## 3. Personas

- **#1 Tax-anxious salaried trader (~60%)**
  - Ages 28–40, Tier-1/2.
  - Core Focus: AIS reconciliation + ITR JSON + Harvest.
- **#2 F&O speculator / active trader**
  - Core Focus: Journal + Replay; discipline and win-rate focus.
- **#3 Hybrid portfolio builder**
  - Core Focus: Replay + Consolidate; scenario planning across equity, MF, crypto.

## 4. Goals & Success Metrics

| Metric | Target (MVP) |
| :--- | :--- |
| **Paying Pro users** *(4 mo post closed beta)* | 100 |
| **Free → paid conversion** | ≥ 10% |
| **AIS auto-match** *(test corpus)* | ≥ 95% |
| **Harvest / harvest simulation accuracy** | ≥ 95% (CA-validated sample) |
| **Time-to-first-value** | < 90 seconds |
| **Weekly Journal or Replay usage** | ≥ 40% active users |
| **Beta NPS** | ≥ 8/10 |

## 5. Scope

### 5.1 In scope (v1)
- **India only**: NSE/BSE, Indian brokers, AIS, ITR-3/4 JSON export assistance.
- **Read-only**: Zerodha Kite Connect, Groww Trade API, Upstox; WazirX + CoinDCX + CSV.
- **F&O**: in scope across Consolidate, Journal, Replay, Harvest.
- **Demo mode**: one-click sample portfolio; no login; reset on refresh.

### 5.2 Out of scope (v1 guardrails)
- No trade execution, custody, or lending.
- No personalized investment advice; simulations + disclaimers only.
- Not a tax preparer/filer — exports + User/CA input fields only.
- No long-term raw voice storage (delete after transcription).
- No US/EU tax; crypto limited to Indian exchanges in MVP.

## 6. Regulatory, Disclaimers & Privacy

- **Heavy disclaimers**: “Not financial advice — consult your CA.”
- **DPDP Compliance**: Mumbai region data residency; MFA for Pro/Premium; JWT + refresh.
- **Voice Privacy**: Delete raw audio within <5s of successful transcription; retain transcript + tags.
- **Privacy policy string (locked)**: *Raw voice recordings deleted immediately after transcription. Only text transcript retained. User may delete any journal entry at any time.*
- **WhatsApp (Twilio)**: Opt-in requirement; India DLT compliance.
- **Tax persona default**: Non-speculative business income (PGBP) — ITR-3; user may override once per AY.

## 7. User Journey

- **Figure 1** — Primary journey (happy path)
- **Figure 2** — Onboarding & time-to-first-value (<90s)
  - **Step 1 (~15s)**: Supabase email/password or Google OAuth.
  - **Step 2 (30–45s)**: broker OAuth or WazirX/CoinDCX API keys plus optional AIS upload.
  - **Step 3**: consolidated dashboard with holdings, AIS mismatch count, and Harvest banner.

## 8. Functional Requirements

### 8.1 Platform (FR-PLT-*)
- **FR-PLT-01**: Supabase auth — email/password + Google OAuth.
- **FR-PLT-02**: Demo mode — seeded data; rate limit 20 req/5 min per IP.
- **FR-PLT-03**: Tax Persona global setting + one override per AY.
- **FR-PLT-04**: MFA required Pro/Premium (TOTP); optional Free; nudge before first Harvest/AIS export.
- **FR-PLT-05**: Short-lived access + refresh tokens.
- **FR-PLT-06**: Data residency ap-south-1.

### 8.2 Consolidate (FR-CON-*)
- **FR-CON-01**: Unified dashboard — equity + F&O + MF + crypto.
- **FR-CON-02**: Equity/F&O fields: symbol, ISIN, qty, FIFO lots, avg buy, live price, unrealized/realized P&L, charges, STCG/LTCG flag.
- **FR-CON-03**: MF: folio, units, avg NAV, P&L.
- **FR-CON-04**: VDA: FIFO cost; 30%+cess display; TDS Credits ledger.
- **FR-CON-05**: WebSocket or polling per connector.
- **FR-CON-06**: Corporate actions — manual confirm/apply only (v1).

### 8.3 AIS (FR-AIS-*)
- **FR-AIS-01**: Upload JSON → CSV → PDF (OCR last).
- **FR-AIS-02**: Multiple versions per AY; Latest flag; history + match %; overwrite confirm.
- **FR-AIS-03**: Auto-match + mismatch types (missing, qty, price, duplicate, TDS).
- **FR-AIS-04**: Resolution grid + bulk exact-match + mismatch export.
- **FR-AIS-05**: ITR JSON generation with User/CA input form pre-export.

### 8.4 Harvest (FR-HAR-*)
- **FR-HAR-01**: FIFO; equity STCG/LTCG + exemption; VDA 30%+cess; set-off per persona.
- **FR-HAR-02**: Outputs — tax saved estimate, sell list, post-harvest sim, warnings.
- **FR-HAR-03**: Free on-demand only; Pro/Premium — 06:00 IST Celery job + portfolio-change + 60s polling on Harvest page.
- **FR-HAR-04**: Deep link “Simulate in Replay.”

### 8.5 Replay (FR-REP-*)
- **FR-REP-01**: User history + Nifty/Bank Nifty + drag-drop what-if.
- **FR-REP-02**: Price stack — broker → NSE CSV / free API → user CSV.
- **FR-REP-03**: Monte Carlo 1000 paths + inflation (CPI).
- **FR-REP-04**: Monte Carlo entitlement — Pro+.

### 8.6 Journal (FR-JRN-*)
- **FR-JRN-01**: MediaRecorder → Whisper/Groq → delete audio <5s.
- **FR-JRN-02**: Fixed psychology taxonomy; no buy/sell advice.
- **FR-JRN-03**: User-delete cascades transcript + tags.

### 8.7 Notifications (FR-NOT-*)
- **FR-NOT-01**: In-app + Resend email + Twilio WhatsApp (opt-in).
- **FR-NOT-02**: Harvest, AIS mismatch, journal streak, Sunday report, drawdown alert.

### 8.8 CA Export & Share (FR-CA-*)
- **FR-CA-01**: ZIP — ITR JSON + CSV lots/trades + PDF + notes + Harvest/Replay exports.
- **FR-CA-02**: Tokenized read-only link — TTL 7/30/90 days, optional password.

### 8.9 Admin (FR-ADM-*)
- **FR-ADM-01**: Feature flags per user/module.
- **FR-ADM-02**: Impersonation read-only + broker re-sync only; full audit; user notified.
- **FR-ADM-03**: DPDP data export on request.

## 9. ITR Export Logic

Infer recommended form from Tax Persona (default ITR-3). Before final export, display confirmation modal with dropdown (ITR-3 | ITR-4) and eligibility tooltip. Warn if ITR-4 chosen but capital gains or F&O are outside presumptive limits. Exported JSON strictly follows official CBDT schema for chosen form (pin version Appendix A).

## 10. Subscription & Billing

| Tier | plan_id | Monthly | Annual |
| :--- | :--- | :--- | :--- |
| **Free** | plan_free | ₹0 | — |
| **Pro** | plan_pro_monthly | ₹299 | — |
| **Pro** | plan_pro_annual | — | ₹2,499 (~42% off) |
| **Premium** | plan_premium_monthly | ₹799 | — |
| **Premium** | plan_premium_annual | — | ₹6,999 (~27% off) |

Server enforces entitlements on every protected API (FastAPI + RLS). Webhooks update `subscription.status` + `plan_id`.

### Failed Payment & Grace
- Razorpay pending + Smart Retry (immediate, +3d, +7d).
- **Grace**: 7 full days from first failed charge — full Pro/Premium access.
- **After day 7**: downgrade to Free.
- **Post-downgrade**: read-only dashboard + historical view + one-time CA bundle (JSON+PDF) for current AY (once per lapse cycle).
- **Blocked**: new Harvest, new AIS, Monte Carlo, voice journal, new connections beyond Free, daily alerts.
- **Notify**: Day 0, 3, 6 — in-app + email + WhatsApp with payment update deep link.

### Proration (Razorpay)
Plan changes immediate; proration auto; min adjustment ₹0.50; UI shows ₹X today and savings.

### Tier Limits (Brokers / Lookback)
| Tier | Brokers + Crypto | Lookback |
| :--- | :--- | :--- |
| **Free** | 2 + 1 | Current FY only |
| **Pro** | 5 + 3 | Lifetime |
| **Premium** | Unlimited | Lifetime + multi-AY (3–5 AYs) |

## 11. AY Pinning

- **MVP/Pro**: single current AY (2026–27 / FY 2025–26) for all modules. User may upload historical AIS/CSV files solely to reconcile against the current AY dataset (no multi-AY navigation on Pro).
- **Premium**: multi-AY switcher (last 3–5 AYs), full historical lot exposure, multi-year Harvest, bulk ITR exports.

## 12. Rate Limits & Operations

**Heavy ops**: AIS upload+reconcile, Harvest scan (user-initiated), Monte Carlo 1k.
- **Option A (MVP)**: 5 heavy ops / user / hour (all tiers). Free additionally max 10 heavy ops / rolling 24h.
- Scheduled Pro/Premium daily Harvest + debounced post-sync harvest excluded from user heavy-op quota.

| Context | Limit |
| :--- | :--- |
| **Demo (per IP)** | 20 req / 5 min |
| **Public unauthenticated** | 60 req / min per IP |
| **Authenticated Free** | 300 req / 15 min per user |
| **Pro / Premium** | 1,200 req / 15 min per user |

## 13. Performance Constraints

*(Price staleness SLO)*
- **Market hours (09:15–15:30 IST)**: quotes ≤ 60s stale; WS preferred else poll ≤ 30s.
- **Outside hours**: ≤ 2 min stale; last close + after-hours if available.
- UI badge + banner + Refresh if threshold exceeded.

## 14. Data Model (Entities Overview)

*Logical model for PostgreSQL (Supabase).*
**(Figure 3 — Entity relationship diagram)**
*Editable Mermaid sources live under `scripts/diagrams/sources/fig03-erd.mmd` in the repository.*

**Key entities**:
`User`, `UserTaxPersona`, `Subscription`, `BrokerConnection`, `Instrument`, `Trade`, `HoldingLot`, `Charge`, `TdsCreditLedger`, `CorporateActionAdjustment`, `AisUpload`, `AisLine`, `AisMatchResult`, `HarvestRun`, `HarvestRecommendationLine`, `ReplayScenario`, `ReplayRun`, `JournalEntry`, `JournalTag`, `CaShareToken`, `CaExportJob`, `NotificationPreference`, `AdminAuditLog`.

## 15. Integration Matrix

| System | Purpose | Auth Mechanism | Notes |
| :--- | :--- | :--- | :--- |
| **Supabase** | Auth, DB, RLS, MFA | OAuth / email | |
| **Zerodha Kite** | Holdings, orders, F&O | OAuth2 | |
| **Groww** | Portfolio read | API/TBD | Per Groww docs |
| **Upstox** | Read-only portfolio | OAuth2 | |
| **WazirX / CoinDCX** | Crypto | API key | |
| **CSV** | Fallback Upload | User upload | |
| **AIS (portal file)** | Reconciliation | User upload | |
| **Razorpay** | Billing | Webhooks | |
| **Resend** | Email | API key | |
| **Twilio WA** | Alerts | Templates | |
| **Groq / OpenAI** | STT + LLM | API keys | |
| **Celery + Redis** | Jobs | Internal | |
| **NSE/Yahoo/Twelve Data**| EOD / indices | Varies | |

## 16. Backend Flows

1. Signup/login + MFA gate by tier.
2. Broker OAuth + `initial_full_sync` Celery.
3. Incremental sync + quote cache + WS/poll.
4. AIS upload → parse → version → match engine.
5. AIS resolution → ITR export readiness.
6. Harvest on-demand / scheduled / on-change (debounced).
7. Replay backtest + Monte Carlo + provenance.
8. Journal voice pipeline → delete audio → tag.
9. ITR JSON + PDF + CSV audit.
10. CA ZIP + share token viewer.
11. Notifications outbox.
12. Razorpay webhook → entitlements.
13. Admin impersonation + audit + user notify.

*(Architecture schema corresponds to Figure 9 — Backend / integration overview)*

## 17. UI Wireframes (Optional Section)

Screen-level layouts as structured block diagrams. Features correspond to sources: `scripts/diagrams/sources/fig04–fig08`.
- **17.1** Dashboard (Consolidate) — Figure 4
- **17.2** Harvest results — Figure 5
- **17.3** AIS reconciliation — Figure 6
- **17.4** Replay builder — Figure 7
- **17.5** Journal entry — Figure 8

## 18. Appendix

**(Schema & compliance pins)**
- Pin CBDT JSON schema version + ITR utility build date for AY 2026–27.
- Pin Razorpay dashboard settings: proration, credit vs refund on downgrade.
- CA validation: first 10 ITR JSON exports.
- Legal: SEBI non-advisory copy pack + DPDP privacy policy + subprocessor list.

## 19. Revision History

| Version | Date | Notes |
| :--- | :--- | :--- |
| **1.0** | 2026-04-24 | BRD locked from client discovery sessions |
