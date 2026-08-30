"""
Payment adapter routes.
Creates Razorpay Payment Links ONLY after policy pass + approval.
Handles status verification and graceful failure.
"""
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models.merchant import Merchant, Product
from models.transaction import Transaction, TransactionState
from policy.engine import PolicyEngine, PolicyDecision
from payments.razorpay_adapter import razorpay_adapter, PaymentStatus
from ai.orchestrator import buyer_orchestrator
from audit.service import audit_service

router = APIRouter()
policy_engine = PolicyEngine()


class CreatePaymentLinkRequest(BaseModel):
    transaction_id: str
    buyer_limit_inr: Optional[int] = None


class VerifyPaymentRequest(BaseModel):
    transaction_id: str


@router.post("/payment-link", summary="Create Razorpay Payment Link (after authorization)")
async def create_payment_link(
    request: CreatePaymentLinkRequest,
    session: Session = Depends(get_session),
):
    """
    Creates a Razorpay Payment Link ONLY if:
    1. Policy engine ALLOWS the transaction
    2. Buyer approval exists when required
    Idempotent: returns existing link if already created.
    """
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == request.transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # ── Idempotency: return existing link ────────────────────────────────────
    if txn.razorpay_payment_link_id and txn.state in [
        TransactionState.PAYMENT_LINK_CREATED,
        TransactionState.PAYMENT_SUCCESS,
    ]:
        return {
            "transaction_id": txn.transaction_id,
            "payment_link_id": txn.razorpay_payment_link_id,
            "payment_link_url": txn.razorpay_payment_link_url,
            "state": txn.state,
            "idempotent": True,
        }

    # ── Validate transaction state ────────────────────────────────────────────
    if txn.state not in [TransactionState.DRAFT, TransactionState.PENDING_APPROVAL, TransactionState.APPROVED]:
        raise HTTPException(status_code=400, detail=f"Cannot create payment in state: {txn.state}")

    if not txn.merchant_id or not txn.product_id or not txn.amount_inr:
        raise HTTPException(status_code=400, detail="Transaction missing product/merchant/amount. Select a product first.")

    # ── Load merchant and product ─────────────────────────────────────────────
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == txn.merchant_id)
    ).first()
    product = session.exec(
        select(Product).where(
            Product.product_id == txn.product_id,
            Product.merchant_id == txn.merchant_id,
        )
    ).first()

    if not merchant or not product:
        raise HTTPException(status_code=404, detail="Merchant or product not found")

    # ── Policy check (deterministic, not LLM) ────────────────────────────────
    is_approved = txn.state == TransactionState.APPROVED and txn.approval_id is not None
    policy_result = policy_engine.evaluate(
        merchant=merchant,
        product=product,
        amount_inr=txn.amount_inr,
        buyer_limit_inr=request.buyer_limit_inr,
        is_approved=is_approved,
    )

    txn.policy_result = policy_result.decision
    txn.policy_reason_codes = json.dumps(policy_result.reason_codes)

    # Audit policy decision
    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="agentsetu",
        event_type="policy.decision",
        input_summary={"amount_inr": txn.amount_inr, "is_approved": is_approved},
        decision=policy_result.decision,
        reason_codes=policy_result.reason_codes,
        policy_result=policy_result.decision,
        next_state=(
            "PAYMENT_LINK_CREATED" if policy_result.decision == PolicyDecision.ALLOW
            else "PENDING_APPROVAL" if policy_result.decision == PolicyDecision.NEEDS_APPROVAL
            else "CANCELLED"
        ),
    )

    # ── DENY: block payment ────────────────────────────────────────────────────
    if policy_result.decision == PolicyDecision.DENY:
        txn.state = TransactionState.CANCELLED
        txn.failure_reason = policy_result.message
        txn.updated_at = datetime.utcnow()
        session.add(txn)
        session.commit()
        raise HTTPException(
            status_code=403,
            detail={
                "blocked": True,
                "reason": policy_result.message,
                "reason_codes": policy_result.reason_codes,
                "effective_limit_inr": policy_result.effective_limit_inr,
            }
        )

    # ── NEEDS APPROVAL: return approval request ───────────────────────────────
    if policy_result.decision == PolicyDecision.NEEDS_APPROVAL:
        txn.state = TransactionState.PENDING_APPROVAL
        txn.updated_at = datetime.utcnow()
        session.add(txn)
        session.commit()
        return {
            "transaction_id": txn.transaction_id,
            "state": txn.state,
            "needs_approval": True,
            "message": policy_result.message,
            "amount_inr": txn.amount_inr,
            "requires_approval_above": policy_result.requires_approval_above,
            "reason_codes": policy_result.reason_codes,
        }

    # ── ALLOW: create Razorpay Payment Link ──────────────────────────────────
    link_result = razorpay_adapter.create_payment_link(
        amount_inr=txn.amount_inr,
        merchant_name=merchant.name,
        product_name=product.name,
        transaction_id=txn.transaction_id,
        description=f"AgentSetu: {product.name} from {merchant.name}",
        reference_id=txn.transaction_id,
    )

    if not link_result.success:
        txn.state = TransactionState.PAYMENT_FAILED
        txn.failure_reason = f"Razorpay error: {link_result.error}"
        txn.updated_at = datetime.utcnow()
        session.add(txn)

        audit_service.record(
            session=session,
            transaction_id=txn.transaction_id,
            correlation_id=txn.correlation_id,
            actor="razorpay",
            event_type="payment.created",
            decision="FAILED",
            error_code="RAZORPAY_API_ERROR",
            result=link_result.error,
            next_state="PAYMENT_FAILED",
        )
        session.commit()

        raise HTTPException(
            status_code=502,
            detail={
                "payment_failed": True,
                "error": link_result.error,
                "message": "Razorpay payment link creation failed. Transaction held safely — no duplicate will be attempted.",
            }
        )

    # ── Payment link created successfully ────────────────────────────────────
    txn.razorpay_payment_link_id = link_result.payment_link_id
    txn.razorpay_payment_link_url = link_result.payment_link_url
    txn.state = TransactionState.PAYMENT_LINK_CREATED
    txn.updated_at = datetime.utcnow()
    session.add(txn)

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="agentsetu",
        event_type="payment.created",
        input_summary={"amount_inr": txn.amount_inr},
        decision="SUCCESS",
        payment_reference=link_result.payment_link_id,
        next_state="PAYMENT_LINK_CREATED",
        result="payment_link_created",
    )

    session.commit()

    return {
        "transaction_id": txn.transaction_id,
        "payment_link_id": link_result.payment_link_id,
        "payment_link_url": link_result.payment_link_url,
        "amount_inr": txn.amount_inr,
        "state": txn.state,
        "policy_decision": policy_result.decision,
        "needs_approval": False,
    }


@router.post("/verify/{transaction_id}", summary="Verify payment status (no auto-retry)")
async def verify_payment(
    transaction_id: str,
    session: Session = Depends(get_session),
):
    """
    Explicitly verify Razorpay payment status.
    NEVER auto-retries. Unknown status is held safely.
    """
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not txn.razorpay_payment_link_id:
        raise HTTPException(status_code=400, detail="No payment link found for this transaction")

    # Fetch from Razorpay
    link_result = razorpay_adapter.fetch_payment_link(txn.razorpay_payment_link_id)

    # Map to transaction state
    if link_result.status == PaymentStatus.PAID:
        new_state = TransactionState.PAYMENT_SUCCESS
        result = "payment_captured"
    elif link_result.status in [PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
        new_state = TransactionState.PAYMENT_FAILED
        result = f"payment_{link_result.status.value}"
    elif link_result.status == PaymentStatus.EXPIRED:
        new_state = TransactionState.PAYMENT_FAILED
        result = "payment_link_expired"
    else:
        new_state = TransactionState.PAYMENT_UNKNOWN
        result = "status_unknown"

    txn.state = new_state
    txn.updated_at = datetime.utcnow()
    session.add(txn)

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="agentsetu",
        event_type="payment.status",
        input_summary={"razorpay_status": link_result.status},
        payment_reference=txn.razorpay_payment_link_id,
        next_state=new_state,
        result=result,
    )

    if new_state == TransactionState.PAYMENT_SUCCESS:
        txn.state = TransactionState.RECEIPT_ISSUED
        session.add(txn)
        audit_service.record(
            session=session,
            transaction_id=txn.transaction_id,
            correlation_id=txn.correlation_id,
            actor="agentsetu",
            event_type="receipt.issued",
            result="receipt_generated",
            next_state="RECEIPT_ISSUED",
        )

    session.commit()

    # Recovery suggestion for failures
    recovery_message = None
    if new_state in [TransactionState.PAYMENT_FAILED, TransactionState.PAYMENT_UNKNOWN]:
        recovery_message = (
            "Payment state needs verification. I have not retried the payment. "
            "You can retry with a verified payment method or cancel this transaction."
            if new_state == TransactionState.PAYMENT_UNKNOWN
            else "Payment did not complete. No duplicate charge has been attempted. "
                 "You may retry or choose an alternative."
        )
        txn.recovery_action = recovery_message
        txn.state = TransactionState.RECOVERY_PROPOSED
        session.add(txn)
        session.commit()

    return {
        "transaction_id": txn.transaction_id,
        "state": new_state,
        "razorpay_status": link_result.status,
        "payment_link_url": txn.razorpay_payment_link_url,
        "recovery_message": recovery_message,
        "receipt": (
            {
                "transaction_id": txn.transaction_id,
                "merchant_name": txn.merchant_name,
                "product_name": txn.product_name,
                "amount_inr": txn.amount_inr,
                "payment_link_id": txn.razorpay_payment_link_id,
                "state": "PAID",
            }
            if new_state == TransactionState.RECEIPT_ISSUED else None
        ),
    }


@router.get("/receipt/{transaction_id}", summary="Get machine-readable transaction receipt")
async def get_receipt(
    transaction_id: str,
    session: Session = Depends(get_session),
):
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    from models.audit import AuditEvent
    events = session.exec(
        select(AuditEvent).where(AuditEvent.transaction_id == transaction_id)
        .order_by(AuditEvent.timestamp)
    ).all()

    return {
        "receipt": {
            "transaction_id": txn.transaction_id,
            "correlation_id": txn.correlation_id,
            "state": txn.state,
            "buyer_intent": txn.buyer_intent,
            "merchant_name": txn.merchant_name,
            "product_name": txn.product_name,
            "amount_inr": txn.amount_inr,
            "policy_decision": txn.policy_result,
            "approval_id": txn.approval_id,
            "approved_at": txn.approved_at.isoformat() if txn.approved_at else None,
            "payment_link_id": txn.razorpay_payment_link_id,
            "payment_link_url": txn.razorpay_payment_link_url,
            "created_at": txn.created_at.isoformat(),
        },
        "audit_events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "actor": e.actor,
                "timestamp": e.timestamp.isoformat(),
                "decision": e.decision,
                "result": e.result,
            }
            for e in events
        ],
    }
