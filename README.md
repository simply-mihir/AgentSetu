<div align="center">
  <h1>⚡ AgentSetu</h1>
  <p><strong>The authorization and interoperability layer for agentic commerce.</strong></p>
  <p><i>Merchant manifests · AI buyer · Bounded payment · Immutable audit · Premium 3D UI</i></p>
</div>

---

Built for **Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce**.

## 🚀 What it does

AgentSetu bridges the gap between AI orchestration and secure financial transactions. It makes Razorpay merchants **machine-readable**, **discoverable**, **policy-aware**, and **safely transactable by AI agents**—all without giving the agent unrestricted spending authority.

| Component | Responsibility |
|-----------|---------------|
| **ARM** (Agent-Readable Manifest) | Machine-readable merchant manifest containing products, policies, and payment endpoints. |
| **AI Buyer Orchestrator** | Translates natural language into structured constraints, ranks candidates, and generates explanations. |
| **Policy Engine** | Deterministic authorization: spend caps, approval gates, category restrictions. |
| **Razorpay Adapter** | Handles bounded, idempotent, and secure test-mode Payment Links. |
| **Audit Service** | Append-only event trail: every material agent and financial action is immutably recorded. |

> **Architecture principle:** _The LLM reasons; deterministic code decides. The agent may propose; policy must approve._

---

## 🎨 Premium V3 User Interface

The frontend application has been meticulously designed and engineered with a **premium, glassmorphism-driven light aesthetic**. 

**Key Visual Features:**
- **Liquid Glass & Frost Aesthetics**: Heavy use of backdrop-blur, subtle gradients, and soft white/sea-green ambient lighting.
- **Dynamic 3D Environment**: Interactive 3D pillar elements rendered with `Three.js` and `React Three Fiber` that react dynamically to the scroll state, creating a living page.
- **Scroll-Linked Depth Animations**: UI cards and sections emerge from a glass plane with seamless z-index and opacity transitions powered by `Framer Motion`.
- **The AgentComposer**: An animated, chat-like AI orchestration interface embedded seamlessly into the Hero section to demonstrate the core capability of the product intuitively.

---

## 🏗️ Architecture & Workflows

### System Layers
The architecture is strictly separated into reasoning, policy, data, and presentation layers:
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

### Transaction Flow

1. **Buyer Intent**: User types a natural language prompt (e.g. "Buy organic honey under ₹500").
2. **AI Orchestrator**: The LLM parses the intent and generates strictly-typed structured constraints.
3. **Registry Discovery**: System filters merchant products based on the constraints.
4. **Deterministic Scoring**: Products are ranked based on a hardcoded formula: `0.45×price + 0.25×delivery + 0.20×rating + 0.10×policy`.
5. **Approval Phase**: 
   - If the item price exceeds the buyer's autonomous limit, it transitions to `PENDING_APPROVAL`.
   - Buyer explicitly approves the transaction in the UI.
6. **Policy Engine**: A final, deterministic check is performed. 
7. **Execution**: A bounded, one-time capability token is issued, locking the row (`SELECT FOR UPDATE`), and creating an idempotent Razorpay Payment Link.

---

## 🛡️ Security & Policy Engine

- ✅ **No payment without policy pass** — The deterministic policy engine is the absolute gatekeeper.
- ✅ **Idempotent payment creation** — A cryptographic fingerprint prevents duplicate payment links.
- ✅ **Append-only audit** — Every single material action is immutably recorded in the `AuditEvent` log.
- ✅ **LLM cannot override limits** — AI dictates preference, not execution. All financial decisions are deterministic.
- ✅ **Secrets server-side only** — Payment tokens are never exposed to the browser or ARM.
- ✅ **Role-Based Access Control** — Identity is strictly derived from JWT `(BUYER, MERCHANT_OWNER, PLATFORM_ADMIN)`.

---

## 🛠️ Tech Stack

| Layer | Choice |
|-------|--------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **AI / Orchestration** | OpenAI Structured Outputs (`gpt-4o-mini`) |
| **Database** | SQLModel, Alembic, SQLite (dev) / PostgreSQL (prod) |
| **Auth** | JWT (HS256), Argon2, JTI revocation |
| **Payments** | Razorpay APIs |
| **Frontend** | React 18, Next.js 14, TypeScript, Tailwind CSS |
| **Animations / 3D** | Framer Motion, Three.js, React Three Fiber |
| **CI / Quality** | GitHub Actions, Ruff, Mypy, ESLint |

---

## 📦 Project Structure

```text
agentsetu/
├─ services/api/          # FastAPI Backend
│  ├─ main.py             # App entry point + auto-seed
│  ├─ models/             # SQLModel DB models
│  ├─ arm/                # ARM manifest generator + schema
│  ├─ policy/             # Deterministic policy engine
│  ├─ payments/           # Razorpay adapter
│  ├─ ai/                 # OpenAI buyer orchestrator
│  ├─ audit/              # Append-only audit service
│  └─ routes/             # REST endpoints
│
├─ apps/web/              # Next.js 14 Frontend
│  ├─ app/buyer/          # Buyer chat + approval + receipt UI
│  ├─ app/merchant/       # Catalog import + policy controls
│  ├─ app/audit/          # Transaction timeline viewer
│  ├─ components/         # 3D objects, UI, and animated composites
│  └─ lib/api.ts          # Typed API client
│
├─ .github/workflows/     # CI pipelines (Linting, Mypy, Build, Tests)
├─ start.sh               # Local startup script
└─ README.md
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/simply-mihir/AgentSetu.git
cd agentsetu
cp services/api/.env.example services/api/.env
```

### 2. Configure Environment

Edit `services/api/.env`:
```env
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret
OPENAI_API_KEY=sk-your-key
```

### 3. Start the Application

```bash
# Easy start
./start.sh
```

**Manual Start:**
```bash
# Backend (Terminal 1)
cd services/api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (Terminal 2)
cd apps/web
npm install
npm run dev
```

### 4. Navigate the Platforms

- **Public Landing Page**: [http://localhost:3000/](http://localhost:3000/)
- **Buyer UI**: [http://localhost:3000/buyer](http://localhost:3000/buyer)
- **Merchant Console**: [http://localhost:3000/merchant](http://localhost:3000/merchant)
- **Audit Center**: [http://localhost:3000/audit](http://localhost:3000/audit)
- **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📸 Demo Scenarios

### A. Happy Path — Fast checkout under ₹500
- **Input**: `"Buy organic honey under ₹500, deliver in 2 days"`
- **Result**: AI extracts constraints → discovers products → ranks candidates → policy ALLOWS execution instantly → Razorpay link created.

### B. Boundary — Approval Required
- **Input**: `"Buy desi cow ghee under ₹700"`
- **Result**: The ₹699 price breaches the configured ₹500 auto-approval limit → state shifts to `NEEDS_APPROVAL` → buyer approves manually in the UI → payment is processed.

### C. Graceful Failure
- **Trigger**: Attempting to execute an expired Razorpay link or simulating a failure.
- **Result**: The system safely transitions the transaction to `PAYMENT_UNKNOWN` and proposes recovery without duplicating orders or creating race conditions.

---

## 📊 Continuous Integration

AgentSetu features robust CI pipelines:
- **Backend Linting**: Enforced with `ruff`.
- **Backend Typechecking**: Strict enforcement with `mypy` natively suppressing SQLModel dynamic properties.
- **Frontend Quality**: Enforces `next lint --max-warnings 0` and `tsc --noEmit`.
- **Testing**: Pytest validation of the orchestration and routing layers.
