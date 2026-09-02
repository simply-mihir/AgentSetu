"""
Merchant onboarding, ARM generation, and policy management routes.

SECURITY:
- POST /import requires authentication (MERCHANT_OWNER/ADMIN/PLATFORM_ADMIN)
- PUT /{merchant_id}/policy requires authentication with merchant access
- GET / and GET /{merchant_id} are public catalog endpoints
"""
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from pydantic import BaseModel

from database import get_session
from models.merchant import Merchant, Product
from models.user import User, UserRole
from models.merchant_user import MerchantUser
from auth.dependencies import (
    get_current_user, get_optional_user,
    assert_merchant_owner_or_admin, require_role,
)
from arm.generator import get_or_generate_arm
from arm.schema import MerchantImportRequest, PolicyUpdateRequest

router = APIRouter()


class ProductOut(BaseModel):
    product_id: str
    name: str
    category: str
    price_inr: int
    inventory_count: int
    availability: bool
    delivery_sla_days_min: int
    delivery_sla_days_max: int
    return_policy: str
    merchant_rating: float
    description: str


class MerchantOut(BaseModel):
    merchant_id: str
    name: str
    currency: str
    description: str
    category: str
    max_autonomous_spend_inr: int
    approval_threshold_inr: int
    restricted_categories: List[str]
    refund_authority: str
    is_active: bool
    product_count: int


@router.post("/import", summary="Import merchant catalog and generate ARM")
async def import_merchant(
    request: MerchantImportRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Import or update a merchant catalog. Generates ARM automatically.
    C3 FIX: Requires authentication. Only MERCHANT_OWNER, MERCHANT_ADMIN,
    or PLATFORM_ADMIN can import catalogs.
    """
    # Verify the user has permission to manage this merchant
    allowed_roles = {UserRole.MERCHANT_OWNER, UserRole.MERCHANT_ADMIN, UserRole.PLATFORM_ADMIN}
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only merchant owners/admins can import catalogs")

    # For non-PLATFORM_ADMIN, verify merchant access
    if current_user.role != UserRole.PLATFORM_ADMIN:
        # Check if merchant exists and user has access
        existing_merchant = session.exec(
            select(Merchant).where(Merchant.merchant_id == request.merchant_id)
        ).first()
        if existing_merchant:
            assert_merchant_owner_or_admin(request.merchant_id, current_user, session)
        # If merchant doesn't exist yet, creating a new one is allowed for MERCHANT_OWNER

    # Upsert merchant
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == request.merchant_id)
    ).first()

    if not merchant:
        merchant = Merchant(merchant_id=request.merchant_id)

    merchant.name = request.merchant_name
    merchant.currency = request.currency
    merchant.description = request.description
    merchant.category = request.category
    merchant.max_autonomous_spend_inr = request.max_autonomous_spend_inr
    merchant.approval_threshold_inr = request.approval_threshold_inr
    merchant.restricted_categories = json.dumps(request.restricted_categories)
    merchant.updated_at = datetime.utcnow()

    session.add(merchant)
    session.commit()
    session.refresh(merchant)

    # If this is a new merchant and the user is MERCHANT_OWNER, create membership
    if current_user.role in {UserRole.MERCHANT_OWNER, UserRole.MERCHANT_ADMIN}:
        existing_membership = session.exec(
            select(MerchantUser).where(
                MerchantUser.merchant_id == request.merchant_id,
                MerchantUser.user_id == current_user.user_id,
            )
        ).first()
        if not existing_membership:
            from models.merchant_user import MerchantUserRole
            membership = MerchantUser(
                merchant_id=request.merchant_id,
                user_id=current_user.user_id,
                role=MerchantUserRole.OWNER if current_user.role == UserRole.MERCHANT_OWNER else MerchantUserRole.ADMIN,
            )
            session.add(membership)
            session.commit()

    # Import products
    imported, errors = [], []
    for p_data in request.products:
        try:
            required = ["product_id", "name", "price_inr", "category"]
            missing = [f for f in required if f not in p_data]
            if missing:
                errors.append({"product_id": p_data.get("product_id", "?"), "error": f"Missing: {missing}"})
                continue

            existing = session.exec(
                select(Product).where(
                    Product.product_id == p_data["product_id"],
                    Product.merchant_id == request.merchant_id
                )
            ).first()

            if not existing:
                existing = Product(
                    product_id=p_data["product_id"],
                    merchant_id=request.merchant_id
                )

            delivery_days = p_data.get("delivery_sla_days", [1, 3])
            existing.name = p_data["name"]
            existing.category = p_data["category"]
            existing.price_inr = int(p_data["price_inr"])
            existing.inventory_count = p_data.get("inventory_count", 10)
            existing.availability = p_data.get("availability", True)
            existing.delivery_sla_days_min = delivery_days[0] if isinstance(delivery_days, list) else delivery_days
            existing.delivery_sla_days_max = delivery_days[-1] if isinstance(delivery_days, list) else delivery_days
            existing.return_policy = p_data.get("return_policy", "7_days")
            existing.merchant_rating = float(p_data.get("merchant_rating", 4.0))
            existing.description = p_data.get("description", "")
            existing.image_url = p_data.get("image_url", "")
            existing.payment_link_id = p_data.get("payment_link_id")
            existing.updated_at = datetime.utcnow()

            session.add(existing)
            imported.append(p_data["product_id"])
        except Exception as e:
            errors.append({"product_id": p_data.get("product_id", "?"), "error": str(e)})

    session.commit()

    # Generate ARM
    arm = get_or_generate_arm(request.merchant_id, session)

    return {
        "success": True,
        "merchant_id": request.merchant_id,
        "products_imported": len(imported),
        "errors": errors,
        "arm_generated": arm is not None,
    }


@router.get("/", summary="List all merchants")
async def list_merchants(session: Session = Depends(get_session)):
    """Public catalog endpoint — lists active merchants."""
    merchants = session.exec(select(Merchant)).all()
    result = []
    for m in merchants:
        products = session.exec(
            select(Product).where(Product.merchant_id == m.merchant_id)
        ).all()
        result.append({
            "merchant_id": m.merchant_id,
            "name": m.name,
            "currency": m.currency,
            "description": m.description,
            "category": m.category,
            "is_active": m.is_active,
            "product_count": len(products),
        })
    return result


@router.get("/{merchant_id}/arm", summary="Get ARM manifest for a merchant")
async def get_arm(merchant_id: str, session: Session = Depends(get_session)):
    arm = get_or_generate_arm(merchant_id, session)
    if not arm:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return arm.model_dump()


@router.get("/{merchant_id}", summary="Get merchant details")
async def get_merchant(merchant_id: str, session: Session = Depends(get_session)):
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    products = session.exec(
        select(Product).where(Product.merchant_id == merchant_id)
    ).all()

    return {
        "merchant_id": merchant.merchant_id,
        "name": merchant.name,
        "currency": merchant.currency,
        "description": merchant.description,
        "category": merchant.category,
        "max_autonomous_spend_inr": merchant.max_autonomous_spend_inr,
        "approval_threshold_inr": merchant.approval_threshold_inr,
        "restricted_categories": merchant.get_restricted_categories(),
        "refund_authority": merchant.refund_authority,
        "is_active": merchant.is_active,
        "products": [
            {
                "product_id": p.product_id,
                "name": p.name,
                "category": p.category,
                "price_inr": p.price_inr,
                "inventory_count": p.inventory_count,
                "availability": p.availability,
                "delivery_sla_days": [p.delivery_sla_days_min, p.delivery_sla_days_max],
                "return_policy": p.return_policy,
                "merchant_rating": p.merchant_rating,
                "description": p.description,
            }
            for p in products
        ]
    }


@router.put("/{merchant_id}/policy", summary="Update merchant agent policy")
async def update_policy(
    merchant_id: str,
    request: PolicyUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    H2 FIX: Changed from get_optional_user to get_current_user.
    Authentication is ALWAYS required for policy mutation.
    """
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Tenant isolation: only merchant owners/admins may change policy
    assert_merchant_owner_or_admin(merchant_id, current_user, session)

    merchant.max_autonomous_spend_inr = request.max_autonomous_spend_inr
    merchant.approval_threshold_inr = request.approval_threshold_inr
    merchant.set_restricted_categories(request.restricted_categories)
    merchant.refund_authority = request.refund_authority
    merchant.updated_at = datetime.utcnow()

    session.add(merchant)
    session.commit()

    # Regenerate ARM
    get_or_generate_arm(merchant_id, session)

    return {"success": True, "merchant_id": merchant_id, "policy_updated": True}
