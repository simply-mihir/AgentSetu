"""
Transaction orchestration routes.
Buyer intent → discovery → ranking → policy → approval → payment.
"""
import json
import hashlib
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models.merchant import Merchant, Product
from models.transaction import Transaction, TransactionState
from policy.engine import PolicyEngine, PolicyDecision
from ai.orchestrator import buyer_orchestrator
from audit.service import audit_service

router = APIRouter()
policy_engine = PolicyEngine()


class IntentRequest(BaseModel):
    message: str
    buyer_limit_inr: Optional[int] = None
    session_id: Optional[str] = None


class SelectProductRequest(BaseModel):
    transaction_id: str
    product_id: str
    merchant_id: str


class ApproveRequest(BaseModel):
    transaction_id: str
    approved_by: str = "buyer"


class EvaluatePolicyRequest(BaseModel):
    merchant_id: str
    product_id: str
    amount_inr: int
    buyer_limit_inr: Optional[int] = None
    is_approved: bool = False


def make_fingerprint(merchant_id: str, product_id: str, amount: int, approval_id: str) -> str:
    payload = f"{merchant_id}:{product_id}:{amount}:{approval_id}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


@router.post("/intent", summary="Process buyer intent — discover + rank products")
async def process_intent(
    request: IntentRequest,
    session: Session = Depends(get_session),
):
    """
    Full buyer intent pipeline:
    1. Parse natural language → structured constraints
    2. Query registry with constraints
    3. Score and rank candidates
    4. Create transaction record
    5. Generate explanation
    """
    # ── 1. Parse intent ──────────────────────────────────────────────────────
    constraints = buyer_orchestrator.parse_intent(request.message)

    # ── 2. Registry discovery ────────────────────────────────────────────────
    all_products = session.exec(select(Product)).all()
    all_merchants = {
        m.merchant_id: m
        for m in session.exec(select(Merchant)).all()
    }

    candidates = []
    for p in all_products:
        merchant = all_merchants.get(p.merchant_id)
        if not merchant or not merchant.is_active or not p.availability or p.inventory_count <= 0:
            continue

        # Restricted category check
        if p.category.lower() in [r.lower() for r in merchant.get_restricted_categories()]:
            continue

        # Apply constraints
        max_budget = constraints.get("max_budget_inr")
        if max_budget and p.price_inr > max_budget:
            continue

        sla = constraints.get("delivery_sla_days")
        if sla and p.delivery_sla_days_max > sla:
            continue

        category = constraints.get("category")
        if category and p.category.lower() != category.lower():
            continue

        keywords = constraints.get("keywords", [])
        if keywords:
            matched = any(
                kw.lower() in p.name.lower() or kw.lower() in p.description.lower()
                for kw in keywords
            )
            if not matched:
                # Still include with lower score if category matches
                pass

        candidates.append({
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

    # ── 3. Score and rank ────────────────────────────────────────────────────
    ranked = buyer_orchestrator.score_candidates(candidates, constraints)

    # ── 4. Create transaction ─────────────────────────────────────────────────
    txn = Transaction(
        buyer_intent=request.message,
        parsed_constraints=json.dumps(constraints),
        candidates_json=json.dumps(ranked[:5]),
        state=TransactionState.DRAFT,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    # ── 5. Audit: intent received ─────────────────────────────────────────────
    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="buyer",
        event_type="intent.received",
        input_summary={"message": request.message, "buyer_limit_inr": request.buyer_limit_inr},
        next_state="DRAFT",
        result="parsed",
    )

    # ── 6. Audit: catalog discovered ──────────────────────────────────────────
    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="agentsetu",
        event_type="catalog.discovered",
        input_summary={"constraints": constraints, "candidates_found": len(candidates)},
        result=f"{len(ranked)} products matched",
    )

    top = ranked[:3] if ranked else []
    explanation = ""
    if top:
        explanation = buyer_orchestrator.generate_comparison(
            candidates=top,
            constraints=constraints,
            selected_product=top[0],
        )

        # ── 7. Audit: recommendation made ────────────────────────────────────
        audit_service.record(
            session=session,
            transaction_id=txn.transaction_id,
            correlation_id=txn.correlation_id,
            actor="agentsetu",
            event_type="recommendation.made",
            input_summary={
                "selected": top[0].get("name") if top else None,
                "merchant": top[0].get("merchant_name") if top else None,
            },
            result="recommendation_generated",
        )

    return {
        "transaction_id": txn.transaction_id,
        "correlation_id": txn.correlation_id,
        "state": txn.state,
        "constraints": constraints,
        "candidates": top,
        "total_found": len(ranked),
        "explanation": explanation,
        "no_results": len(ranked) == 0,
        "relaxation_hint": (
            f"No products found. Try raising your budget to ₹{(constraints.get('max_budget_inr') or 0) + 100} "
            f"or extending delivery to {(constraints.get('delivery_sla_days') or 3) + 1} days."
            if not ranked else None
        ),
    }


@router.post("/select", summary="Select a product from candidates")
async def select_product(
    request: SelectProductRequest,
    session: Session = Depends(get_session),
):
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == request.transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    product = session.exec(
        select(Product).where(
            Product.product_id == request.product_id,
            Product.merchant_id == request.merchant_id,
        )
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == request.merchant_id)
    ).first()

    txn.product_id = product.product_id
    txn.product_name = product.name
    txn.merchant_id = merchant.merchant_id
    txn.merchant_name = merchant.name
    txn.amount_inr = product.price_inr
    txn.state = TransactionState.PENDING_APPROVAL
    txn.updated_at = datetime.utcnow()

    session.add(txn)
    session.commit()
    session.refresh(txn)

    return {
        "transaction_id": txn.transaction_id,
        "state": txn.state,
        "selected": {
            "product_id": product.product_id,
            "name": product.name,
            "merchant_name": merchant.name,
            "price_inr": product.price_inr,
            "delivery_sla_days": [product.delivery_sla_days_min, product.delivery_sla_days_max],
        }
    }


@router.post("/policy/evaluate", summary="Evaluate policy for a proposed transaction")
async def evaluate_policy(
    request: EvaluatePolicyRequest,
    session: Session = Depends(get_session),
):
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == request.merchant_id)
    ).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    product = session.exec(
        select(Product).where(
            Product.product_id == request.product_id,
            Product.merchant_id == request.merchant_id,
        )
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    result = policy_engine.evaluate(
        merchant=merchant,
        product=product,
        amount_inr=request.amount_inr,
        buyer_limit_inr=request.buyer_limit_inr,
        is_approved=request.is_approved,
    )

    return {
        "decision": result.decision,
        "reason_codes": result.reason_codes,
        "effective_limit_inr": result.effective_limit_inr,
        "message": result.message,
        "requires_approval_above": result.requires_approval_above,
        "can_proceed": result.decision == PolicyDecision.ALLOW,
        "needs_approval": result.decision == PolicyDecision.NEEDS_APPROVAL,
        "is_denied": result.decision == PolicyDecision.DENY,
    }


@router.post("/approve", summary="Buyer approves a pending transaction")
async def approve_transaction(
    request: ApproveRequest,
    session: Session = Depends(get_session),
):
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == request.transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if txn.state not in [TransactionState.DRAFT, TransactionState.PENDING_APPROVAL]:
        raise HTTPException(status_code=400, detail=f"Cannot approve transaction in state: {txn.state}")

    approval_id = f"appr_{uuid.uuid4().hex[:8]}"
    txn.approval_id = approval_id
    txn.approved_by = request.approved_by
    txn.approved_at = datetime.utcnow()
    txn.state = TransactionState.APPROVED

    # Generate fingerprint
    if txn.merchant_id and txn.product_id and txn.amount_inr:
        txn.fingerprint = make_fingerprint(
            txn.merchant_id, txn.product_id, txn.amount_inr, approval_id
        )

    txn.updated_at = datetime.utcnow()
    session.add(txn)
    session.commit()
    session.refresh(txn)

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor=request.approved_by,
        event_type="approval.granted",
        input_summary={
            "amount_inr": txn.amount_inr,
            "merchant": txn.merchant_name,
            "product": txn.product_name,
        },
        decision="APPROVED",
        next_state="APPROVED",
        result="buyer_consent_recorded",
    )

    return {
        "transaction_id": txn.transaction_id,
        "approval_id": approval_id,
        "state": txn.state,
        "approved_at": txn.approved_at.isoformat(),
        "fingerprint": txn.fingerprint,
    }


@router.get("/{transaction_id}", summary="Get transaction details")
async def get_transaction(
    transaction_id: str,
    session: Session = Depends(get_session),
):
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "transaction_id": txn.transaction_id,
        "correlation_id": txn.correlation_id,
        "state": txn.state,
        "buyer_intent": txn.buyer_intent,
        "parsed_constraints": json.loads(txn.parsed_constraints),
        "merchant_id": txn.merchant_id,
        "merchant_name": txn.merchant_name,
        "product_id": txn.product_id,
        "product_name": txn.product_name,
        "amount_inr": txn.amount_inr,
        "policy_result": txn.policy_result,
        "policy_reason_codes": json.loads(txn.policy_reason_codes),
        "approval_id": txn.approval_id,
        "approved_at": txn.approved_at.isoformat() if txn.approved_at else None,
        "razorpay_payment_link_id": txn.razorpay_payment_link_id,
        "razorpay_payment_link_url": txn.razorpay_payment_link_url,
        "fingerprint": txn.fingerprint,
        "failure_reason": txn.failure_reason,
        "recovery_action": txn.recovery_action,
        "created_at": txn.created_at.isoformat(),
    }


@router.get("/", summary="List recent transactions")
async def list_transactions(session: Session = Depends(get_session)):
    txns = session.exec(
        select(Transaction).order_by(Transaction.created_at.desc()).limit(20)
    ).all()
    return [
        {
            "transaction_id": t.transaction_id,
            "correlation_id": t.correlation_id,
            "state": t.state,
            "buyer_intent": t.buyer_intent[:80] + "..." if len(t.buyer_intent) > 80 else t.buyer_intent,
            "merchant_name": t.merchant_name,
            "product_name": t.product_name,
            "amount_inr": t.amount_inr,
            "created_at": t.created_at.isoformat(),
        }
        for t in txns
    ]
