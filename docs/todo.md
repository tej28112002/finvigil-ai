# FinVigil AI — TODO List

## About Page — Pending Improvements
- [ ] Problem story section
- [ ] How it works 4-step visual flow
- [ ] Supported brokers section
- [ ] Founder section (Tejas)
- [ ] Trust and security signals
- [ ] FAQ section
- [ ] Contact section (support@finvigil.in)
- [ ] Numbers and social proof (after beta)
- [ ] Press section (after coverage)

## Billing
- [ ] Test webhook with Razorpay dashboard (verified via manually-signed HMAC requests against a live server instead — real signature verification + full event state machine tested; the actual Razorpay dashboard test-event sender UI itself hasn't been used)
- [x] Add GROQ_API_KEY to .env for Voice Journal (done — verified with a real synthesized-speech transcription, exact word-for-word match)

## Phase 14 — Admin Panel roles
- [x] Full role-based access control (user/support/admin on user_tax_personas.role)
- [x] Feature flags (global default + per-user override, both verified against real DB)
- [x] User management (list, detail, role toggle)

## Phase 15 — Testing
- [ ] Unit tests for FIFO engine
- [ ] Unit tests for tax engine
- [ ] CA validation of calculations
- [ ] Security audit

## Phase 16 — Beta
- [ ] Invite system
- [ ] Feedback widget
- [ ] Error monitoring (Sentry)

## Phase 17 — Launch
- [ ] Production hosting
- [ ] Custom domain
- [ ] Privacy policy
- [ ] Terms of service
