# FinVigil AI Backend Architecture

This document defines the highly decoupled, production-grade backend architecture for FinVigil AI. It embeds domain-driven design, CQRS, strict idempotency, rate-limiting, and deep tenant isolation (demo vs. production).

---

## 1. Production Folder Structure (Domain-Driven & CQRS)

```text
finvigil_backend/
├── app/
│   ├── core/                   # Cross-cutting concerns
│   │   ├── security/           # KMS, AES-GCM 256 for Broker API Keys
│   │   ├── idempotency.py      # 🔥 Idempotency Keys (Redis-backed duplicate prevention)
│   │   ├── rate_limiter.py     # 🔥 Rate Limiting (Token-bucket per Tier & Heavy Ops)
│   │   ├── observability.py    # OpenTelemetry configuration (Tracing, Metrics)
│   │   └── logging.py          # Structured JSON logging
│   │
│   ├── api/                    # HTTP protocol layer (FastAPI routers & Gating)
│   │   └── dependencies.py     # Injects DemovsProd Context, Auth, Rate Limits
│   │
│   ├── application/            # (USE CASES - Application Layer Boundary)
│   │   └── use_cases/          # Orchestrators (RunHarvestUseCase, ReconcileAisUseCase)
│   │
│   ├── domain/                 # PURE LOGIC (Domain Core)
│   │   ├── engines/            # Pure Math (HarvestEngine, ReplaySimulator)
│   │   ├── rules/              # Tax Set-Off logic, FIFO sorting
│   │   └── entities/           # Abstract shapes (AbstractTrade, SimulationVector)
│   │
│   ├── services/               # Infrastructure orchestration 
│   │
│   ├── transformers/           # NORMALIZATION (Anti-Corruption Layer)
│   │
│   ├── repositories/           # Write Models (Heavy mutations to Supabase Postgres)
│   │   ├── postgres_impl/      # Real DB writes
│   │   └── memory_impl/        # 🔥 Demo Mode Isolation (Ephemeral storage)
│   │
│   ├── projections/            # READ MODELS (Optimized tables/views for Dashboards)
│   │
│   ├── events/                 # EVENT SYSTEM (Pub/Sub via Redis/RabbitMQ)
│   │   ├── publishers.py
│   │   └── subscribers.py
│   │
│   ├── integrations/           # Outbound Adapters (Broker REST clients, Groq API)
│   │
│   └── worker/                 # Celery Async Queues & Job routing
```

---

## 2. Strict Layer Boundaries & Request Flow

- **API Layer (`api/`)**: Gating heavily guarded by tier entitlement, rate quotas, and Auth.
- **Application Layer (`use_cases/`)**: Dictates exactly *what* needs to happen (e.g. `RunHarvestUseCase` injects Repo, injects Pure Domain Math, saves result).
- **Domain Layer (`domain/`)**: Dictates *how* computation happens without any knowledge of external dependencies or APIs.
- **Data Source Abstraction**: `ReplaySimulator` accepts an agnostic `AbstractMarketData` interface so Yahoo Finance vs. NSE files are interchangeable.

---

## 3. Idempotency Layer (Gap 1)

Because distributed systems retry failed events, executing "Broker Sync" twice could result in catastrophic phantom trades.
- **API Idempotency**: All mutation APIs require an `Idempotency-Key` header. Redis caches processed request keys.
- **Event Bus Idempotency**: The `EventSubscriber` extracts deterministic hashes explicitly from message bodies (e.g. `hash(broker_txn_id + user_id)`). If this hash already sits in Redis, the event listener silently ACKS and drops the message.
- **Repository Upserts**: The Postgres `repositories` enforce strict uniqueness on `broker_trade_id`, acting as the final safety net converting blind `INSERT` calls into safe `ON CONFLICT DO UPDATE` commands.

---

## 4. Rate Limiting at Domain Entry (Gap 2)

We actively guard the heavy `Domain` (like 1,000-path Monte Carlos and Harvest simulations) from DDoS or tier-abuse.
- **Policy Enforcement**: `app/core/rate_limiter.py` enforces quota algorithms directly at FastAPI `Depends()` checkpoints.
- **Heavy Ops Guarding**: BRD states `5 heavy ops / user / hour`. 
  - When a REST call enters, it is intercepted. 
  - Token-bucket in Redis verifies the user's tier and remaining heavy operations. 
  - If a user triggers a 6th Monte Carlo path, it immediately returns `429 Too Many Requests` *before* instantiating any `Application/Domain` logic.

---

## 5. Cold Start & Demo Mode Isolation (Gap 3)

Demo users require immediate mock functionality (<90s) without persisting phantom data to Postgres or triggering compliance footprints.
- **Ephemeral Context Boundary**: When `/demo_start` is clicked, no user record is created in Supabase. Instead, the API sets a `demo_uid` cookie.
- **In-Memory Repositories**: The Dependency Injector spots the Demo context. It injects `MemoryHoldingRepository` and `MemoryTradeRepository` instead of `PostgresHoldingRepository`.
- **Instant Garbage Collection**: On refresh or expiration (TTL 10m), the Redis/Memory data drops into the void permanently keeping zero trace in real projections or databases.

---

## 6. CQRS: Read Models vs. Write Models 

- **Write Models (`repositories/`)**: Complex normalization and ingestion loops handling thousands of trades append to `HoldingLot`. 
- **Read Models (`projections/`)**: Instead of running heavy groupings to sum P&L on demand, events push calculated aggregates to `DashboardProjection` views. The `/view` API queries these projections keeping latency millisecond fast.

---

## 7. Event Bus & Fault Tolerance 

- **Event Topology**: Decoupled async triggers via RabbitMQ/Redis targeting explicit routing lines (`broker.sync.completed`).
- **Resiliency Engine**: `HarvestEngine` compute failures route to an exponential backoff **Retry Queue**. Repeated failures land in a **Dead Letter Queue (DLQ)**.

### Event-Driven Data Flow
```text
Broker API
   ↓
Integration Adapter
   ↓
Transformer (Normalization)
   ↓
Repository (Write DB)
   ↓
Event: BROKER_SYNC_COMPLETED (Checked vs. Idempotency Key)
   ↓
Use Case: Run Harvest (Checked vs. Heavy Ops Limit)
   ↓
Domain Engine (Pure Logic - Tax Math)
   ↓
Repository (Save Results)
   ↓
Projection (Read Model Updated for Dashboard)
   ↓
API Response / Notification
```

---

## 8. Versioning Strategy & AY Pinning

- **Temporal Immutability**: AIS updates insert discrete new entity versions (`AisUpload version=v1`). Previous data sets stay immutable.
- **Assessment Year Pinning**: The query framework layers an Assessment Year (`AY`) hard context. Operations hitting past locked AY dates throw out-of-bound errors.

---

## 9. Observability & Monitoring

- **Distributed Tracing**: OpenTelemetry (`TraceID`) injects into initial requests, streaming through Python Context Vars all the way heavily down to Celery events.
- **Structured JSON Logging**: Guaranteed standardized outputs (e.g. `{"event": "harvest_failed", "trace_id": "123", "broker": "zerodha"}`).
- **Key SLIs**: Track ingestion latency, Queue Depths, Idempotency drops, DLQ triggers, and End-to-End `<90s onboarding` success rate directly pushed to a Prometheus metrics sink.
