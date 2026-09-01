# AgentSetu — Manual Setup Checklist

These tasks require human action (credentials, accounts, external services).
Complete them before production deployment.

---

## 1. Razorpay

- [ ] Complete KYC on Razorpay dashboard
- [ ] Obtain live API keys (`rzp_live_*`)
- [ ] Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in production env
- [ ] Configure webhook URL in Razorpay dashboard → `{BASE_URL}/v1/webhooks/razorpay`
- [ ] Set `RAZORPAY_WEBHOOK_SECRET` from Razorpay webhook settings
- [ ] Enable relevant webhook events: `payment_link.paid`, `payment_link.expired`, `payment_link.cancelled`
- [ ] (Optional) Apply for Razorpay Partner Program for OAuth / connected accounts

## 2. Database

- [ ] Provision PostgreSQL (managed: AWS RDS, Railway, Supabase, or similar)
- [ ] Create database `agentsetu`
- [ ] Set `DATABASE_URL=postgresql://user:pass@host:5432/agentsetu`
- [ ] Run `alembic upgrade head` to initialize schema
- [ ] Verify with `alembic current`

## 3. Redis (Optional but Recommended)

- [ ] Provision Redis instance
- [ ] Set `REDIS_URL=redis://host:6379/0`
- [ ] Required for: production rate limiting, JTI token revocation persistence

## 4. Security Keys

- [ ] Generate `SECRET_KEY`: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] Generate `ENCRYPTION_KEY`: `python3 -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Store in managed secrets (not `.env` file in production)

## 5. OpenAI

- [ ] Obtain production API key from OpenAI
- [ ] Set `OPENAI_API_KEY`
- [ ] Choose model: `gpt-4o-mini` (cost-effective) or `gpt-4o` (higher quality)

## 6. Observability

- [ ] Create Sentry project at sentry.io
- [ ] Set `SENTRY_DSN`
- [ ] Set `LOG_FORMAT=json` for log aggregation
- [ ] Configure log forwarding (CloudWatch, Datadog, etc.)

## 7. Domain & SSL

- [ ] Register/configure domain
- [ ] Set up SSL certificate (Let's Encrypt or managed)
- [ ] Set `BASE_URL=https://api.yourdomain.com`
- [ ] Set `CORS_ORIGINS` to your frontend domain(s)

## 8. Deployment Platform

- [ ] Choose platform: Railway, Render, AWS ECS, GCP Cloud Run, or self-hosted
- [ ] Configure environment variables in platform secrets
- [ ] Set `APP_MODE=production`
- [ ] Set `ENVIRONMENT=production`
- [ ] Deploy and verify with `./scripts/production-check.sh https://api.yourdomain.com`

## 9. Frontend

- [ ] Set `NEXT_PUBLIC_API_URL=https://api.yourdomain.com` in frontend env
- [ ] Deploy frontend (Vercel, Netlify, or same platform)
- [ ] Verify CORS works between frontend and API

## 10. Verification

- [ ] Run `./scripts/production-check.sh https://api.yourdomain.com`
- [ ] All checks pass (no ❌)
- [ ] Create a test account via `/v1/auth/signup`
- [ ] Verify `/health` and `/ready` return 200
- [ ] (When Razorpay live) Perform a ₹1 test transaction end-to-end

## 11. Legal (if applicable)

- [ ] Privacy Policy page
- [ ] Terms of Service page
- [ ] Refund Policy page
- [ ] Cookie consent (if applicable)

## 12. WhatsApp / Meta (Future)

- [ ] Meta Business verification
- [ ] WhatsApp Business API access
- [ ] Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`
