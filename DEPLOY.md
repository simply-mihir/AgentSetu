# AgentSetu — Production Deployment Requirements

Complete checklist to deploy AgentSetu for real users with live Razorpay payments.

---

## 01 · Secrets & Environment Variables

**Priority: Required** — the app refuses to start in production mode if any of these are missing.

### Generate secret keys

```bash
# Run each command once. Copy the output — these are your SECRET_KEY and ENCRYPTION_KEY.
python3 -c "import secrets; print(secrets.token_hex(64))"   # → SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(64))"   # → ENCRYPTION_KEY
```

> ⛔ Never commit these to git. Store in your platform's secret manager (Railway Variables, Doppler, AWS Secrets Manager, GCP Secret Manager).

### Full environment variable reference

| Variable | Value |
|---|---|
| `APP_MODE` | `production` |
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/agentsetu` |
| `SECRET_KEY` | 64-char hex (generated above) |
| `ENCRYPTION_KEY` | 64-char hex (generated above, different from SECRET_KEY) |
| `RAZORPAY_KEY_ID` | `rzp_live_XXXXXXXXXXXXXXXX` |
| `RAZORPAY_KEY_SECRET` | Live key secret from Razorpay dashboard |
| `RAZORPAY_WEBHOOK_SECRET` | Random hex, must match what's set in Razorpay dashboard |
| `OPENAI_API_KEY` | `sk-…` from platform.openai.com |
| `OPENAI_MODEL` | `gpt-4o-mini` (or `gpt-4o`) |
| `CORS_ORIGINS` | `https://yourdomain.com,https://www.yourdomain.com` |
| `BASE_URL` | `https://api.yourdomain.com` |
| `SENTRY_DSN` | From sentry.io project settings |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 h) or `480` (8 h) |
| `REDIS_URL` | `redis://…` (optional, for distributed rate limiting) |

---

## 02 · PostgreSQL Database

**Priority: Required** — SQLite is dev-only. Production needs a managed PostgreSQL.

### Choose a provider

| Provider | Notes |
|---|---|
| **Railway** (recommended) | One-click Postgres, same platform as API, connection string auto-injected |
| **Supabase** | Generous free tier, pgBouncer pooler built-in |
| **Neon** | Serverless Postgres with branching, good for early-stage |
| **AWS RDS** | Enterprise-grade, more ops overhead |

### Run migrations

Your `Dockerfile` CMD already runs migrations before starting the server:

```
sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"
```

To run manually against the production DB:

```bash
DATABASE_URL="postgresql://user:pass@host/agentsetu" alembic upgrade head
```

> ⚠️ Every future schema change needs a new Alembic migration:
> `alembic revision --autogenerate -m "describe change"` — review the generated file before running in production.

### Enable automated backups

Turn on point-in-time recovery in your provider's dashboard. For self-managed:

```bash
# Daily pg_dump at 2 AM UTC
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/agentsetu-$(date +%F).sql.gz
```

---

## 03 · Razorpay Live Activation

**Priority: Required** — test keys process zero money.

### Step 1: Complete merchant KYC

Go to **dashboard.razorpay.com → Account & Settings → Activation**. Required documents:

| Document | Notes |
|---|---|
| Business type | Proprietorship / LLP / Pvt Ltd |
| PAN card | Business PAN (or personal PAN for sole proprietors) |
| GST number | Required if annual turnover > ₹20 lakh |
| Bank account | Settlement account for Razorpay payouts |
| Business address proof | Utility bill or rental agreement |
| Cancel cheque / bank statement | For settlement account verification |

KYC approval takes **1–3 business days**. Start this immediately — it runs in parallel with the rest of setup.

### Step 2: Copy live API keys

Dashboard → Settings → API Keys → **Generate Live Mode Key Pair**.

- Key ID starts with `rzp_live_` (your `config.py` checks this prefix to gate live mode)
- Copy Key Secret immediately — it's shown only once
- Set both as `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in production env

> ⛔ If you accidentally set a test key in production, payment-link creation calls will appear to succeed but no real money moves.

### Step 3: Register the webhook URL

Dashboard → Settings → Webhooks → **Add New Webhook**:

- **URL:** `https://api.yourdomain.com/v1/webhooks/razorpay`
- **Events:** `payment_link.paid`, `payment_link.expired`, `payment.failed`
- **Secret:** Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` and set as `RAZORPAY_WEBHOOK_SECRET`

The webhook secret in Razorpay dashboard must exactly match `RAZORPAY_WEBHOOK_SECRET` in your env. Your webhook handler verifies the HMAC-SHA256 signature before touching any state.

> ⚠️ Razorpay retries failed webhooks up to 15 times over 24 hours. Your `WebhookEvent` dedup table (keyed on `provider_event_id`) handles this safely — duplicate events return `{"duplicate": true}`.

### Step 4: Validate with a real ₹1 transaction

Before any users touch the system, run the full flow yourself:

1. Create a product priced at ₹1
2. Run: intent → select → payment-link → pay on Razorpay checkout
3. Verify webhook fires and transaction transitions to `PAYMENT_SUCCESS`
4. Check `audit_events` table for a complete audit trail
5. Refund yourself the ₹1 from Razorpay dashboard

---

## 04 · Hosting & Docker

**Priority: Required**

### Choose a platform

| Platform | Notes |
|---|---|
| **Railway** (recommended) | Auto-detects Dockerfile, same platform for Postgres + Redis |
| **Render** | Good free tier, zero-downtime deploys built-in |
| **Fly.io** | Global edge containers, more config required |
| **DigitalOcean App Platform** | Managed Kubernetes, predictable pricing |

Point the build context to `services/api/` and Dockerfile to `services/api/Dockerfile`. Set the exposed port to **8000**.

### Redis for rate limiting (optional but recommended)

Without Redis, `slowapi` rate limits are per-process and reset on redeploy. Add a Redis service (Railway Redis, Render Redis, or Upstash) and set `REDIS_URL`.

### Wire health checks

Configure your platform to hit `/health` (liveness) and `/ready` (readiness) before routing traffic:

```
GET /health  → 200 { "status": "ok", "mode": "production" }
GET /ready   → 200 { "status": "ready", "checks": { "database": "ok" } }
```

---

## 05 · Domain & SSL

**Priority: Required**

- Buy a domain and configure DNS to point `api.yourdomain.com` at your backend host
- SSL is provisioned automatically by Railway, Render, and Fly via Let's Encrypt
- Update `BASE_URL=https://api.yourdomain.com` in env
- Update `CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com` in env

Verify HTTPS redirect is enforced:

```bash
curl -I http://api.yourdomain.com
# Must return 301 → https://api.yourdomain.com, not 200
```

---

## 06 · Security Headers

**Priority: Important**

Add to `services/api/main.py` (after existing middlewares):

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    if request.headers.get("content-length"):
        if int(request.headers["content-length"]) > 1_000_000:  # 1 MB
            return JSONResponse(
                {"error": {"code": "REQUEST_TOO_LARGE"}}, status_code=413
            )
    return await call_next(request)
```

Verify with [securityheaders.com](https://securityheaders.com) — aim for A or A+.

---

## 07 · Monitoring & Observability

**Priority: Important**

### Sentry — error tracking

```bash
# Add to requirements.txt
sentry-sdk[fastapi]==2.19.0
```

```python
# main.py — add before app = FastAPI(...)
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        environment=settings.environment,
    )
```

Create a project at [sentry.io](https://sentry.io) (free tier: 5k errors/month), get the DSN, set `SENTRY_DSN` in env.

### Uptime monitoring

Monitor both endpoints every 3–5 minutes:

| Tool | Cost | Notes |
|---|---|---|
| BetterUptime | Free tier | Slack/email alerts |
| UptimeRobot | Free tier | 50 monitors, 5-min interval |
| Checkly | Free tier | Good for full-flow API checks |

Alert if `/health` or `/ready` returns non-200 for 2+ consecutive checks.

### Structured JSON logging

```bash
# Add to requirements.txt
python-json-logger==2.0.7
```

```python
# main.py — replace basicConfig call
from pythonjsonlogger import jsonlogger
handler = logging.StreamHandler()
handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
))
logging.basicConfig(handlers=[handler], level=logging.INFO)
```

---

## 08 · Frontend Deployment

**Priority: Required**

### Deploy to Vercel

1. Import the GitHub repo at [vercel.com/new](https://vercel.com/new)
2. Set **Root Directory** to `apps/web`
3. Add environment variable: `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
4. Connect your custom domain in Vercel → Domains

Vercel auto-builds on every push to main. Cloudflare Proxy in front of Vercel adds WAF + DDoS protection at no cost.

### Verify CORS

After deploying both backend and frontend, open browser devtools → Network. Any request from `yourdomain.com` to `api.yourdomain.com` must not show a CORS error. If it does, check that `CORS_ORIGINS` in the backend env includes the exact frontend origin (no trailing slash).

---

## 09 · CI/CD Pipeline

**Priority: Important**

The `.github/workflows/ci.yml` is already on GitHub (pushed in the latest commit). It runs:

- **Backend:** ruff lint, mypy type check, unit + integration + security tests (41 total)
- **Frontend:** tsc, next lint, next build

Tests run in demo mode against in-memory SQLite — no external services or secrets needed in CI.

### Add `workflow` scope if not already done

```bash
gh auth refresh -h github.com -s workflow
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions backend+frontend pipeline"
git push origin main
```

---

## 10 · Compliance & Legal

**Priority: Required** — Razorpay checks all three documents during KYC activation.

### Privacy Policy

Must disclose:
- What data you collect: email, transaction history, buyer intent messages
- Where it is stored: your cloud provider (name the country)
- Who you share it with: **Razorpay** (payments), **OpenAI** (AI inference)
- OpenAI data policy: API calls may be used for safety monitoring but are not used to train models
- How users can request data deletion (DPDP Act 2023 requirement)

### Terms of Service

Must cover:
- What AgentSetu is and who can use it
- Liability limits
- Dispute resolution
- Governing law (India, or your state)

### Refund & Cancellation Policy

Must specify:
- Return window (e.g. 7 days — feeds into the product model's `return_policy` field)
- How buyers initiate a refund
- Who processes it (Razorpay)

Razorpay's activation checklist explicitly requires all three policy URLs to be live on your website.

### RBI compliance

AgentSetu is a **technology intermediary** — it creates payment links via Razorpay's API and hands off to Razorpay for collection. Razorpay holds the PA (Payment Aggregator) license from RBI. You do not need one provided:

- Funds flow directly from buyer → merchant through Razorpay
- AgentSetu never holds money in transit (no nodal account)

Your current architecture satisfies this. If you add marketplace escrow or split payments, re-evaluate with a legal advisor.

### GST

If you charge a platform service fee (e.g. a % commission on each transaction), GST at 18% applies on that fee. Razorpay can generate GST-compliant invoices. If you pass through merchant prices with no platform cut, this section doesn't affect you.

---

## 11 · Go-Live Checklist

**Priority: Required** — run through this the day before launch.

- [ ] All 41 tests pass: `pytest tests/ -v` → `41 passed, 0 failed`
- [ ] `GET https://api.yourdomain.com/health` returns `{"status": "ok", "mode": "production"}`
- [ ] `GET https://api.yourdomain.com/ready` returns `{"checks": {"database": "ok"}}`
- [ ] Razorpay KYC approved, live keys set in env (`rzp_live_` prefix confirmed)
- [ ] Webhook URL registered in Razorpay, secret matches `RAZORPAY_WEBHOOK_SECRET`
- [ ] Real ₹1 end-to-end payment completed: transaction → `PAYMENT_SUCCESS`, webhook → `PROCESSED`
- [ ] Audit trail visible in `audit_events` table for the ₹1 transaction
- [ ] Authorization capability in `CONSUMED` state after payment
- [ ] No errors in Sentry during the ₹1 test
- [ ] Security headers present: `curl -I https://api.yourdomain.com` shows `Strict-Transport-Security`
- [ ] HTTPS redirect working: `curl -I http://api.yourdomain.com` returns 301
- [ ] Frontend loads at `https://yourdomain.com` and can reach the API
- [ ] Privacy Policy, Terms of Service, and Refund Policy pages are live
- [ ] Razorpay spending limit alert configured in dashboard
- [ ] Uptime monitor active on `/health` and `/ready`
- [ ] Sentry receiving events (trigger a 404, confirm it appears in Sentry)
- [ ] **Soft launch**: invite 3–5 internal users first; watch Sentry + logs in real time for the first hour before opening to the public

---

## Quick Reference — Deployment Commands

```bash
# Generate keys
python3 -c "import secrets; print(secrets.token_hex(64))"

# Run migrations manually
DATABASE_URL="postgresql://..." alembic upgrade head

# Create a new migration after schema change
alembic revision --autogenerate -m "add column X to table Y"

# Run full test suite (all 41 must pass before deploying)
cd services/api && pytest ../../tests/ -v

# Smoke test production endpoints
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/ready

# Build Docker image locally
docker build -t agentsetu-api ./services/api

# Run Docker container locally with production env
docker run --env-file services/api/.env -p 8000:8000 agentsetu-api

# Push CI workflow (needs workflow scope)
gh auth refresh -h github.com -s workflow
git push origin main
```

---

*Stack: FastAPI 0.115 · SQLModel · Alembic · PostgreSQL · argon2 · Razorpay · OpenAI · Docker · GitHub Actions*
