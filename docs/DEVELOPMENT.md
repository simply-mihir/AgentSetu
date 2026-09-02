# AgentSetu — Development Guide

## Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- Razorpay test keys ([dashboard.razorpay.com/app/keys](https://dashboard.razorpay.com/app/keys))
- OpenAI API key (or use `sk-demo` for offline dev — AI features will fail gracefully)

---

## Setup

### Backend

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys

uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000

### Docker (full stack)

```bash
docker compose up -d
# API: http://localhost:8000
# Web: http://localhost:3000 (run separately or add to compose)
```

---

## Testing

```bash
cd services/api
source .venv/bin/activate
python3 -m pytest ../../tests/ -v --tb=short
```

Tests use an in-memory SQLite database (`StaticPool`) and set `TESTING=1` to disable rate limiting.

### Test structure

```
tests/
├── integration/          # Full flow tests (intent → approve → pay)
│   └── test_purchase_flow.py
├── security/             # Auth, tenant isolation, cross-tenant
│   ├── test_auth_required.py
│   ├── test_cross_tenant.py
│   └── test_tenant_isolation.py
└── unit/                 # Service-level tests
    ├── test_ai_security.py
    ├── test_api_hardening.py
    ├── test_arm_protocol.py
    ├── test_buyer_policy.py
    ├── test_capability_hardened.py
    ├── test_capability_service.py
    ├── test_commerce_receipt.py
    ├── test_discovery_performance.py
    ├── test_idempotency.py
    ├── test_policy_engine.py
    └── test_webhook_reliability.py
```

### Adding tests

- Place in the appropriate subdirectory
- Use `client` and `session` fixtures from `tests/conftest.py`
- Use `demo_merchant`, `demo_buyer`, `buyer_headers` fixtures for authenticated flows
- Password for test accounts: `TestPass123!` (meets Phase 12 validation rules)

---

## Database

### Development (SQLite)

Default. No setup needed. Database file: `agentsetu.db`.

Reset: delete the file and restart.

### Staging/Production (PostgreSQL)

```env
DATABASE_URL=postgresql://user:pass@host:5432/agentsetu
```

Schema changes: use Alembic.

```bash
# Generate migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current version
alembic current
```

---

## Key Conventions

### Error format

All API errors return:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "request_id": "req_abc123",
    "details": {}
  }
}
```

Error codes are defined in `errors.py::ErrorCode`.

### Auth

- JWT in `Authorization: Bearer <token>` header
- `get_current_user` dependency raises 401 if missing
- `get_optional_user` returns `None` for anonymous endpoints
- Identity is **always** from the JWT, never from request body

### Audit

Every material action calls `audit_service.record()` with:
- `transaction_id`, `correlation_id` — for grouping
- `actor` — who did it (user_id or "agentsetu" or "razorpay")
- `event_type` — what happened (e.g., `policy.decision`, `payment.created`)
- `decision`, `reason_codes` — why

---

## Environment Variables

See `services/api/.env.example` for all available settings.

Key ones for development:
- `APP_MODE=demo` — seeds sample merchants, enables `/docs`
- `DATABASE_URL=sqlite:///./agentsetu.db`
- `SECRET_KEY` — leave empty for dev (auto-generated insecure key)
- `LOG_FORMAT=text` — human-readable logs
