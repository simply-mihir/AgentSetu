"""
AgentSetu API — The authorization and interoperability layer for agentic commerce.
"""
import json
import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import settings
from database import create_db_and_tables, engine
from routes import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("agentsetu")

# ── Rate limiter ──────────────────────────────────────────────────────────────
import os as _os
_testing = _os.environ.get("TESTING", "").lower() in ("1", "true")
limiter = Limiter(key_func=get_remote_address, enabled=not _testing)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"AgentSetu API starting — mode={settings.app_mode} env={settings.environment}")
    create_db_and_tables()

    if settings.is_production:
        issues = settings.validate_production()
        if issues:
            for issue in issues:
                logger.error(f"Production config issue: {issue}")
            raise RuntimeError(f"Production config validation failed: {issues}")

    # Seed demo merchants only in demo mode
    if settings.is_demo:
        await seed_demo_merchants()

    logger.info("AgentSetu API ready ✓")
    yield
    logger.info("AgentSetu API shutting down")


async def seed_demo_merchants():
    """Seed 3 demo merchants only if not already present. Demo mode only."""
    import os
    from sqlmodel import Session, select
    from models.merchant import Merchant, Product
    from arm.generator import get_or_generate_arm

    seed_file = os.path.join(os.path.dirname(__file__), "data", "seed_merchants.json")
    if not os.path.exists(seed_file):
        logger.warning("Seed file not found — skipping demo seed")
        return

    with open(seed_file) as f:
        merchants_data = json.load(f)

    with Session(engine) as session:
        for m_data in merchants_data:
            existing = session.exec(
                select(Merchant).where(Merchant.merchant_id == m_data["merchant_id"])
            ).first()
            if existing:
                continue

            merchant = Merchant(
                merchant_id=m_data["merchant_id"],
                name=m_data["merchant_name"],
                currency=m_data.get("currency", "INR"),
                description=m_data.get("description", ""),
                category=m_data.get("category", ""),
                max_autonomous_spend_inr=m_data.get("max_autonomous_spend_inr", 500),
                approval_threshold_inr=m_data.get("approval_threshold_inr", 1500),
                restricted_categories=json.dumps(m_data.get("restricted_categories", [])),
            )
            session.add(merchant)
            session.commit()

            for p_data in m_data.get("products", []):
                delivery = p_data.get("delivery_sla_days", [1, 3])
                product = Product(
                    product_id=p_data["product_id"],
                    merchant_id=merchant.merchant_id,
                    name=p_data["name"],
                    category=p_data["category"],
                    price_inr=int(p_data["price_inr"]),
                    inventory_count=p_data.get("inventory_count", 10),
                    availability=p_data.get("availability", True),
                    delivery_sla_days_min=delivery[0] if isinstance(delivery, list) else delivery,
                    delivery_sla_days_max=delivery[-1] if isinstance(delivery, list) else delivery,
                    return_policy=p_data.get("return_policy", "7_days"),
                    merchant_rating=float(p_data.get("merchant_rating", 4.0)),
                    description=p_data.get("description", ""),
                )
                session.add(product)

            session.commit()
            get_or_generate_arm(merchant.merchant_id, session)
            logger.info(f"[DEMO] Seeded merchant: {merchant.name}")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AgentSetu API",
    description="The authorization and interoperability layer for agentic commerce",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restricted to configured origins only (no wildcard in production)
allowed_origins = settings.cors_origins_list
if not settings.is_production:
    allowed_origins.append("*")  # Allow all for local dev only

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Razorpay-Signature", "Idempotency-Key"],
)


# ── Request ID middleware ─────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:8]}"
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/v1")


# ── Health endpoints ──────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "agentsetu-api",
        "version": "1.0.0",
        "mode": settings.app_mode,
    }


@app.get("/ready", tags=["Health"])
async def ready():
    """Readiness probe — checks DB connectivity."""
    from sqlmodel import Session, text
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    is_ready = db_status == "ok"
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": {"database": db_status},
        },
    )


@app.get("/", tags=["Health"])
async def root():
    return {
        "name": "AgentSetu API",
        "tagline": "The authorization and interoperability layer for agentic commerce",
        "version": "1.0.0",
        "mode": settings.app_mode,
        "docs": "/docs",
    }
