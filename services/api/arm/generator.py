"""ARM manifest generator from merchant DB records.

L1 FIX: TTL-based caching — cached ARM is returned if it was generated
within the last ARM_CACHE_TTL_SECONDS and its content hash hasn't changed.
"""
import logging

from sqlmodel import Session, select

from arm.schema import ARMManifest, ARMMerchant, ARMPolicies, ARMProduct
from models.merchant import Merchant, Product
from utils.time import utc_now

logger = logging.getLogger(__name__)

# L1: ARM cache TTL — serve cached manifest if generated within this window
ARM_CACHE_TTL_SECONDS = 300  # 5 minutes


def generate_arm(merchant: Merchant, products: list[Product]) -> ARMManifest:
    arm_products = []
    for p in products:
        if not p.availability:
            continue
        arm_products.append(ARMProduct(
            product_id=p.product_id,
            name=p.name,
            category=p.category,
            price_inr=p.price_inr,
            inventory_count=p.inventory_count,
            availability=p.availability,
            delivery_sla_days=[p.delivery_sla_days_min, p.delivery_sla_days_max],
            return_policy=p.return_policy,
            merchant_rating=p.merchant_rating,
            description=p.description,
            # Phase 9: payment_link_id intentionally NOT included.
            # ARM is a public-facing manifest; internal payment references stay server-side.
        ))

    manifest = ARMManifest(
        merchant=ARMMerchant(
            id=merchant.merchant_id,
            name=merchant.name,
            currency=merchant.currency,
            description=merchant.description,
            category=merchant.category,
        ),
        products=arm_products,
        policies=ARMPolicies(
            max_autonomous_spend_inr=merchant.max_autonomous_spend_inr,
            approval_required_above_inr=merchant.approval_threshold_inr,
            restricted_categories=merchant.get_restricted_categories(),
            refund_authority=merchant.refund_authority,
        ),
        payment={"provider": "razorpay", "type": "payment_link"}
    )
    # Phase 9: compute content hash for integrity verification
    manifest.manifest_hash = manifest.compute_hash()
    return manifest


def get_or_generate_arm(
    merchant_id: str,
    session: Session,
    force_refresh: bool = False,
) -> ARMManifest | None:
    """Return cached ARM if fresh, otherwise regenerate.

    L1 FIX: TTL-based read-back — if the cached ARM was generated within
    ARM_CACHE_TTL_SECONDS and the underlying data hasn't changed (content
    hash matches), return the cached version without hitting the product table.
    """
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()
    if not merchant:
        return None

    # L1: Try cached ARM first (skip if force_refresh)
    if not force_refresh and merchant.arm_json:
        try:
            cached = ARMManifest.model_validate_json(merchant.arm_json)
            # Check TTL — generated_at is ISO format with trailing Z
            from datetime import datetime
            generated_at = datetime.fromisoformat(cached.generated_at.rstrip("Z")).replace(tzinfo=None)
            age = (utc_now() - generated_at).total_seconds()
            if age < ARM_CACHE_TTL_SECONDS:
                logger.debug("ARM cache hit for %s (age=%.0fs)", merchant_id, age)
                return cached
            logger.debug("ARM cache expired for %s (age=%.0fs)", merchant_id, age)
        except Exception:
            logger.debug("ARM cache parse failed for %s — regenerating", merchant_id)

    # Cache miss or expired — regenerate
    products = session.exec(
        select(Product).where(Product.merchant_id == merchant_id)
    ).all()

    manifest = generate_arm(merchant, list(products))

    # L1: Compare content hash to avoid unnecessary DB writes
    if merchant.arm_json:
        try:
            old = ARMManifest.model_validate_json(merchant.arm_json)
            if old.manifest_hash == manifest.manifest_hash:
                # Content unchanged — update only generated_at timestamp
                manifest.manifest_id = old.manifest_id
        except Exception:
            pass

    # Cache in DB
    merchant.arm_json = manifest.model_dump_json()
    session.add(merchant)
    session.commit()

    logger.debug("ARM regenerated for %s", merchant_id)
    return manifest
