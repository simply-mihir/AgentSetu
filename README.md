# AgentSetu ⚡

> The authorization and interoperability layer for agentic commerce.
> **Merchant manifests · AI buyer · bounded payment · audit**

Built for Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce.

---

## What it does

AgentSetu makes Razorpay merchants **machine-readable**, **discoverable**, **policy-aware**, and **safely transactable by AI agents** — without giving the agent unrestricted spending authority.

| Component | Responsibility |
|-----------|---------------|
| **ARM** (Agent-Readable Manifest) | Machine-readable merchant manifest: products, policies, payment endpoints |
| **AI Buyer Orchestrator** | Natural-language → structured constraints → ranked candidates → explanation |
| **Policy Engine** | Deterministic authorization: spend caps, approval gates, category restrictions |
| **Razorpay Adapter** | Test-mode Payment Links: create, verify, status, idempotent |
| **Audit Service** | Append-only event trail: every material agent and money action |

**Architecture principle:** _The LLM reasons; policy code decides. The agent may propose; deterministic code must approve._

---

## Quick Start

### 1. Clone & setup

```bash
cd agentsetu
cp services/api/.env.example services/api/.env
# Edit .env with your Razorpay test keys and OpenAI key
```

### 2. Add your API keys

Edit `services/api/.env`:
```env
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret
OPENAI_API_KEY=sk-your-key
```

Get Razorpay test keys: https://dashboard.razorpay.com/app/keys

### 3. Start everything

```bash
./start.sh
```

Or manually:

```bash
# Backend
cd services/api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd apps/web
npm install
npm run dev
```

### 4. Open the app

- **Buyer UI**: http://localhost:3000/buyer
- **Merchant Console**: http://localhost:3000/merchant
- **Audit Center**: http://localhost:3000/audit
- **API Docs**: http://localhost:8000/docs

---

## Demo Scenarios

### A. Happy Path — Honey under ₹500

```
Type: "Buy organic honey under ₹500, deliver in 2 days"
```
→ AI extracts constraints → discovers OrganicKart → ranks candidates → policy ALLOWS → Razorpay link created

### B. Boundary — Approval Required

```
Type: "Buy desi cow ghee under ₹700"
```
→ ₹699 > OrganicKart's ₹500 auto-limit → NEEDS_APPROVAL → buyer approves → payment created

### C. Graceful Failure

→ Trigger via a failed/expired Razorpay link → system marks PAYMENT_UNKNOWN → recovery proposed → no duplicate retry

### Reset Demo

```bash
cd services/api
rm -f agentsetu.db
uvicorn main:app --reload  # Re-seeds automatically
```

---

## Project Structure

```
agentsetu/
├─ services/api/          # FastAPI backend
│  ├─ main.py             # App entry point + auto-seed
│  ├─ config.py           # Settings (env vars)
│  ├─ models/             # SQLModel DB models
│  ├─ arm/                # ARM generator + schema
│  ├─ policy/             # Deterministic policy engine
│  ├─ payments/           # Razorpay adapter
│  ├─ ai/                 # OpenAI buyer orchestrator
│  ├─ audit/              # Append-only audit service
│  ├─ routes/             # FastAPI route handlers
│  └─ data/               # Seed merchants JSON
│
├─ apps/web/              # Next.js 14 frontend
│  ├─ app/buyer/          # Buyer chat + approval + receipt
│  ├─ app/merchant/       # Catalog import + policy controls
│  ├─ app/audit/          # Transaction timeline viewer
│  ├─ components/         # Reusable UI components
│  └─ lib/api.ts          # Typed API client
│
├─ start.sh               # One-command startup
└─ README.md
```

---

## API Reference

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/v1/auth/signup` | — | Create account |
| POST | `/v1/auth/login` | — | Login, get JWT |
| POST | `/v1/auth/logout` | ✅ | Revoke current token |
| GET | `/v1/auth/me` | ✅ | Current user info |
| POST | `/v1/merchants/import` | ✅ | Import catalog + generate ARM |
| GET | `/v1/merchants/` | — | List merchants (public) |
| GET | `/v1/merchants/{id}` | — | Merchant detail (public) |
| GET | `/v1/merchants/{id}/arm` | — | Get ARM manifest |
| PUT | `/v1/merchants/{id}/policy` | ✅ | Update agent spend policy |
| GET | `/v1/discover/` | — | Search by category/price/delivery |
| POST | `/v1/transactions/intent` | opt | Process buyer intent (full pipeline) |
| POST | `/v1/transactions/select` | opt | Select product from candidates |
| POST | `/v1/transactions/approve` | ✅ | Record buyer consent |
| GET | `/v1/transactions/{id}` | ✅ | Transaction detail |
| GET | `/v1/transactions/` | ✅ | List transactions (tenant-scoped) |
| POST | `/v1/payments/payment-link` | ✅ | Create Razorpay Payment Link |
| POST | `/v1/payments/verify/{id}` | ✅ | Verify payment status |
| GET | `/v1/payments/receipt/{id}` | ✅ | Machine-readable receipt (v1.0) |
| POST | `/v1/payments/cancel/{id}` | ✅ | Cancel unpaid payment link |
| GET | `/v1/audit/` | ✅ | List audit events (tenant-scoped) |
| GET | `/v1/audit/{correlation_id}` | ✅ | Full transaction timeline |
| POST | `/v1/webhooks/razorpay` | HMAC | Razorpay webhook handler |

---

## ARM Schema (v0.2)

```json
{
  "schema_version": "arm-0.2",
  "manifest_id": "arm_a1b2c3d4e5f6",
  "generated_at": "2026-09-01T12:00:00Z",
  "manifest_hash": "sha256:...",
  "merchant": { "id": "organickart-01", "name": "OrganicKart", "currency": "INR" },
  "products": [{
    "product_id": "ok-honey-500",
    "name": "Organic Raw Honey 500g",
    "price_inr": 449,
    "availability": true,
    "delivery_sla_days": [1, 2],
    "category": "grocery"
  }],
  "policies": {
    "max_autonomous_spend_inr": 500,
    "approval_required_above_inr": 500,
    "restricted_categories": [],
    "refund_authority": "human_only"
  }
}
```

Note: No payment credentials in the manifest. Payment is handled server-side only.

---

## Scoring Model

```
score = 0.45 × price_score + 0.25 × delivery_score + 0.20 × rating_score + 0.10 × policy_fit
```

All scoring is deterministic and exposed to the buyer. The LLM generates the explanation text; it does not compute the ranking.

---

## Safety Guarantees

- ✅ **No payment without policy pass** — policy engine is the gatekeeper
- ✅ **No silent retry** — unknown payment state is held, not retried
- ✅ **Idempotent payment creation** — fingerprint prevents duplicate links
- ✅ **Append-only audit** — every material action is immutably recorded
- ✅ **LLM cannot override limits** — all financial decisions are deterministic
- ✅ **Secrets server-side only** — never exposed to browser or ARM

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + Python 3.12 |
| AI | OpenAI structured outputs (gpt-4o-mini) |
| Database | SQLite (dev) / PostgreSQL (prod) + SQLModel + Alembic |
| Auth | JWT (HS256) + argon2 passwords + JTI revocation |
| Payments | Razorpay Payment Links (test/live) |
| Frontend | Next.js 14 + TypeScript + Tailwind |
| Animation | Framer Motion |
| Deploy | Docker + docker-compose (PostgreSQL + Redis + API) |

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, transaction flow, state machine, data models |
| [SECURITY.md](docs/SECURITY.md) | Threat model, mitigations, auth, payment safety |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Setup, testing, conventions, environment variables |
| [MANUAL_SETUP_CHECKLIST.md](docs/MANUAL_SETUP_CHECKLIST.md) | External dependencies checklist for production |
| [PRODUCTION_IMPLEMENTATION_STATUS.md](docs/PRODUCTION_IMPLEMENTATION_STATUS.md) | Phase-by-phase implementation status |
