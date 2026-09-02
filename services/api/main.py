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
_openapi_tags = [
    {"name": "Auth", "description": "Authentication — signup, login, logout, token management"},
    {"name": "Discovery", "description": "Product and merchant discovery — deterministic registry search"},
    {"name": "Merchants", "description": "Merchant onboarding, ARM manifests, and policy management"},
    {"name": "Transactions", "description": "Transaction orchestration — intent → discovery → ranking → approval"},
    {"name": "Payments", "description": "Payment gate — policy → capability → Razorpay (server-side only)"},
    {"name": "Audit", "description": "Audit trail — every material agent and money action is recorded"},
    {"name": "Webhooks", "description": "Payment provider webhook handlers (Razorpay)"},
    {"name": "Health", "description": "Liveness and readiness probes"},
]

app = FastAPI(
    title="AgentSetu API",
    description=(
        "The authorization and interoperability layer for AI-native agentic commerce.\n\n"
        "**Core invariants:**\n"
        "- LLM NEVER authorizes money movement — deterministic policy is the final gate\n"
        "- Every financial action is auditable and idempotent\n"
        "- Identity is always derived from authenticated context\n"
        "- All errors use the standard `{error: {code, message, request_id, details}}` envelope"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_tags=_openapi_tags,
)

# Rate limiter
app.state.limiter = limiter


# ── Phase 14: Consistent error responses ─────────────────────────────────────
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Phase 14: Rate limit errors in standard error format."""
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": str(exc.detail) if hasattr(exc, "detail") else "Rate limit exceeded",
                "request_id": request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:8]}"),
                "details": {},
            }
        },
    )


async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Phase 14: Normalize all HTTP errors to the standard envelope.
    If detail is already a dict with 'error', pass through. Otherwise wrap it."""
    detail = exc.detail
    request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:8]}")

    if isinstance(detail, dict) and "error" in detail:
        # Already structured — inject request_id if missing
        detail["error"].setdefault("request_id", request_id)
        return JSONResponse(status_code=exc.status_code, content=detail)

    # String detail or other format — wrap
    code = "NOT_FOUND" if exc.status_code == 404 else (
        "FORBIDDEN" if exc.status_code == 403 else (
        "AUTH_REQUIRED" if exc.status_code == 401 else (
        "VALIDATION_ERROR" if exc.status_code in (400, 422) else "SERVER_ERROR"
    )))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(detail),
                "request_id": request_id,
                "details": {},
            }
        },
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    """Phase 14: Pydantic validation errors in standard format."""
    request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:8]}")
    errors = exc.errors()
    message = "; ".join(
        f"{'.'.join(str(l) for l in e.get('loc', []))}: {e.get('msg', 'invalid')}"
        for e in errors
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": message,
                "request_id": request_id,
                "details": {"validation_errors": errors},
            }
        },
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
app.add_exception_handler(RequestValidationError, _validation_exception_handler)

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


# ── Request ID + Security Headers middleware ─────────────────────────────────
@app.middleware("http")
async def add_request_id_and_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:8]}"

    # Phase 14: Request body size limit (1 MB) — reject before processing
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_048_576:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "PAYLOAD_TOO_LARGE",
                    "message": "Request body exceeds 1 MB limit.",
                    "request_id": request_id,
                    "details": {},
                }
            },
        )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    # Phase 14 / Phase 23: Security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"  # disabled; CSP is the real defense
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
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
