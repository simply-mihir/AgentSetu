"""Discovery routes — search merchants and products by agent constraints."""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from database import get_session
from models.merchant import Merchant, Product

router = APIRouter()


@router.get("/", summary="Search merchants/products by constraints")
async def discover(
    category: Optional[str] = Query(None, description="Product category"),
    max_price: Optional[int] = Query(None, description="Maximum price in INR"),
    delivery_sla: Optional[int] = Query(None, description="Max delivery days"),
    keyword: Optional[str] = Query(None, description="Product keyword search"),
    merchant_id: Optional[str] = Query(None, description="Filter by merchant"),
    session: Session = Depends(get_session),
):
    """
    Registry discovery. Deterministic filtering — no semantic search.
    Returns products matching all specified constraints.
    """
    products = session.exec(select(Product)).all()
    merchants_map = {}
    all_merchants = session.exec(select(Merchant)).all()
    for m in all_merchants:
        merchants_map[m.merchant_id] = m

    results = []
    for p in products:
        merchant = merchants_map.get(p.merchant_id)
        if not merchant or not merchant.is_active:
            continue
        if not p.availability:
            continue
        if p.inventory_count <= 0:
            continue

        # Category filter
        if category and p.category.lower() != category.lower():
            continue

        # Max price filter
        if max_price is not None and p.price_inr > max_price:
            continue

        # Delivery SLA filter
        if delivery_sla is not None and p.delivery_sla_days_max > delivery_sla:
            continue

        # Keyword filter
        if keyword:
            kw = keyword.lower()
            if kw not in p.name.lower() and kw not in p.description.lower() and kw not in p.category.lower():
                continue

        # Merchant filter
        if merchant_id and p.merchant_id != merchant_id:
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

    return {
        "count": len(results),
        "results": results,
        "filters_applied": {
            "category": category,
            "max_price": max_price,
            "delivery_sla": delivery_sla,
            "keyword": keyword,
        }
    }


@router.get("/categories", summary="List all available categories")
async def list_categories(session: Session = Depends(get_session)):
    products = session.exec(select(Product)).all()
    categories = sorted(set(p.category for p in products if p.availability))
    return {"categories": categories}
