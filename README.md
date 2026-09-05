<div align="center">
  <h1>AgentSetu</h1>
  <p><strong>The Next-Generation Authorization and Interoperability Layer for Agentic Commerce.</strong></p>
  <p><i>Merchant Manifests · Autonomous AI Buyers · Bounded Payments · Immutable Auditing · Premium 3D Interfaces</i></p>
</div>

---

Developed for the **Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce**.

## Executive Overview

AgentSetu bridges the critical gap between artificial intelligence orchestration and secure, deterministic financial transactions. It transforms Razorpay merchants into machine-readable, discoverable, and safely transactable entities for autonomous AI agents, without granting those agents unrestricted spending authority.

| Component | Responsibility |
|-----------|---------------|
| **Agent-Readable Manifest (ARM)** | Machine-readable merchant manifest defining products, policies, and payment endpoints. |
| **AI Buyer Orchestrator** | Translates natural language into structured constraints, ranks candidates, and generates reasoning. |
| **Policy Engine** | Deterministic authorization enforcing spend caps, approval gates, and category restrictions. |
| **Razorpay Adapter** | Handles bounded, idempotent, and highly secure test-mode Payment Links. |
| **Audit Service** | Maintains an append-only event trail: every material AI and financial action is immutably recorded. |

> **Architecture Principle:** _The LLM reasons; deterministic code decides. The agent may propose; the policy must approve._

---

## Premium V3 User Interface

The frontend architecture has been meticulously engineered with a premium, glassmorphism-driven light aesthetic to provide a highly immersive user experience.

**Key Visual Innovations:**
- **Liquid Glass & Frost Aesthetics**: Advanced implementation of backdrop-blur, subtle gradients, and soft ambient lighting environments.
- **Dynamic 3D Environments**: Interactive 3D pillar elements rendered with `Three.js` and `React Three Fiber` that react dynamically to the scroll state, bringing the interface to life.
- **Scroll-Linked Depth Animations**: UI components emerge seamlessly from a glass plane utilizing advanced z-index and opacity transitions powered by `Framer Motion`.
- **The AgentComposer**: An animated, chat-like AI orchestration interface embedded organically into the Hero section to elegantly demonstrate the platform's core capabilities.

---

## Architecture & Workflows

### System Topology
The architecture enforces strict separation of concerns across reasoning, policy, data, and presentation layers:
```text
┌─────────────────────────────────────────────────────────────┐
│  Channels (WhatsApp, MCP, Web UI)                           │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Routes (v1)                                        │
│  ┌──────────┬───────────┬──────────┬────────┬─────────────┐ │
│  │ Auth     │ Discovery │ Txn Orch │ Payment│ Audit       │ │
│  └──────────┴───────────┴──────────┴────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Services                                                    │
│  ┌──────────┬───────────┬──────────┬────────┬─────────────┐ │
│  │ AI Orch  │ Policy    │ Capabil- │ Razorpay│ ARM Gen    │ │
│  │ (OpenAI) │ Engine    │ ity Svc  │ Adapter │            │ │
│  └──────────┴───────────┴──────────┴────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Data (SQLModel + Alembic)                                   │
│  SQLite (dev) │ PostgreSQL (prod)                            │
└─────────────────────────────────────────────────────────────┘
```

### Transaction Execution Flow

1. **Buyer Intent**: The user issues a natural language directive (e.g., "Procure organic honey under ₹500").
2. **AI Orchestrator**: The language model interprets the intent, generating strictly-typed structured constraints.
3. **Registry Discovery**: The system filters merchant products strictly based on the extracted parameters.
4. **Deterministic Scoring**: Candidate products are ranked via a hardcoded formula: `0.45×price + 0.25×delivery + 0.20×rating + 0.10×policy`.
5. **Approval Phase**: 
   - If the item price exceeds the buyer's autonomous spending limit, the state shifts to `PENDING_APPROVAL`.
   - The buyer explicitly authorizes the transaction via the user interface.
6. **Policy Engine**: A final, deterministic policy check is executed. 
7. **Execution**: A bounded, one-time capability token is issued, locking the database row (`SELECT FOR UPDATE`), and generating an idempotent Razorpay Payment Link.

---

## Security & Policy Enforcement

- **Strict Policy Gatekeeping** — The deterministic policy engine serves as the absolute gatekeeper. No transaction can proceed without explicit cryptographic policy approval.
- **Idempotent Payment Generation** — A cryptographic fingerprint ensures the prevention of duplicate payment links.
- **Immutable Audit Logging** — Every material action is immutably recorded in the `AuditEvent` ledger for compliance and transparency.
- **LLM Constraint Enforcement** — Artificial intelligence dictates preference, not execution. All financial decisions remain strictly deterministic.
- **Server-Side Secret Management** — Payment tokens and credentials are never exposed to the client or the Agent-Readable Manifest.
- **Role-Based Access Control (RBAC)** — Identity and authorization are strictly derived from JWTs `(BUYER, MERCHANT_OWNER, PLATFORM_ADMIN)`.

---

## Technology Stack

| Layer | Technology |
|-------|--------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **AI / Orchestration** | OpenAI Structured Outputs (`gpt-4o-mini`) |
| **Database** | SQLModel, Alembic, SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT (HS256), Argon2, JTI revocation |
| **Payments** | Razorpay APIs |
| **Frontend** | React 18, Next.js 14, TypeScript, Tailwind CSS |
| **Animations / 3D** | Framer Motion, Three.js, React Three Fiber |
| **CI / Quality Assurance** | GitHub Actions, Ruff, Mypy, ESLint, Pytest |

---

## Project Structure

```text
agentsetu/
├─ services/api/          # FastAPI Backend Architecture
│  ├─ main.py             # Application entry point & initialization
│  ├─ models/             # SQLModel Database definitions
│  ├─ arm/                # ARM manifest generation and schemas
│  ├─ policy/             # Deterministic authorization engine
│  ├─ payments/           # Razorpay integration adapter
│  ├─ ai/                 # OpenAI buyer orchestration service
│  ├─ audit/              # Append-only immutable audit service
│  └─ routes/             # RESTful API endpoints
│
├─ apps/web/              # Next.js 14 Frontend Application
│  ├─ app/buyer/          # Buyer conversational UI and approval flows
│  ├─ app/merchant/       # Merchant catalog import and policy controls
│  ├─ app/audit/          # Transaction timeline visualization
│  ├─ components/         # 3D objects, advanced UI, and composites
│  └─ lib/api.ts          # Strongly typed API client
│
├─ .github/workflows/     # CI pipelines (Linting, Typechecking, Tests)
├─ start.sh               # Local environment initialization script
└─ README.md
```

---

## Quick Start Guide

### 1. Repository Initialization

```bash
git clone https://github.com/simply-mihir/AgentSetu.git
cd agentsetu
cp services/api/.env.example services/api/.env
```

### 2. Environment Configuration

Edit `services/api/.env` with your respective credentials:
```env
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret
OPENAI_API_KEY=sk-your-key
```

### 3. Application Deployment

```bash
# Automated deployment
./start.sh
```

**Manual Initialization:**
```bash
# Backend Service (Terminal 1)
cd services/api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend Service (Terminal 2)
cd apps/web
npm install
npm run dev
```

### 4. Platform Navigation

- **Public Landing Interface**: [http://localhost:3000/](http://localhost:3000/)
- **Buyer Application**: [http://localhost:3000/buyer](http://localhost:3000/buyer)
- **Merchant Console**: [http://localhost:3000/merchant](http://localhost:3000/merchant)
- **Audit Center**: [http://localhost:3000/audit](http://localhost:3000/audit)
- **API Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Demonstration Scenarios

### Scenario A: High-Velocity Checkout (< ₹500)
- **Input**: `"Procure organic honey under ₹500, deliver in 2 days"`
- **Result**: The orchestrator extracts constraints, discovers compliant products, and ranks candidates. The policy engine ALLOWS execution instantaneously, resulting in immediate Razorpay link generation.

### Scenario B: Boundary Constraints & Approval Escalation
- **Input**: `"Procure desi cow ghee under ₹700"`
- **Result**: The ₹699 item price breaches the configured ₹500 auto-approval threshold. The transaction state shifts to `NEEDS_APPROVAL`. The buyer must manually authorize the purchase within the UI before payment processing proceeds.

### Scenario C: Graceful Degradation & Failure Handling
- **Trigger**: Attempting to execute an expired Razorpay link or simulating network failure.
- **Result**: The system safely transitions the transaction state to `PAYMENT_UNKNOWN` and proposes recovery mechanisms without duplicating orders or creating race conditions.

---

## Continuous Integration & Quality Assurance

AgentSetu maintains strict, enterprise-grade CI pipelines:
- **Backend Linting**: Strictly enforced via `ruff`.
- **Backend Typechecking**: Comprehensive enforcement via `mypy`, naturally suppressing SQLModel dynamic property false positives.
- **Frontend Quality**: Enforces zero-warning strictness (`next lint --max-warnings 0`) and type validation (`tsc --noEmit`).
- **Testing**: Rigorous `pytest` validation of the orchestration, policy, and routing layers.
