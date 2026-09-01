"""ARM manifest generator from merchant DB records."""
from typing import Optional
from sqlmodel import Session, select
from models.merchant import Merchant, Product
from arm.schema import ARMManifest, ARMMerchant, ARMProduct, ARMPolicies


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


def get_or_generate_arm(merchant_id: str, session: Session) -> Optional[ARMManifest]:
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()
    if not merchant:
        return None

    products = session.exec(
        select(Product).where(Product.merchant_id == merchant_id)
    ).all()

    manifest = generate_arm(merchant, list(products))

    # Cache in DB
    merchant.arm_json = manifest.model_dump_json()
    session.add(merchant)
    session.commit()

    return manifest
