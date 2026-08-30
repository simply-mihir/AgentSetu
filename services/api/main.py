"""
AgentSetu API — The authorization and interoperability layer for agentic commerce.
FastAPI backend serving ARM, discovery, AI buyer, policy engine, and payment routes.
"""
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import create_db_and_tables, engine
from routes import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("agentsetu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AgentSetu API starting up…")
    create_db_and_tables()
    await seed_demo_merchants()
    logger.info("AgentSetu API ready ✓")
    yield
    logger.info("AgentSetu API shutting down")


async def seed_demo_merchants():
    """Seed 3 demo merchants if not already present."""
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
                continue  # Already seeded

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
            logger.info(f"Seeded merchant: {merchant.name}")


app = FastAPI(
    title="AgentSetu API",
    description="The authorization and interoperability layer for agentic commerce",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agentsetu-api", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "name": "AgentSetu API",
        "tagline": "The authorization and interoperability layer for agentic commerce",
        "version": "1.0.0",
        "docs": "/docs",
    }
