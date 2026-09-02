# AgentSetu — Free-Tier Deployment Guide

> Deploy the full AgentSetu prototype using only free tiers and Razorpay Test Mode.  
> Total recurring cost: **₹0/month** (OpenAI pay-as-you-go ~₹0.80 per 100 demos).  
> Time: ~45 minutes.

---

## Architecture

```
                    ┌─────────────────┐
                    │   Vercel (Free)  │
                    │   Next.js 14     │
                    └────────┬────────┘
                             │  HTTPS
                             ▼
                    ┌─────────────────┐
                    │  Render (Free)   │
                    │  FastAPI + Uvi   │
                    └───┬────┬────┬───┘
                        │    │    │
            ┌───────────┘    │    └───────────┐
            ▼                ▼                ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ Neon (Free)  │ │Upstash (Free)│ │ Sentry (Free)│
   │ PostgreSQL   │ │  Redis       │ │ Errors       │
   └──────────────┘ └──────────────┘ └──────────────┘
            │
            ▼
   ┌──────────────┐         ┌──────────────┐
   │ Razorpay     │         │   OpenAI     │
   │ Test Mode    │         │  gpt-4o-mini │
   └──────────────┘         └──────────────┘
```

## Free-Tier Service Map

| Component | Provider | Free Tier Limits |
|-----------|----------|-----------------|
| Database | **Neon** PostgreSQL 16 | 0.5 GB, 190 compute-hours/mo, no expiry |
| Redis | **Upstash** | 10K commands/day, 256 MB, 1 database |
| Backend | **Render** Web Service | 750 hours/mo, spins down after 15 min idle |
| Frontend | **Vercel** Hobby | 100 GB bandwidth, automatic HTTPS, Edge CDN |
| Payments | **Razorpay** Test Mode | Unlimited test transactions, no KYC needed |
| AI | **OpenAI** gpt-4o-mini | Pay-as-you-go, ~₹1.25/1M input tokens |
| Errors | **Sentry** Developer | 5K errors/mo, 30-day retention |

**Why these providers?**
- **Neon** over Render Postgres — no 90-day database expiry
- **Upstash** over self-hosted Redis — serverless, no container needed
- **Render** over Railway — no credit card required for free tier
- **Vercel** — natural home for Next.js

---

## Accounts to Create

Sign up for these before starting. All free tiers require no credit card except OpenAI.

- [ ] **GitHub** — needed for Render and Vercel deploys
- [ ] **Neon** — [neon.tech](https://neon.tech) — sign up with GitHub
- [ ] **Upstash** — [upstash.com](https://upstash.com) — sign up with GitHub
- [ ] **Render** — [render.com](https://render.com) — sign up with GitHub
- [ ] **Vercel** — [vercel.com](https://vercel.com) — sign up with GitHub
- [ ] **Razorpay** — [dashboard.razorpay.com](https://dashboard.razorpay.com) — sign up with email
- [ ] **OpenAI** — [platform.openai.com](https://platform.openai.com) — requires payment method (initial free credits: $5–$18)
- [ ] **Sentry** (optional) — [sentry.io](https://sentry.io) — sign up with GitHub

---

## Step 1 — Database (Neon PostgreSQL)

1. Go to **neon.tech** → Create a new project
2. Name: `agentsetu`. Region: match your Render backend (e.g., `ap-southeast-1`)
3. PostgreSQL version: **16**
4. Copy the **connection string**:
   ```
   postgresql://agentsetu_owner:xxx@ep-cool-name-123.region.aws.neon.tech/agentsetu?sslmode=require
   ```
5. Save as `DATABASE_URL`

> **Neon autosuspend:** free tier suspends compute after 5 min of inactivity. First query after wake takes ~1s. The `/ready` endpoint reconnects automatically.

### Run migrations (optional)

```bash
# From services/api/ with venv activated
export DATABASE_URL="postgresql://...your-neon-url..."
alembic upgrade head
```

Or let the app auto-create tables on first boot (demo/sandbox mode).

---

## Step 2 — Redis (Upstash)

1. Go to **console.upstash.com** → Create a Redis database
2. Name: `agentsetu`. Region: same as Neon
3. TLS: enabled (default)
4. Copy the **Redis URL**:
   ```
   rediss://default:xxx@usw1-cool-name.upstash.io:6379
   ```
   Note: `rediss://` (double-s) for TLS.
5. Save as `REDIS_URL`

> 10K commands/day is plenty for rate limiting and JTI token revocation.

---

## Step 3 — Backend (Render)

### Create the Web Service

1. Go to **dashboard.render.com** → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `agentsetu-api` |
| Region | Same as Neon (e.g., Singapore or Oregon) |
| Branch | `main` |
| Root Directory | `services/api` |
| Runtime | Docker |
| Instance Type | **Free** |

4. Add all **Environment Variables** from the [Environment Reference](#environment-variable-reference) below
5. Click **Create Web Service**

> **Cold starts:** Render free tier spins down after 15 min idle. First request after sleep takes 30–60s. Hit `/health` before your demo to warm it up.

### Alternative: Native Python (if Docker builds are slow)

| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

---

## Step 4 — Frontend (Vercel)

1. Go to **vercel.com** → **New Project** → Import your GitHub repo
2. Configure:

| Setting | Value |
|---------|-------|
| Framework Preset | Next.js (auto-detected) |
| Root Directory | `apps/web` |
| Build Command | `npm run build` (default) |
| Install Command | `npm ci --legacy-peer-deps` |

3. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://agentsetu-api.onrender.com
   ```
4. Click **Deploy**

### After deploy: update backend CORS

Go back to Render and update `CORS_ORIGINS`:
```
CORS_ORIGINS=https://agentsetu.vercel.app
```

---

## Step 5 — Razorpay (Test Mode)

1. Log into **dashboard.razorpay.com**
2. Toggle to **Test Mode** (top-left)
3. **Settings → API Keys → Generate Key**
   - Key ID starts with `rzp_test_`
   - Save the Key Secret immediately (shown once)
4. **Settings → Webhooks → Add New Webhook**
   - URL: `https://agentsetu-api.onrender.com/v1/webhooks/razorpay`
   - Secret: generate one, save as `RAZORPAY_WEBHOOK_SECRET`
   - Events: `payment_link.paid`, `payment_link.expired`, `payment_link.cancelled`

> **No KYC needed for Test Mode.** Full API access immediately.

### Test card numbers

| Card | Number | Result |
|------|--------|--------|
| Mastercard | `5267 3181 8797 5449` | Success |
| Visa | `4111 1111 1111 1111` | Success |
| Any card | CVV: any 3 digits, Expiry: any future date | — |

---

## Step 6 — OpenAI

1. Go to **platform.openai.com → API Keys**
2. Create a new secret key named `agentsetu`
3. Save as `OPENAI_API_KEY`
4. Model: `gpt-4o-mini` (default in config)

> **Cost:** 1–2 API calls per purchase flow. A full demo session (3 flows) costs < $0.01 with gpt-4o-mini.

---

## Step 7 — Sentry (Optional)

1. Go to **sentry.io** → Create a new project (platform: FastAPI)
2. Copy the **DSN** from project settings
3. Save as `SENTRY_DSN` in Render env vars

Leave `SENTRY_DSN` empty to skip Sentry — errors still appear in Render's log viewer.

---

## Environment Variable Reference

### Backend (Render)

| Variable | Value | Required |
|----------|-------|----------|
| `APP_MODE` | `demo` or `sandbox` | Yes |
| `ENVIRONMENT` | `staging` | Yes |
| `DATABASE_URL` | Neon connection string (with `?sslmode=require`) | Yes |
| `REDIS_URL` | Upstash Redis URL (`rediss://...`) | Yes |
| `SECRET_KEY` | Random 64-char hex¹ | Yes |
| `ENCRYPTION_KEY` | Random 64-char hex¹ | Yes |
| `RAZORPAY_KEY_ID` | `rzp_test_...` from Razorpay | Yes |
| `RAZORPAY_KEY_SECRET` | From Razorpay | Yes |
| `RAZORPAY_WEBHOOK_SECRET` | From Razorpay webhook config | Yes |
| `OPENAI_API_KEY` | `sk-...` from OpenAI | Yes |
| `OPENAI_MODEL` | `gpt-4o-mini` | No (default) |
| `BASE_URL` | `https://agentsetu-api.onrender.com` | Yes |
| `CORS_ORIGINS` | `https://agentsetu.vercel.app` | Yes |
| `LOG_FORMAT` | `json` | No |
| `SENTRY_DSN` | Sentry DSN or empty | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | No (default: 1440) |

¹ Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### Frontend (Vercel)

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://agentsetu-api.onrender.com` |

### Demo vs Sandbox Mode

| Feature | `demo` | `sandbox` |
|---------|--------|-----------|
| Auto-seed 3 merchants | ✅ | ❌ |
| OpenAI calls | Fallback if no key | Real API calls |
| Razorpay | Test mode (dummy keys OK) | Test mode (real test keys) |
| /docs endpoint | Enabled | Enabled |
| Best for | Quick demo, hackathon judging | Full prototype with onboarding |

Use `demo` if you want OrganicKart, TechMart, and SpiceWorld pre-seeded. Use `sandbox` to demonstrate the merchant onboarding flow.

---

## Deployment Order Checklist

Follow this order to avoid circular dependencies:

- [ ] **1.** Create Neon database → get `DATABASE_URL`
- [ ] **2.** Create Upstash Redis → get `REDIS_URL`
- [ ] **3.** Create Razorpay Test Mode keys → get key ID, secret, webhook secret
- [ ] **4.** Create OpenAI API key → get `OPENAI_API_KEY`
- [ ] **5.** Generate `SECRET_KEY` and `ENCRYPTION_KEY` locally
- [ ] **6.** Deploy backend to Render with all env vars (use `*` for CORS initially)
- [ ] **7.** Verify backend: `curl https://your-app.onrender.com/health`
- [ ] **8.** Deploy frontend to Vercel with `NEXT_PUBLIC_API_URL`
- [ ] **9.** Update Render `CORS_ORIGINS` to your Vercel URL (remove `*`)
- [ ] **10.** Configure Razorpay webhook URL → your Render service
- [ ] **11.** Run end-to-end smoke test (signup → buy → pay → receipt → audit)
- [ ] **12.** (Optional) Set up Sentry → add `SENTRY_DSN`
- [ ] **13.** (Optional) Set up UptimeRobot (free) to ping `/health` every 5 min

---

## Post-Deployment Verification

### Health checks

```bash
# Liveness
curl https://agentsetu-api.onrender.com/health
# → {"status":"ok","service":"agentsetu-api","version":"1.0.0","mode":"sandbox"}

# Readiness (checks DB)
curl https://agentsetu-api.onrender.com/ready
# → {"status":"ready","checks":{"database":"ok"}}

# OpenAPI docs
open https://agentsetu-api.onrender.com/docs
```

### Production check script

```bash
./scripts/production-check.sh https://agentsetu-api.onrender.com
```

### E2E smoke test

1. Open the Vercel frontend URL
2. Sign up with a test account
3. **Merchant** tab → verify 3 demo merchants (if `APP_MODE=demo`)
4. **Buyer** tab → submit: *"Buy organic honey under ₹500"*
5. Complete Razorpay Test Mode payment with test card
6. **Audit** tab → verify full event timeline

---

## Troubleshooting

### Backend takes 30–60s to respond
Render free tier spins down after 15 min. Hit `/health` before demos. Consider [UptimeRobot](https://uptimerobot.com) (free, 50 monitors) to ping every 5 min.

### Database connection refused
Check `?sslmode=require` in the Neon URL. Neon auto-suspends after 5 min — first query takes ~1s. If you see persistent errors, check 190 compute-hours/month limit.

### CORS errors in browser console
Your Vercel URL must be in `CORS_ORIGINS` on Render. Include full origin: `https://agentsetu.vercel.app`.

### Razorpay webhooks not arriving
Check: (1) webhook URL matches Render URL, (2) service is awake, (3) events enabled in Razorpay settings. Razorpay retries on failure — use their webhook log.

### Razorpay "Invalid Key" error
Ensure you're using **Test Mode** keys (`rzp_test_`). AgentSetu blocks live keys in non-production mode.

### OpenAI calls failing
If `OPENAI_API_KEY` is `sk-demo`, intent parsing returns a zero-confidence fallback. Set a real key for full functionality.

### Render Docker build fails (OOM)
Free tier has 512 MB RAM. Switch to the native Python runtime (see Step 3 alternative).

---

## Cost Summary

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Neon PostgreSQL | Free | ₹0 |
| Upstash Redis | Free | ₹0 |
| Render (Backend) | Free | ₹0 |
| Vercel (Frontend) | Hobby | ₹0 |
| Razorpay | Test Mode | ₹0 |
| Sentry | Developer | ₹0 |
| OpenAI (gpt-4o-mini) | Pay-as-you-go | ~₹0–5* |

**Total: ₹0/month**

*OpenAI: ~₹0.80 per 100 demo sessions. Initial free credits cover thousands of demos.

No credit card required for any service except OpenAI.
