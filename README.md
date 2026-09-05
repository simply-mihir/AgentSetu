<div align="center">
  <h1>AgentSetu</h1>
  <p>
    <b>The next-generation, policy-driven payment orchestration platform for autonomous AI commerce.</b>
  </p>
  <p><i>Merchant Manifests · Autonomous AI Buyers · Bounded Payments · Immutable Auditing</i></p>
  <p>
    <a href="https://github.com/simply-mihir/AgentSetu">
      <img src="https://img.shields.io/badge/Repo-GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub Repo">
    </a>
    <a href="https://github.com/simply-mihir/AgentSetu/releases">
      <img src="https://img.shields.io/github/v/release/simply-mihir/AgentSetu?style=for-the-badge" alt="Latest Release">
    </a>
    <a href="LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License">
    </a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white" alt="Next.js">
    <img src="https://img.shields.io/badge/SQLModel-SQLAlchemy-red?style=flat-square&logo=sqlite&logoColor=white" alt="SQLModel">
    <img src="https://img.shields.io/badge/Alembic-Migrations-orange?style=flat-square" alt="Alembic">
    <img src="https://img.shields.io/badge/Razorpay-SDK-02042B?style=flat-square&logo=razorpay&logoColor=white" alt="Razorpay">
    <img src="https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat-square&logo=openai&logoColor=white" alt="OpenAI">
    <img src="https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Docker">
    <img src="https://img.shields.io/badge/Pytest-8.3.3-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="Pytest">
    <img src="https://img.shields.io/badge/Ruff-Linter-D7FF64?style=flat-square" alt="Ruff">
    <img src="https://img.shields.io/badge/GitHub_Actions-CI/CD-2088FF?style=flat-square&logo=githubactions&logoColor=white" alt="GitHub Actions">
    <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind">
  </p>
</div>

---

**AgentSetu** is a high-performance, policy-driven payment orchestration engine built around three architectural pillars:

1. **Policy Engine** — per-merchant spend limits, category blocks, daily caps, and idempotent capability tokens
2. **AI Orchestration** — GPT-4o-mini Structured Outputs to parse agent intents into typed purchase actions
3. **Immutable Audit Trail** — every transaction, capability grant, and policy evaluation is recorded with a correlation ID

The service exposes a fully versioned REST API (Swagger UI auto-generated), runs on FastAPI + SQLModel, and includes a React/Next.js 3D frontend. The CI pipeline on GitHub Actions runs lint → migrations → 240+ tests → Docker build on every push.

---

## Table of Contents

1. [Key Features](#1-key-features)
2. [System Architecture](#2-system-architecture)
3. [Flow Diagrams](#3-flow-diagrams)
   - 3.1 [User Request Flow](#31-user-request-flow)
   - 3.2 [Purchase Flow](#32-purchase-flow)
   - 3.3 [Policy Engine Decision Tree](#33-policy-engine-decision-tree)
   - 3.4 [Capability Token Lifecycle](#34-capability-token-lifecycle)
4. [Database Schema](#4-database-schema)
5. [API Reference](#5-api-reference)
6. [Security Architecture](#6-security-architecture)
7. [Analytics & Scoring](#7-analytics--scoring)
8. [CI/CD Workflow](#8-cicd-workflow)
9. [Quick Start — Local Development](#9-quick-start--local-development)
10. [Running Tests](#10-running-tests)
11. [Project Structure](#11-project-structure)
12. [Environment Configuration](#12-environment-configuration)
13. [License](#13-license)

---

## 1. Key Features

### Core Capabilities

| Feature | Description |
| :--- | :--- |
| **Merchant Catalog** | Public `GET /v1/merchants/` with pagination, category filters, and product counts. Sensitive policy fields are stripped for privacy. |
| **Product Discovery** | Full-text search across merchants and products with constraints — price range, category, availability. |
| **Purchase Flow** | Auto-approved and approval-required flows with idempotent payment-link creation via Razorpay. |
| **Capability Tokens** | One-time-use, time-bounded tokens for secure payment actions. Supports revocation and expiration. |
| **Policy Engine** | Enforces spend limits, daily caps, category blocks, and custom merchant policies per transaction. |
| **ARM Manifest** | Generates a deterministic JSON manifest (`GET /v1/merchants/{id}/arm`) describing merchant risk settings. |
| **Analytics Dashboard** | Visibility scores, transaction state breakdowns, and merchant-level insights. |
| **Audit Trail** | Immutable audit events with correlation IDs for end-to-end traceability. |
| **MCP Tools** | Exposes capabilities as Model Context Protocol tools for AI agent consumption. |

### Engineering Depth

| Feature | Detail |
| :--- | :--- |
| **Zero-trust security** | JWT auth, request-ID tracking, security headers, slowapi rate-limiting |
| **AI-native design** | OpenAI Structured Outputs parse free-form agent intents into typed purchase requests |
| **Idempotency** | `Idempotency-Key` header prevents double-charges on retries |
| **Offline test suite** | pytest-asyncio with SQLite in-memory DB — no external services needed |
| **Multi-stage Docker** | Slim production image, reproducible builds |
| **Full CI/CD** | Ruff → Alembic → Pytest → Docker on every push |

---

## 2. System Architecture

```mermaid
graph TB
    subgraph Clients["Client Layer"]
        UI["Web / Mobile UI"]
        AIAgent["AI Agent"]
        MCPClient["MCP Client"]
    end

    subgraph Edge["API Layer (FastAPI)"]
        AuthMW["Auth Middleware"]
        Router["Router v1"]
        RateLimiter["Rate Limiter (slowapi)"]
    end

    subgraph Services["Service Layer"]
        PolicySvc["Policy Engine"]
        CapSvc["Capability Service"]
        ARMGen["ARM Generator"]
        AnalyticsSvc["Analytics Service"]
        AuditSvc["Audit Service"]
        AIOrch["AI Orchestration (GPT-4o-mini)"]
        RazorpayAdp["Razorpay Adapter"]
    end

    subgraph Data["Data Layer (SQLModel + Alembic)"]
        MerchantTbl[("Merchants")]
        ProductTbl[("Products")]
        TxTbl[("Transactions")]
        CapTbl[("Capabilities")]
        AuditTbl[("Audit Events")]
    end

    UI -- "HTTPS REST" --> Router
    AIAgent -- "HTTPS REST" --> Router
    MCPClient -- "MCP Tools" --> Router
    Router --> AuthMW
    AuthMW --> RateLimiter
    RateLimiter --> PolicySvc
    RateLimiter --> CapSvc
    RateLimiter --> ARMGen
    RateLimiter --> AnalyticsSvc
    RateLimiter --> AuditSvc
    RateLimiter --> AIOrch
    AIOrch --> RazorpayAdp
    PolicySvc --> MerchantTbl
    CapSvc --> CapTbl
    ARMGen --> MerchantTbl
    AnalyticsSvc --> TxTbl
    AuditSvc --> AuditTbl
    RazorpayAdp --> TxTbl

    classDef clients fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#0a0a0a
    classDef api fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#0a0a0a
    classDef svc fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#0a0a0a
    classDef data fill:#fce7f3,stroke:#ec4899,stroke-width:2px,color:#0a0a0a
    class UI,AIAgent,MCPClient clients
    class AuthMW,Router,RateLimiter api
    class PolicySvc,CapSvc,ARMGen,AnalyticsSvc,AuditSvc,AIOrch,RazorpayAdp svc
    class MerchantTbl,ProductTbl,TxTbl,CapTbl,AuditTbl data
```

**Layer responsibilities:**

```
┌──────────────────────────────────────────────────────────────────────┐
│               Channels  (Web UI · AI Agent · MCP Client)            │
├──────────────────────────────────────────────────────────────────────┤
│                     FastAPI Routes  /v1/*                            │
│   ┌──────────┬────────────┬──────────┬──────────┬────────────────┐  │
│   │  /auth   │ /merchants │/products │/payments │/analytics/audit│  │
│   └──────────┴────────────┴──────────┴──────────┴────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                        Service Layer                                 │
│   ┌──────────┬────────────┬──────────┬──────────┬────────────────┐  │
│   │AI Orch.  │Policy Eng. │ Cap.Svc  │ Razorpay │ ARM Generator  │  │
│   └──────────┴────────────┴──────────┴──────────┴────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                   Data  (SQLModel + Alembic)                         │
│          SQLite (dev / test)  │  PostgreSQL (prod)                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Flow Diagrams

### 3.1 User Request Flow

Every inbound request passes through the same middleware stack before reaching a route handler.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client (Browser / AI Agent)
    participant MW as Auth Middleware
    participant RL as Rate Limiter
    participant R as Router v1
    participant Svc as Service Layer
    participant DB as Database

    Client->>+MW: HTTP Request + Bearer Token
    MW->>MW: Verify JWT signature & expiry
    alt Token invalid or missing
        MW-->>Client: 401 Unauthorized
    else Token valid
        MW->>+RL: Forward request + identity
        RL->>RL: Check per-IP fixed window
        alt Rate limit exceeded
            RL-->>Client: 429 Too Many Requests (Retry-After)
        else Within limit
            RL->>+R: Route to handler
            R->>+Svc: Call service method
            Svc->>+DB: Query / mutate
            DB-->>-Svc: Result
            Svc-->>-R: Domain object
            R-->>-Client: JSON Response (200/201/4xx)
        end
    end
```

---

### 3.2 Purchase Flow

The critical path for an AI agent executing a purchase through AgentSetu.

```mermaid
sequenceDiagram
    autonumber
    actor Agent as AI Agent
    participant API as FastAPI
    participant Policy as Policy Engine
    participant Cap as Capability Service
    participant Razorpay as Razorpay Adapter
    participant Audit as Audit Service
    participant DB as Database

    Agent->>+API: POST /v1/payments/link (amount, merchant_id, idempotency_key)
    API->>+Policy: evaluate(agent_id, merchant_id, amount)

    Policy->>DB: Fetch merchant policy
    DB-->>Policy: spend_limit, daily_cap, blocked_categories

    alt Policy denied
        Policy-->>API: PolicyDenied (reason)
        API-->>Agent: 403 Forbidden + reason
    else Policy approved
        Policy-->>-API: PolicyApproved

        API->>+Cap: issue_token(agent_id, merchant_id, amount)
        Cap->>DB: INSERT capability token (single-use, TTL)
        DB-->>Cap: token_id
        Cap-->>-API: CapabilityToken

        API->>+Razorpay: create_payment_link(amount, token_id)
        Razorpay-->>-API: payment_link_url

        API->>+Audit: record(event=PAYMENT_LINK_CREATED, correlation_id)
        Audit->>DB: INSERT audit_event
        Audit-->>-API: ok

        API-->>-Agent: 201 Created (payment_link_url, token_id)
    end
```

**Why this is safe:**
- The Capability Token is **single-use** — replaying the request with the same `Idempotency-Key` returns the same response without re-charging.
- Policy evaluation happens **before** Razorpay is called — no charge is created until spend limits are verified.
- Every step emits an immutable **Audit Event** with a correlation ID.

---

### 3.3 Policy Engine Decision Tree

Decision logic for `POST /v1/payments/link`.

```mermaid
flowchart TD
    Start(["Incoming Payment Request"]) --> Auth{JWT valid?}

    Auth -- no --> E401["401 Unauthorized"]
    Auth -- yes --> FetchPolicy["Fetch Merchant Policy from DB"]

    FetchPolicy --> CatCheck{Category blocked?}
    CatCheck -- yes --> E403a["403 Forbidden: Category Blocked"]
    CatCheck -- no --> SpendCheck{Amount exceeds\nspend limit?}

    SpendCheck -- yes --> E403b["403 Forbidden: Spend Limit Exceeded"]
    SpendCheck -- no --> DailyCheck{Daily cap\nexceeded?}

    DailyCheck -- yes --> E403c["403 Forbidden: Daily Cap Reached"]
    DailyCheck -- no --> ApprovalCheck{Requires\napproval?}

    ApprovalCheck -- yes --> Queue["Queue for Manual Approval"]
    Queue --> Pending["202 Accepted: Pending Approval"]
    ApprovalCheck -- no --> IssueToken["Issue Capability Token"]

    IssueToken --> CreateLink["Create Razorpay Payment Link"]
    CreateLink --> Audit["Record Audit Event"]
    Audit --> Resp["201 Created: payment_link_url + token_id"]

    classDef errNode fill:#fee2e2,stroke:#ef4444,color:#0a0a0a
    classDef okNode fill:#dcfce7,stroke:#22c55e,color:#0a0a0a
    classDef pendingNode fill:#fef3c7,stroke:#f59e0b,color:#0a0a0a
    classDef decisionNode fill:#e0e7ff,stroke:#6366f1,color:#0a0a0a
    class E401,E403a,E403b,E403c errNode
    class Resp okNode
    class Pending pendingNode
    class Auth,CatCheck,SpendCheck,DailyCheck,ApprovalCheck decisionNode
```

---

### 3.4 Capability Token Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Issued : Policy approved\nPOST /v1/payments/link
    Issued --> Used : Agent completes payment\nrazorpay webhook fires
    Issued --> Expired : TTL elapsed without use
    Issued --> Revoked : Manual revocation\nDELETE /v1/capabilities/{id}
    Used --> [*]
    Expired --> [*]
    Revoked --> [*]
```

**Token guarantees:**
- **Single-use** — once `Used`, re-submission is rejected with `410 Gone`
- **Time-bounded** — TTL enforced at the DB layer via `expires_at` index scan
- **Revocable** — agents or admins can invalidate a token before it is consumed

---

## 4. Database Schema

### Entity Relationship Overview

```mermaid
erDiagram
    MERCHANTS {
        int id PK
        string name
        string category
        string email
        float max_autonomous_spend_inr
        float approval_threshold_inr
        float daily_spend_cap_inr
        json blocked_categories
        float visibility_score
        int product_count
        datetime created_at
    }

    PRODUCTS {
        int id PK
        int merchant_id FK
        string name
        string description
        float price_inr
        string category
        bool available
        datetime created_at
    }

    TRANSACTIONS {
        int id PK
        int merchant_id FK
        string agent_id
        float amount_inr
        string status
        string razorpay_link_id
        string idempotency_key
        string correlation_id
        datetime created_at
    }

    CAPABILITIES {
        int id PK
        int merchant_id FK
        string agent_id
        float amount_inr
        string token_id
        string status
        datetime expires_at
        datetime created_at
    }

    AUDIT_EVENTS {
        int id PK
        string event_type
        string correlation_id
        string agent_id
        int merchant_id FK
        json payload
        datetime occurred_at
    }

    MERCHANT_USERS {
        int id PK
        int merchant_id FK
        string email
        string hashed_password
        string role
        datetime created_at
    }

    MERCHANTS ||--o{ PRODUCTS : "lists"
    MERCHANTS ||--o{ TRANSACTIONS : "receives"
    MERCHANTS ||--o{ CAPABILITIES : "grants"
    MERCHANTS ||--o{ AUDIT_EVENTS : "generates"
    MERCHANTS ||--o{ MERCHANT_USERS : "has"
```

### Table: `merchants` (dimension)

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | `integer` | PK, autoincrement |
| `name` | `varchar(128)` | Not null, unique |
| `category` | `varchar(64)` | Product category domain |
| `email` | `varchar(256)` | Unique, indexed |
| `max_autonomous_spend_inr` | `float` | Max a single AI-agent payment can be |
| `approval_threshold_inr` | `float` | Above this → requires human approval |
| `daily_spend_cap_inr` | `float` | Rolling 24-hour cap across all agents |
| `blocked_categories` | `json` | List of product categories denied |
| `visibility_score` | `float` | Computed score 0–1 (see §7) |
| `product_count` | `integer` | Denormalized for fast catalog listing |

### Table: `capabilities` (fact)

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | `integer` | PK, autoincrement |
| `token_id` | `varchar(64)` | **Unique**, indexed — UUID issued at creation |
| `merchant_id` | `integer` | FK → `merchants.id` |
| `agent_id` | `varchar(128)` | Requesting agent identifier |
| `amount_inr` | `float` | Authorized amount |
| `status` | `varchar(16)` | `issued` / `used` / `expired` / `revoked` |
| `expires_at` | `timestamptz` | Indexed — swept by cleanup job |

### Table: `audit_events` (immutable log)

| Column | Type | Notes |
| :--- | :--- | :--- |
| `id` | `integer` | PK, autoincrement |
| `event_type` | `varchar(64)` | `PAYMENT_LINK_CREATED`, `POLICY_DENIED`, `TOKEN_REVOKED`, etc. |
| `correlation_id` | `varchar(64)` | Ties together all events in one request chain |
| `agent_id` | `varchar(128)` | Nullable (public endpoints) |
| `merchant_id` | `integer` | FK → `merchants.id` |
| `payload` | `json` | Full context snapshot |
| `occurred_at` | `timestamptz` | Indexed — **never updated after insert** |

---

## 5. API Reference

| Method | Path | Auth | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/v1/auth/token` | No | Issue JWT for merchant user |
| `GET` | `/v1/merchants/` | No | List merchants — policy fields omitted |
| `GET` | `/v1/merchants/{id}` | Yes | Full merchant details including policy |
| `GET` | `/v1/merchants/{id}/arm` | No | ARM manifest JSON |
| `GET` | `/v1/products/` | No | Search products with filters |
| `POST` | `/v1/payments/link` | Yes | Create idempotent Razorpay payment link |
| `GET` | `/v1/payments/receipt/{transaction_id}` | Yes | Retrieve payment receipt |
| `GET` | `/v1/analytics/{merchant_id}/overview` | Yes | Visibility score + improvement tips |
| `GET` | `/v1/transactions/` | Yes | List recent transactions |
| `GET` | `/v1/audit/` | Yes | List audit events |
| `GET` | `/v1/mcp/tools` | No | List available MCP tool schemas |

All endpoints are documented via **Swagger UI** at `http://localhost:8000/docs`.

<details>
<summary><b>POST /v1/payments/link — request & response</b></summary>

**Request:**
```json
{
  "merchant_id": 42,
  "amount_inr": 1500.00,
  "description": "Purchase: Wireless Keyboard",
  "idempotency_key": "agent-session-abc-txn-001"
}
```

**Response (201 Created):**
```json
{
  "transaction_id": 198,
  "payment_link_url": "https://rzp.io/l/xyz123",
  "token_id": "cap-uuid-here",
  "status": "pending",
  "amount_inr": 1500.00,
  "merchant_id": 42,
  "correlation_id": "req-uuid-here",
  "created_at": "2026-09-05T13:00:00Z"
}
```

**Error codes:** `401` missing/invalid JWT · `403` policy denied · `409` idempotency conflict · `429` rate limited

</details>

<details>
<summary><b>GET /v1/merchants/{id}/arm — ARM Manifest</b></summary>

```json
{
  "merchant_id": 42,
  "merchant_name": "TechZone Electronics",
  "generated_at": "2026-09-05T13:00:00Z",
  "policy": {
    "max_autonomous_spend_inr": 5000,
    "approval_threshold_inr": 2000,
    "daily_spend_cap_inr": 20000,
    "blocked_categories": ["gambling", "adult"]
  },
  "visibility_score": 0.87,
  "product_count": 34,
  "risk_level": "LOW"
}
```

</details>

---

## 6. Security Architecture

```mermaid
flowchart TD
    Req["Incoming HTTP Request"] --> Header["Inject X-Request-ID + Sec Headers"]
    Header --> JWT{Bearer Token\npresent?}

    JWT -- no --> P401["401 Unauthorized"]
    JWT -- yes --> Verify["Verify JWT (python-jose)"]
    Verify --> Valid{Signature\n& expiry ok?}

    Valid -- no --> P401b["401 Unauthorized"]
    Valid -- yes --> RL["Rate Limiter (slowapi)\n60 req/min per IP"]

    RL --> Exceeded{Limit\nexceeded?}
    Exceeded -- yes --> P429["429 Too Many Requests\n+ Retry-After header"]
    Exceeded -- no --> Input["Pydantic Schema Validation"]

    Input --> InputOk{Schema\nvalid?}
    InputOk -- no --> P422["422 Unprocessable Entity"]
    InputOk -- yes --> Handler["Route Handler"]

    Handler --> Idempotency{Idempotency-Key\ncollision?}
    Idempotency -- yes --> Replay["Return cached 201 response"]
    Idempotency -- no --> Policy["Policy Engine"]

    classDef errNode fill:#fee2e2,stroke:#ef4444,color:#0a0a0a
    classDef okNode fill:#dcfce7,stroke:#22c55e,color:#0a0a0a
    class P401,P401b,P422,P429 errNode
    class Handler,Policy,Replay okNode
```

**Security controls in depth:**

| Control | Implementation |
| :--- | :--- |
| **JWT Auth** | `python-jose`, HS256, configurable secret, short-lived tokens |
| **Request-ID** | `X-Request-ID` injected by middleware, propagated to all log lines |
| **Security Headers** | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store` |
| **Rate Limiting** | `slowapi` fixed-window, 60 req/min default per IP, `Retry-After` on 429 |
| **Input Validation** | Pydantic schemas, strict type coercion, no raw SQL |
| **Idempotency** | SHA-256 keyed on `Idempotency-Key` header — safe to retry |
| **Policy Isolation** | Sensitive fields (`max_autonomous_spend_inr`, etc.) never returned from public endpoints |

---

## 7. Analytics & Scoring

AgentSetu computes a **visibility score (0–1)** per merchant, updated on every analytics request.

```mermaid
flowchart LR
    A["Product Count\n(0–1)"] --> Score["Weighted\nVisibility Score"]
    B["Image Completeness\n(0–1)"] --> Score
    C["Policy Transparency\n(0–1)"] --> Score
    D["Transaction\nSuccess Rate (0–1)"] --> Score
    E["Review Rating\nDistribution (0–1)"] --> Score

    Score --> Low["0.0 – 0.4\nLow Visibility"]
    Score --> Med["0.4 – 0.7\nModerate Visibility"]
    Score --> High["0.7 – 1.0\nHigh Visibility"]
```

**Score formula:**

```
visibility_score =
    0.30 × product_completeness
  + 0.20 × image_score
  + 0.20 × policy_transparency
  + 0.20 × txn_success_rate
  + 0.10 × rating_score
```

Scores are **deterministic and reproducible** — given the same merchant state, the same score is always produced. The analytics endpoint also returns actionable improvement tips keyed to which sub-score is lowest.

---

## 8. CI/CD Workflow

```mermaid
flowchart TD
    Push["Push / PR to GitHub"] --> GHA["GitHub Actions Triggered"]

    GHA --> Setup["Setup Python 3.12\n+ Cache dependencies"]
    Setup --> Install["pip install setuptools less than 70.0.0\n+ requirements.txt"]
    Install --> Lint["Ruff Lint"]

    Lint --> LintOk{Lint\npassed?}
    LintOk -- no --> Fail1["Fail: Lint Error"]
    LintOk -- yes --> Migrate["Alembic upgrade head"]

    Migrate --> MigOk{Migrations\nok?}
    MigOk -- no --> Fail2["Fail: Migration Error"]
    MigOk -- yes --> Tests["Pytest suite (240+ tests)"]

    Tests --> TestOk{All\npassed?}
    TestOk -- no --> Fail3["Fail: Test Failure\n+ Notify Developer"]
    TestOk -- yes --> Docker["Docker multi-stage build"]

    Docker --> Push2["Push image to GHCR"]
    Push2 --> Deploy["Deploy to Staging"]

    classDef failNode fill:#fee2e2,stroke:#ef4444,color:#0a0a0a
    classDef passNode fill:#dcfce7,stroke:#22c55e,color:#0a0a0a
    class Fail1,Fail2,Fail3 failNode
    class Deploy passNode
```

**Pipeline steps (`.github/workflows/ci.yml`):**

| Step | Detail |
| :--- | :--- |
| 1. Checkout | Full clone with submodules |
| 2. Python Setup | 3.12, pip cache from `requirements.txt` hash |
| 3. Dependencies | `setuptools<70.0.0` pinned; prevents pydantic-core build failures |
| 4. Ruff | Zero-tolerance linting; auto-fix mode off in CI |
| 5. Alembic | `alembic upgrade head` against a fresh SQLite DB |
| 6. Pytest | 240+ tests, `--tb=short`, SQLite + mocked Razorpay |
| 7. Docker Build | Multi-stage: builder → slim runtime |
| 8. Push + Deploy | GHCR image push, staging deployment |

---

## 9. Quick Start — Local Development

```bash
# Clone
git clone https://github.com/simply-mihir/AgentSetu.git
cd AgentSetu/services/api

# Create and activate virtualenv
python -m venv .venv && source .venv/bin/activate

# Install dependencies (setuptools must be <70.0.0)
pip install "setuptools<70.0.0"
pip install -r requirements.txt

# Run migrations (creates SQLite dev DB)
alembic upgrade head

# Start API server (hot-reload)
uvicorn main:app --reload
```

**Access points:**
- API → [http://localhost:8000](http://localhost:8000)
- Swagger UI → [http://localhost:8000/docs](http://localhost:8000/docs)
- Redoc → [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Docker (Multi-stage)

```bash
# Boot the full stack
docker compose up --build
```

```dockerfile
# ---------- Build Stage ----------
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install "setuptools<70.0.0" && pip install -r requirements.txt
COPY . .

# ---------- Runtime Stage ----------
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 10. Running Tests

The test suite uses SQLite in-memory and a mocked Razorpay SDK — **no external services needed**.

```bash
cd AgentSetu

# Run full suite
pytest ../../tests/ -v --tb=short

# Run with coverage
pytest ../../tests/ --cov=. --cov-report=term-missing
```

**Coverage map:**

| Module | Coverage |
| :--- | :--- |
| Policy Engine | >98% |
| Capability Service | >97% |
| Analytics & Scoring | >95% |
| Auth & Security | >95% |
| Payment Flow | >93% |
| Audit Trail | >97% |
| **Overall** | **>95%** |

---

## 11. Project Structure

```text
AgentSetu/
├── .github/
│   └── workflows/
│       └── ci.yml                          # Lint → Migrate → Test → Docker
├── apps/
│   └── web/                                # Next.js 14 + Three.js frontend
│       ├── app/                            # App Router pages
│       ├── components/
│       │   ├── agent/AgentSetuOrb.tsx      # 3D animated orb (React Three Fiber)
│       │   └── landing/                    # Landing page sections
│       └── styles/globals.css              # Tailwind + glassmorphic tokens
├── services/
│   └── api/                                # FastAPI backend
│       ├── main.py                         # App factory + middleware + router
│       ├── routes/
│       │   ├── auth.py                     # JWT issue + verify
│       │   ├── merchants.py                # Catalog + ARM
│       │   ├── products.py                 # Discovery + search
│       │   ├── payments.py                 # Payment link + receipt
│       │   ├── analytics.py                # Visibility score
│       │   ├── transactions.py             # Txn history
│       │   ├── audit.py                    # Audit log
│       │   └── mcp.py                      # MCP tool schemas
│       ├── models/                         # SQLModel ORM models
│       ├── schemas/                        # Pydantic request/response schemas
│       ├── payments/
│       │   └── razorpay_adapter.py         # Razorpay SDK wrapper
│       ├── migrations/
│       │   ├── env.py                      # Alembic environment
│       │   └── versions/                   # Migration scripts
│       └── requirements.txt
├── tests/
│   ├── conftest.py                         # Fixtures (SQLite + mocked Razorpay)
│   └── unit/
│       ├── test_policy_engine.py
│       ├── test_capability_service.py
│       ├── test_analytics.py
│       ├── test_security.py
│       ├── test_purchase_flow.py
│       └── test_discovery_performance.py   # Ensures no sensitive field leakage
├── docker-compose.yml
└── README.md
```

---

## 12. Environment Configuration

| Variable | Purpose | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./dev.db` or `postgresql://...` |
| `SECRET_KEY` | JWT signing secret | 32+ character random string |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT TTL | `60` |
| `RAZORPAY_KEY_ID` | Razorpay API key | `rzp_test_...` |
| `RAZORPAY_KEY_SECRET` | Razorpay secret | `...` |
| `OPENAI_API_KEY` | OpenAI key for AI orchestration | `sk-...` |
| `RATE_LIMIT_DEFAULT` | slowapi limit string | `"60/minute"` |
| `CORS_ORIGINS` | Allowed origins | `"http://localhost:3000"` |

Copy `.env.example` → `.env` and fill in values before starting.

---

## 13. License

MIT — see [LICENSE](LICENSE).

---

<div align="center">
  <sub>Built by <a href="https://github.com/simply-mihir">@simply-mihir</a> · Production-ready, AI-native, and open-source.</sub>
</div>
