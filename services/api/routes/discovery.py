"""Discovery routes — search merchants and products by agent constraints."""
import os
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session, select
from slowapi import Limiter
from slowapi.util import get_remote_address
from database import get_session
from models.merchant import Merchant, Product

router = APIRouter()

# N3 FIX: Rate-limit discovery to prevent DoS via full table scan
_testing = os.environ.get("TESTING", "").lower() in ("1", "true")
_limiter = Limiter(key_func=get_remote_address, enabled=not _testing)


@router.get("/", summary="Search merchants/products by constraints")
@_limiter.limit("30/minute")
async def discover(
    request: Request,
    category: Optional[str] = Query(None, description="Product category"),
    max_price: Optional[int] = Query(None, description="Maximum price in INR"),
    delivery_sla: Optional[int] = Query(None, description="Max delivery days"),
    keyword: Optional[str] = Query(None, description="Product keyword search"),
    merchant_id: Optional[str] = Query(None, description="Filter by merchant"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: Session = Depends(get_session),
):
    """
    Registry discovery. Deterministic filtering — no semantic search.
    Returns products matching all specified constraints.

    H6 PARTIAL FIX: DB-side base filters (availability, inventory, merchant active).
    N7 FIX: Pagination via limit/offset.
    """
    # H6: DB-side base filtering — only load available products with stock
    query = select(Product).where(
        Product.availability.is_(True),
        Product.inventory_count > 0,
    )
    if category:
        query = query.where(Product.category == category)
    if max_price is not None:
        query = query.where(Product.price_inr <= max_price)
    if delivery_sla is not None:
        query = query.where(Product.delivery_sla_days_max <= delivery_sla)
    if merchant_id:
        query = query.where(Product.merchant_id == merchant_id)

    products = session.exec(query).all()

    # Load only active merchants
    active_merchants = session.exec(
        select(Merchant).where(Merchant.is_active.is_(True))
    ).all()
    merchants_map = {m.merchant_id: m for m in active_merchants}

    results = []
    for p in products:
        merchant = merchants_map.get(p.merchant_id)
        if not merchant:
            continue

        # Keyword filter (still in-memory — needs pg_trgm for DB-side full-text)
        if keyword:
            kw = keyword.lower()
            if kw not in p.name.lower() and kw not in p.description.lower() and kw not in p.category.lower():
                continue

        # Check restricted categories
        if p.category.lower() in [r.lower() for r in merchant.get_restricted_categories()]:
            continue

        results.append({
            "product_id": p.product_id,
            "merchant_id": p.merchant_id,
            "merchant_name": merchant.name,
            "name": p.name,
            "category": p.category,
            "price_inr": p.price_inr,
            "inventory_count": p.inventory_count,
            "availability": p.availability,
            "delivery_sla_days_min": p.delivery_sla_days_min,
            "delivery_sla_days_max": p.delivery_sla_days_max,
            "return_policy": p.return_policy,
            "merchant_rating": p.merchant_rating,
            "description": p.description,
            "max_autonomous_spend_inr": merchant.max_autonomous_spend_inr,
            "approval_threshold_inr": merchant.approval_threshold_inr,
        })

    # N7: Pagination
    total = len(results)
    paginated = results[offset:offset + limit]

    return {
        "count": len(paginated),
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": paginated,
        "filters_applied": {
            "category": category,
            "max_price": max_price,
            "delivery_sla": delivery_sla,
            "keyword": keyword,
        }
    }


@router.get("/categories", summary="List all available categories")
async def list_categories(session: Session = Depends(get_session)):
    # N13 FIX: Only load distinct categories from available products
    products = session.exec(
        select(Product.category).where(Product.availability.is_(True))
    ).all()
    categories = sorted(set(products))
    return {"categories": categories}
