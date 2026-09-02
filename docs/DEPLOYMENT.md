# AgentSetu — Free-Tier Deployment Guide

> Deploy the full AgentSetu prototype — backend, frontend, database, Redis, payments, AI, and observability — at **₹0/month** using only free tiers and Razorpay Test Mode.
>
> Time: ~45 minutes.

---

## Architecture

```
                    ┌──────────────────┐
                    │   Vercel (Free)   │
                    │   Next.js 14      │
                    └────────┬─────────┘
                             │  HTTPS
                             ▼
                    ┌──────────────────┐
                    │  Render (Free)    │
                    │  FastAPI + Uvi    │
                    └───┬────┬─────┬───┘
                        │    │     │
            ┌───────────┘    │     └───────────┐
            ▼                ▼                  ▼
   ┌──────────────┐ ┌───────────────┐ ┌──────────────┐
   │  Supabase    │ │ Upstash (Free)│ │ Sentry (Free)│
   │  PostgreSQL  │ │ Redis         │ │ Errors       │
   │  (Free)      │ └───────────────┘ └──────────────┘
   └──────────────┘
                    ┌──────────────────┐
                    │  Razorpay        │
                    │  Test Mode       │
                    └──────────────────┘
                    ┌──────────────────┐
                    │  Groq (Free)     │
                    │  Llama 3.3 70B   │
                    └──────────────────┘
```

---

## Free-Tier Service Map

| Component | Provider | Free Tier Limits | Credit Card? |
|-----------|----------|-----------------|-------------|
| **Database** | Supabase PostgreSQL 15 | 500 MB storage, 2 projects, no expiry | No |
| **Redis** | Upstash | 10K commands/day, 256 MB | No |
| **Backend** | Render Web Service | 750 hours/mo, spins down after 15 min idle | No |
| **Frontend** | Vercel Hobby | 100 GB bandwidth, automatic HTTPS, Edge CDN | No |
| **Payments** | Razorpay Test Mode | Unlimited test transactions, no KYC needed | No |
| **AI / LLM** | Groq | 30 req/min, 14.4K tokens/min (Llama 3.3 70B) | No |
| **Errors** | Sentry Developer | 5K errors/mo, 30-day retention | No |

**Why these providers?**

- **Supabase** over Neon — 500 MB (vs 0.5 GB), no compute-hour limit, built-in dashboard, direct PostgreSQL connection string
- **Groq** over OpenAI — completely free (no credit card), OpenAI-compatible API (same Python SDK, just different base URL), Llama 3.3 70B matches gpt-4o-mini quality for intent parsing
- **Upstash** over self-hosted Redis — serverless, no container needed
- **Render** over Railway — no credit card required for free tier
- **Vercel** — natural home for Next.js

---

## Accounts to Create

Sign up for all of these before starting. **None require a credit card.**

- [ ] **GitHub** — you likely have this. Required for Render and Vercel deploys.
- [ ] **Supabase** — [supabase.com](https://supabase.com) — sign up with GitHub
- [ ] **Upstash** — [upstash.com](https://upstash.com) — sign up with GitHub
- [ ] **Render** — [render.com](https://render.com) — sign up with GitHub
- [ ] **Vercel** — [vercel.com](https://vercel.com) — sign up with GitHub
- [ ] **Razorpay** — [dashboard.razorpay.com](https://dashboard.razorpay.com) — sign up with email
- [ ] **Groq** — [console.groq.com](https://console.groq.com) — sign up with GitHub or Google
- [ ] **Sentry** (optional) — [sentry.io](https://sentry.io) — sign up with GitHub

---

## Step 1 — Database (Supabase PostgreSQL)

1. Go to **supabase.com** → **New project**
2. Organization: create one (or use existing)
3. Configure:
   - **Name:** `agentsetu`
   - **Database Password:** generate a strong password and **save it** — you need it for the connection string
   - **Region:** pick the one closest to your Render region (e.g., `ap-south-1` Mumbai, or `us-west-1` N. California)
   - **Plan:** Free
4. Wait for the project to finish provisioning (~2 minutes)
5. Go to **Settings → Database → Connection string → URI**
6. Select **Mode: Session** (for connection pooler compatibility)
7. Copy the connection string. It looks like:

```
postgresql://postgres.abcdefghijk:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

Replace `[YOUR-PASSWORD]` with the password you set in step 3.

8. Save this as your `DATABASE_URL`

> **Important:** Use the **Session mode** (port `6543`) connection string, not the direct connection (port `5432`). Session mode goes through Supabase's connection pooler, which handles idle connection cleanup — important for a free-tier backend that sleeps and wakes.

### Run migrations (optional)

You can run Alembic migrations locally against the Supabase database, or let the app auto-create tables on first boot (demo/sandbox mode calls `create_db_and_tables()`).

```bash
# From services/api/ with your venv activated
export DATABASE_URL="postgresql://postgres.abcdefghijk:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
alembic upgrade head
```

### Supabase free tier limits

| Resource | Limit |
|----------|-------|
| Storage | 500 MB |
| Bandwidth | 5 GB |
| Projects | 2 |
| Edge functions | 500K invocations/mo |
| Pause after inactivity | 7 days (you can unpause from dashboard) |

> **Auto-pause:** Supabase pauses free projects after 7 days of no API requests. The prototype's regular use prevents this. If it pauses, unpause from the Supabase dashboard (takes ~1 minute).

---

## Step 2 — Redis (Upstash)

1. Go to **console.upstash.com** → Create a new **Redis** database
2. Name: `agentsetu`. Region: same as your Supabase project
3. Select **TLS** enabled (default)
4. Copy the **Redis URL** from the dashboard. Format:

```
rediss://default:AbCdEf123@usw1-cool-name-12345.upstash.io:6379
```

**Note:** it's `rediss://` (double-s) for TLS.

5. Save this as your `REDIS_URL`

> 10K commands/day is more than enough. AgentSetu uses Redis only for rate limiting and JTI token revocation — lightweight operations.

---

## Step 3 — LLM (Groq — Free)

Groq provides a **completely free** LLM API with an OpenAI-compatible interface. No credit card, no trial expiry. AgentSetu's OpenAI SDK talks to Groq by simply changing the base URL.

1. Go to **console.groq.com** → **API Keys** → **Create API Key**
2. Name: `agentsetu`
3. Copy the key (starts with `gsk_`)
4. Save these three values for your Render env vars:

```
OPENAI_API_KEY=gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile
```

### How it works

The `openai` Python SDK accepts a `base_url` parameter. AgentSetu reads `OPENAI_BASE_URL` from the environment — when set to Groq's endpoint, all LLM calls go to Groq instead of OpenAI. Same SDK, same JSON mode, same structured output — different (free) provider.

### Groq free tier limits

| Model | Requests/min | Tokens/min | Tokens/day |
|-------|-------------|-----------|-----------|
| `llama-3.3-70b-versatile` | 30 | 14,400 | 1,000,000 |
| `llama-3.1-8b-instant` | 30 | 131,072 | 1,000,000 |
| `mixtral-8x7b-32768` | 30 | 14,400 | 1,000,000 |

**Recommended:** `llama-3.3-70b-versatile` — best quality for intent parsing and comparison generation. Falls back gracefully on rate limits.

> **Switching back to OpenAI later:** remove `OPENAI_BASE_URL` (or set it to empty), change `OPENAI_API_KEY` to your OpenAI key, and set `OPENAI_MODEL` to `gpt-4o-mini`. No code changes needed.

---

## Step 4 — Backend (Render)

### Push your code to GitHub

Render deploys from a GitHub repo. Make sure your AgentSetu repo is pushed and up to date.

### Create the Web Service

1. Go to **dashboard.render.com** → **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `agentsetu-api` |
| Region | Same as Supabase (e.g., Singapore or Oregon) |
| Branch | `main` |
| Root Directory | `services/api` |
| Runtime | Docker |
| Instance Type | **Free** |

4. Under **Environment Variables**, add every variable from the [Environment Reference](#environment-variable-reference) table below
5. Click **Create Web Service**

Render builds the Docker image and starts the API. First deploy takes 3–5 minutes.

> **Cold starts:** Render free tier spins down after 15 min of inactivity. The first request after sleep takes 30–60 seconds while Docker boots. Hit `/health` a minute before your demo to warm it up.

### Alternative: Native Python (if Docker builds are slow)

If the free tier OOMs during Docker build (512 MB RAM limit), use the native Python runtime:

| Setting | Value |
|---------|-------|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

---

## Step 5 — Frontend (Vercel)

1. Go to **vercel.com** → **New Project** → Import your GitHub repo
2. Configure:

| Setting | Value |
|---------|-------|
| Framework Preset | Next.js (auto-detected) |
| Root Directory | `apps/web` |
| Build Command | `npm run build` (default) |
| Install Command | `npm ci --legacy-peer-deps` |

3. Add the environment variable:

```
NEXT_PUBLIC_API_URL=https://agentsetu-api.onrender.com
```

Replace with your actual Render URL.

4. Click **Deploy**

Vercel builds and serves the Next.js app at `your-project.vercel.app`.

### After deploy: update backend CORS

Go back to Render and update the `CORS_ORIGINS` env var:

```
CORS_ORIGINS=https://agentsetu.vercel.app
```

---

## Step 6 — Razorpay (Test Mode)

1. Log into **dashboard.razorpay.com**
2. Ensure the toggle at the top-left says **Test Mode** (not Live Mode)
3. Go to **Settings → API Keys → Generate Key**
   - Key ID starts with `rzp_test_`
   - Key Secret — **save it immediately**, it's shown only once
4. Go to **Settings → Webhooks → Add New Webhook**
   - **Webhook URL:** `https://agentsetu-api.onrender.com/v1/webhooks/razorpay`
   - **Secret:** generate one and save as `RAZORPAY_WEBHOOK_SECRET`
   - **Events:** check `payment_link.paid`, `payment_link.expired`, `payment_link.cancelled`
   - **Active:** Yes

> **No KYC needed for Test Mode.** Razorpay provides full API access immediately. Test transactions use simulated card numbers.

### Test card numbers

| Card | Number | Expiry | CVV | Result |
|------|--------|--------|-----|--------|
| Mastercard | `5267 3181 8797 5449` | Any future | Any 3 digits | Success |
| Visa | `4111 1111 1111 1111` | Any future | Any 3 digits | Success |

---

## Step 7 — Sentry (Optional)

1. Go to **sentry.io** → Create a new project (platform: FastAPI)
2. Copy the **DSN** from project settings
3. Save as `SENTRY_DSN` in Render env vars

Leave `SENTRY_DSN` empty to skip Sentry. Errors still appear in Render's log viewer.

---

## Environment Variable Reference

### Backend (Render)

Set all of these in Render's **Environment** tab.

| Variable | Value | Required |
|----------|-------|----------|
| `APP_MODE` | `demo` or `sandbox` | ✅ |
| `ENVIRONMENT` | `staging` | ✅ |
| `DATABASE_URL` | Supabase connection string (Session mode, port 6543) | ✅ |
| `REDIS_URL` | Upstash Redis URL (`rediss://...`) | ✅ |
| `SECRET_KEY` | Random 64-char hex ¹ | ✅ |
| `ENCRYPTION_KEY` | Random 64-char hex ¹ | ✅ |
| `RAZORPAY_KEY_ID` | `rzp_test_...` from Razorpay | ✅ |
| `RAZORPAY_KEY_SECRET` | From Razorpay | ✅ |
| `RAZORPAY_WEBHOOK_SECRET` | From Razorpay webhook config | ✅ |
| `OPENAI_API_KEY` | `gsk_...` from Groq | ✅ |
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` | ✅ |
| `OPENAI_MODEL` | `llama-3.3-70b-versatile` | ✅ |
| `BASE_URL` | `https://agentsetu-api.onrender.com` | ✅ |
| `CORS_ORIGINS` | Your Vercel URL (e.g. `https://agentsetu.vercel.app`) | ✅ |
| `LOG_FORMAT` | `json` | No |
| `SENTRY_DSN` | Sentry DSN or empty | No |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | No (default) |

¹ Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"`

### Frontend (Vercel)

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://agentsetu-api.onrender.com` |

---

## Demo vs Sandbox Mode

| Feature | `demo` | `sandbox` |
|---------|--------|-----------|
| Auto-seed 3 merchants (OrganicKart, TechMart, SpiceWorld) | ✅ | ❌ |
| LLM calls | Real API calls | Real API calls |
| Razorpay | Test mode | Test mode |
| Database | SQLite or PostgreSQL | PostgreSQL expected |
| `/docs` endpoint | Enabled | Enabled |
| Best for | Hackathon judging (data ready on boot) | Full demo with merchant onboarding |

**Recommendation for hackathon:** use `APP_MODE=demo`. The 3 seed merchants populate automatically on first boot, so judges see a working catalog immediately.

---

## Deployment Order Checklist

Follow this exact order to avoid circular dependency issues:

- [ ] **1.** Create Supabase project → get `DATABASE_URL` (Session mode, port 6543)
- [ ] **2.** Create Upstash Redis → get `REDIS_URL`
- [ ] **3.** Create Razorpay Test Mode keys → get key ID, secret, webhook secret
- [ ] **4.** Create Groq API key → get `OPENAI_API_KEY`
- [ ] **5.** Generate `SECRET_KEY` and `ENCRYPTION_KEY` locally:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] **6.** Deploy backend to Render with all env vars (use `*` for `CORS_ORIGINS` initially)
- [ ] **7.** Verify backend: `curl https://your-app.onrender.com/health`
- [ ] **8.** Deploy frontend to Vercel with `NEXT_PUBLIC_API_URL` pointing to Render
- [ ] **9.** Update Render `CORS_ORIGINS` to your Vercel URL (remove `*`)
- [ ] **10.** Configure Razorpay webhook URL → your Render service URL
- [ ] **11.** Run end-to-end smoke test (signup → buy → pay → receipt → audit)
- [ ] **12.** (Optional) Set up Sentry → add `SENTRY_DSN` to Render
- [ ] **13.** (Optional) Set up UptimeRobot free (50 monitors) to ping `/health` every 5 min to reduce cold starts

---

## Post-Deployment Verification

### Health checks

```bash
# Liveness
curl https://agentsetu-api.onrender.com/health
# → {"status":"ok","service":"agentsetu-api","version":"1.0.0","mode":"demo"}

# Readiness (checks DB connection)
curl https://agentsetu-api.onrender.com/ready
# → {"status":"ready","checks":{"database":"ok"}}

# OpenAPI docs (available in demo/sandbox mode)
open https://agentsetu-api.onrender.com/docs
```

### Production check script

```bash
./scripts/production-check.sh https://agentsetu-api.onrender.com
```

### E2E smoke test

1. Open your Vercel frontend URL in a browser
2. Sign up with a test account (any email/password)
3. **Merchant** tab → verify the 3 demo merchants appear (if `APP_MODE=demo`)
4. **Buyer** tab → type: *"Buy organic honey under ₹500"*
5. Complete the Razorpay Test Mode payment with test card `5267 3181 8797 5449`
6. Check the **Audit** tab → verify the complete event timeline

---

## Webhook Configuration

Razorpay sends payment status updates to your backend. This is critical for the payment state machine.

### Configuration in Razorpay Dashboard

```
URL:     https://agentsetu-api.onrender.com/v1/webhooks/razorpay
Secret:  (your generated webhook secret)
Events:
  ✓ payment_link.paid
  ✓ payment_link.expired
  ✓ payment_link.cancelled
```

### Flow

```
Buyer completes payment on Razorpay page
  ↓
Razorpay POST → /v1/webhooks/razorpay
  ↓
HMAC signature verified
  ↓
Transaction: PAYMENT_LINK_CREATED → PAYMENT_SUCCESS
  ↓
Receipt generated + audit event logged
```

> **Cold start risk:** if the Render service is asleep when Razorpay sends a webhook, the request may time out. Razorpay retries failed webhooks automatically, so the second attempt succeeds after the service wakes. For your demo, warm the service beforehand.

---

## Troubleshooting

### Backend takes 30–60s to respond

Render free tier spins down after 15 min idle. Hit `/health` before demos. Set up [UptimeRobot](https://uptimerobot.com) (free, 50 monitors) to ping every 5 min.

### "connection refused" or database errors

- Check that your Supabase connection string uses **Session mode** (port `6543`), not direct (port `5432`)
- Supabase pauses free projects after 7 days of no API requests — unpause from the Supabase dashboard
- If switching from SQLite to PostgreSQL, the first boot creates all tables automatically in demo/sandbox mode

### CORS errors in browser console

Your Vercel URL must be in `CORS_ORIGINS` on Render. Include the full origin with protocol: `https://agentsetu.vercel.app`. Render redeploys automatically after env var changes.

### Razorpay webhooks not arriving

1. Webhook URL must match your Render URL exactly
2. Service must be awake (warm it first)
3. Events must be enabled in Razorpay webhook settings
4. Check Razorpay's webhook delivery log for retry status

### Razorpay "Invalid Key" error

Ensure you're using **Test Mode** keys (start with `rzp_test_`). AgentSetu blocks live keys (`rzp_live_`) in non-production mode as a safety measure.

### Groq LLM errors or rate limits

- Verify `OPENAI_BASE_URL` is exactly `https://api.groq.com/openai/v1`
- Check your API key starts with `gsk_`
- If hitting 30 req/min limit during heavy demo use, switch model to `llama-3.1-8b-instant` (higher rate limits, slightly lower quality)
- If Groq is down, you can switch to OpenAI by removing `OPENAI_BASE_URL` and setting an OpenAI key

### Render Docker build fails (OOM)

Free tier has 512 MB RAM. Switch to the native Python runtime:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Cost Summary

| Service | Tier | Monthly Cost |
|---------|------|-------------|
| Supabase PostgreSQL | Free | ₹0 |
| Upstash Redis | Free | ₹0 |
| Render (Backend) | Free | ₹0 |
| Vercel (Frontend) | Hobby | ₹0 |
| Razorpay | Test Mode | ₹0 |
| Groq (LLM) | Free | ₹0 |
| Sentry | Developer | ₹0 |

### **Total: ₹0/month**

No credit card required for any service. Every component runs on a genuinely free tier with no trial expiry.

---

## Switching Providers Later

The architecture is provider-agnostic. To switch any component:

| Want to switch | Change |
|---------------|--------|
| Groq → OpenAI | Remove `OPENAI_BASE_URL`, set OpenAI key, model = `gpt-4o-mini` |
| Groq → Together AI | `OPENAI_BASE_URL=https://api.together.xyz/v1`, Together key |
| Supabase → Neon | Change `DATABASE_URL` to Neon connection string |
| Supabase → Railway Postgres | Change `DATABASE_URL` to Railway connection string |
| Upstash → Railway Redis | Change `REDIS_URL` to Railway Redis URL |
| Render → Railway | Same Docker image, different platform |

No code changes needed for any of these — just environment variables.
