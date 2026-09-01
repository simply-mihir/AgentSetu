# AgentSetu — Production Implementation Status

**Baseline checkpoint:** `c87dba4` on `main` (2026-09-01)  
**Baseline tests:** 41/41 passing  
**Current tests:** 59/59 passing  
**Frontend build:** clean  

---

## Phase 0 — Safety Checkpoint ✅
- [x] Git status verified
- [x] Branch: main, commit: c87dba4
- [x] 41/41 tests passing
- [x] Frontend typecheck clean
- [x] Frontend build succeeds
- [x] Checkpoint commit created

## Phase 1 — Critical Security Fixes ✅
- [x] C1: Transaction routes require auth + tenant filtering
- [x] C2: Payment routes require auth
- [x] C3: Merchant import requires auth
- [x] C4: Audit routes require auth + tenant filtering
- [x] C5: Remove client-controlled buyer_limit_inr (backend + frontend)
- [x] C6: Frontend auth flow (login/signup page, JWT token, 401 interceptor, AuthProvider, logout)
- [x] H1: approved_by from auth context, not request body (backend + frontend)
- [x] H2: Merchant policy uses required auth
- [x] Tests: 53/53 passing (41 original + 12 new security tests)
- [x] Frontend build clean with auth pages

## Phase 2 — Identity / Multi-Tenancy ✅
- [x] Unique constraint: merchant_id + user_id on MerchantUser
- [x] Unique constraint: product_id + merchant_id on Product
- [x] Transaction.buyer_id FK → users.user_id
- [x] Transaction.merchant_id FK → merchants.merchant_id + index
- [x] WebhookEvent(provider, provider_event_id) unique constraint
- [x] WebhookProcessingStatus proper Enum (Phase 7 item)
- [x] Alembic migration generated (e7e53d88625f)
- [x] 6 tenant isolation tests (unique constraints, buyer scoping, cross-merchant, audit scoping)
- [x] 59/59 tests passing

## Phase 3 — Buyer Policy Engine
- [ ] BuyerProfile.daily_limit_inr enforcement
- [ ] BuyerProfile.blocked_merchants enforcement
- [ ] BuyerProfile.blocked_categories enforcement
- [ ] Dead policy branch cleanup
- [ ] Policy engine tests for all buyer profile rules

## Phase 4 — Capability Hardening
- [ ] Bind buyer_id to authenticated buyer
- [ ] Row-level locking (PostgreSQL) for consume
- [ ] Idempotent revocation
- [ ] Extended capability tests

## Phase 5 — Transaction State Machine
- [ ] Explicit transition validation
- [ ] Resolve /select state ambiguity
- [ ] Audit on every transition

## Phase 6 — Idempotency
- [ ] Full 64-char SHA-256 fingerprint
- [ ] API Idempotency-Key header support

## Phase 7 — Webhook Reliability
- [ ] WebhookProcessingStatus proper Enum
- [ ] DB unique constraint on (provider, provider_event_id)
- [ ] In-flight duplicate check (RECEIVED + PROCESSED)
- [ ] Webhook tests

## Phase 8 — Razorpay Adapter Hardening
- [ ] Live-key validation in production
- [ ] Callback URL fix
- [ ] Payment cancellation route
- [ ] OAuth architecture/interface (code-complete, credentials manual)
- [ ] Encrypted credential storage interface

## Phase 9 — ARM Protocol
- [ ] Remove payment_link_id from ARM products
- [ ] Add manifest_id, generated_at, updated_at, manifest_hash
- [ ] ARM versioning
- [ ] ARM caching improvement
- [ ] docs/ARM_SPEC.md

## Phase 10 — Discovery Performance
- [ ] DB-side filters
- [ ] Pagination (limit/offset)
- [ ] Rate limiting on discovery
- [ ] Remove sensitive policy fields from public response

## Phase 11 — Database / Migrations
- [ ] Alembic migrations for all schema changes
- [ ] Skip create_all in production
- [ ] Connection pool configuration
- [ ] Indexes on audit and webhook tables

## Phase 12 — Auth Security
- [ ] Login rate limiting
- [ ] Logout / token revocation
- [ ] Refresh token architecture
- [ ] Email verification architecture (feature-flagged)

## Phase 13 — AI Security
- [ ] Prompt injection defense
- [ ] Structured output validation
- [ ] Adversarial tests

## Phase 14 — Public API v1
- [ ] Cleaned v1 endpoint set
- [ ] OpenAPI docs
- [ ] Consistent error format
- [ ] Rate limits on all endpoints

## Phase 15 — MCP Adapter
- [ ] MCP tool definitions
- [ ] Adapter layer calling internal services
- [ ] Not started — depends on stable API

## Phase 16 — WhatsApp Adapter
- [ ] Channel-independent architecture
- [ ] WhatsApp message adapter interface
- [ ] Mock adapter for development
- [ ] Not started — credentials manual

## Phase 17 — Merchant Dashboard
- [ ] Dashboard page
- [ ] Catalog management
- [ ] ARM preview
- [ ] Policy management
- [ ] Order view
- [ ] Razorpay connection status

## Phase 18 — Buyer Dashboard
- [ ] Order history
- [ ] Receipt view
- [ ] Spending policy management
- [ ] Account settings

## Phase 19 — Audit Center
- [ ] Filters (transaction, merchant, buyer, event type, date range)
- [ ] Pagination
- [ ] RBAC enforcement in UI

## Phase 20 — Commerce Receipt
- [ ] Machine-readable JSON receipt
- [ ] Receipt version, hash, all required fields

## Phase 21 — Observability
- [ ] Structured JSON logging
- [ ] Sentry integration point (feature-flagged)
- [ ] Health/ready endpoints (already exist)

## Phase 22 — Rate Limiting
- [ ] Per-endpoint rate limits
- [ ] Redis backend support
- [ ] HTTP 429 with stable error format

## Phase 23 — Security Headers / Request Limits
- [ ] Security headers middleware
- [ ] Request body size limit
- [ ] CORS restriction by app_mode

## Phase 24 — Frontend Production Hardening
- [ ] Auth-aware API client
- [ ] 401 handling
- [ ] Loading/empty/error states
- [ ] No client-side authorization decisions

## Phase 25 — Testing
- [ ] Auth tests
- [ ] Tenancy tests
- [ ] Policy tests
- [ ] Capability tests
- [ ] Webhook tests
- [ ] Payment tests
- [ ] ARM tests
- [ ] AI tests
- [ ] Security tests
- [ ] Mock Razorpay provider

## Phase 26 — CI/CD
- [ ] Blocking lint/mypy
- [ ] pip-audit
- [ ] Docker build step
- [ ] Migration verification

## Phase 27 — Docker
- [ ] Docker build verification
- [ ] Production startup validation

## Phase 28 — Deployment Files
- [ ] .env.example
- [ ] docs/DEPLOYMENT.md update
- [ ] Health check documentation

## Phase 29 — Production Check Script
- [ ] scripts/production-check.sh
- [ ] scripts/smoke-test.sh

## Phase 30 — Manual Task Checklist
- [ ] docs/MANUAL_SETUP_CHECKLIST.md

## Phase 31 — Documentation
- [ ] README.md update
- [ ] docs/ARCHITECTURE.md
- [ ] docs/API.md
- [ ] docs/SECURITY.md
- [ ] docs/DEVELOPMENT.md

## Phase 32 — Final Validation
- [ ] All backend tests pass
- [ ] Frontend typecheck clean
- [ ] Frontend build succeeds
- [ ] Docker build succeeds
- [ ] E2E positive scenarios
- [ ] E2E negative scenarios
- [ ] Final report produced

---

## Blocked by Manual / External Action
- Razorpay live KYC + API keys
- Razorpay webhook URL registration
- Razorpay OAuth application (partner program)
- Production PostgreSQL + Redis provisioning
- OpenAI API key (production)
- Sentry DSN
- Domain / DNS / SSL
- Vercel / Railway / Render deployment
- WhatsApp / Meta business approval
- Legal pages (Privacy Policy, ToS, Refund Policy)
- Real ₹1 live transaction verification
