"""
Payment adapter routes.
SECURITY: Razorpay is called ONLY after:
  1. Policy engine ALLOWS (deterministic)
  2. Buyer has approved (if required)
  3. A capability has been issued AND consumed atomically

No LLM touches this flow. Amount is verified server-side against DB.
All endpoints require authentication (C2 fix).
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_session
from models.merchant import Merchant, Product
from models.transaction import Transaction, TransactionState, validate_transition
from models.user import User, UserRole, BuyerProfile
from models.merchant_user import MerchantUser
from models.idempotency import IdempotencyRecord
from policy.engine import PolicyEngine, PolicyDecision, BuyerPolicyContext
from payments.razorpay_adapter import razorpay_adapter, PaymentStatus
from capability.service import capability_service
from audit.service import audit_service
from auth.dependencies import get_current_user
from errors import make_error, ErrorCode

router = APIRouter()
policy_engine = PolicyEngine()
limiter = Limiter(key_func=get_remote_address)


class CreatePaymentLinkRequest(BaseModel):
    transaction_id: str
    # C5 FIX: buyer_limit_inr REMOVED from client request.
    # Buyer limits are loaded server-side from BuyerProfile.


def _assert_payment_txn_access(txn: Transaction, user: User, session: Session):
    """Raise 403 unless the caller owns this transaction or is PLATFORM_ADMIN."""
    if user.role == UserRole.PLATFORM_ADMIN:
        return
    if user.role == UserRole.BUYER:
        if txn.buyer_id != user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized for this transaction")
        return
    # Merchant roles — check membership
    if txn.merchant_id:
        membership = session.exec(
            select(MerchantUser).where(
                MerchantUser.merchant_id == txn.merchant_id,
                MerchantUser.user_id == user.user_id,
            )
        ).first()
        if membership:
            return
    raise HTTPException(status_code=403, detail="Not authorized for this transaction")


@router.post("/payment-link", summary="Create Razorpay Payment Link (after authorization)")
@limiter.limit("5/minute")
async def create_payment_link(
    request: Request,
    body: CreatePaymentLinkRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Full payment gate:
    0. Idempotency-Key check (return cached response for retries)
    1. Load transaction + verify state + verify caller authorization
    2. Verify amount has not changed
    3. Load buyer limits from DB (never from client)
    4. Policy engine final check (deterministic)
    5. Issue capability (bound to buyer)
    6. Consume capability atomically
    7. Call Razorpay (server-side only)
    8. Record audit event
    """
    # ── Phase 6: Idempotency-Key header ──────────────────────────────────────
    idempotency_key = request.headers.get("Idempotency-Key")
    if idempotency_key:
        existing_record = session.exec(
            select(IdempotencyRecord).where(
                IdempotencyRecord.idempotency_key == idempotency_key,
                IdempotencyRecord.user_id == current_user.user_id,
                IdempotencyRecord.endpoint == "POST /v1/payments/payment-link",
            )
        ).first()
        if existing_record:
            return JSONResponse(
                status_code=existing_record.status_code,
                content=json.loads(existing_record.response_body),
                headers={"Idempotency-Key": idempotency_key, "X-Idempotent-Replay": "true"},
            )

    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == body.transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail=make_error(
            ErrorCode.NOT_FOUND, "Transaction not found.", 404
        ).body.decode())

    # Bind buyer if not already bound (MUST happen before the access check
    # so that anonymously-created transactions are claimed by the first
    # authenticated buyer, then the access check compares matching IDs).
    if not txn.buyer_id and current_user.role == UserRole.BUYER:
        txn.buyer_id = current_user.user_id
        session.add(txn)
        session.flush()

    # C2 FIX: verify caller is authorized for this transaction
    _assert_payment_txn_access(txn, current_user, session)

    # ── Idempotency: return existing link if already created ──────────────────
    if txn.razorpay_payment_link_id and txn.state in [
        TransactionState.PAYMENT_LINK_CREATED,
        TransactionState.PAYMENT_SUCCESS,
        TransactionState.RECEIPT_ISSUED,
    ]:
        return {
            "transaction_id": txn.transaction_id,
            "payment_link_id": txn.razorpay_payment_link_id,
            "payment_link_url": txn.razorpay_payment_link_url,
            "state": txn.state,
            "idempotent": True,
        }

    # ── Validate transition is legal ──────────────────────────────────────────
    valid_states = [TransactionState.DRAFT, TransactionState.PENDING_APPROVAL, TransactionState.APPROVED]
    if txn.state not in valid_states:
        raise HTTPException(status_code=400, detail=make_error(
            ErrorCode.VALIDATION, f"Cannot create payment in state: {txn.state}", 400
        ).body.decode())

    if not txn.merchant_id or not txn.product_id or not txn.amount_inr:
        raise HTTPException(status_code=400, detail=make_error(
            ErrorCode.VALIDATION, "Transaction missing product/merchant/amount. Select a product first.", 400
        ).body.decode())

    # ── Load merchant and product — server-side amount verification ───────────
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == txn.merchant_id)
    ).first()
    product = session.exec(
        select(Product).where(
            Product.product_id == txn.product_id,
            Product.merchant_id == txn.merchant_id,
        )
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail=make_error(
            ErrorCode.MERCHANT_NOT_FOUND, "Merchant not found.", 404
        ).body.decode())
    if not product:
        raise HTTPException(status_code=404, detail=make_error(
            ErrorCode.PRODUCT_NOT_FOUND, "Product not found.", 404
        ).body.decode())

    # ── Server-side price verification — catch price changes ──────────────────
    if product.price_inr != txn.amount_inr:
        capability_service.revoke_for_transaction(session, txn.transaction_id, reason="price_changed")
        txn.state = TransactionState.DRAFT
        txn.amount_inr = product.price_inr
        session.add(txn)
        session.commit()
        raise HTTPException(status_code=409, detail=make_error(
            ErrorCode.PRICE_CHANGED,
            f"Product price changed to ₹{product.price_inr}. Please review and re-approve.",
            409,
            {"new_price_inr": product.price_inr, "original_price_inr": txn.amount_inr},
        ).body.decode())

    # ── Inventory check ───────────────────────────────────────────────────────
    if not product.availability or product.inventory_count <= 0:
        capability_service.revoke_for_transaction(session, txn.transaction_id, reason="inventory_changed")
        raise HTTPException(status_code=409, detail=make_error(
            ErrorCode.INVENTORY_CHANGED, "Product is no longer available.", 409
        ).body.decode())

    # ── C5 FIX: Load buyer policy from DB, never from client ─────────────────
    buyer_context = None
    buyer_limit_inr = None
    if current_user.role == UserRole.BUYER:
        buyer_profile = session.exec(
            select(BuyerProfile).where(BuyerProfile.user_id == current_user.user_id)
        ).first()
        if buyer_profile:
            import json as _json
            buyer_limit_inr = buyer_profile.per_transaction_auto_limit_inr

            # Calculate today's spend for daily limit enforcement
            from datetime import date
            today_start = datetime.combine(date.today(), datetime.min.time())
            daily_txns = session.exec(
                select(Transaction).where(
                    Transaction.buyer_id == current_user.user_id,
                    Transaction.created_at >= today_start,
                    Transaction.state.in_([
                        TransactionState.PAYMENT_LINK_CREATED,
                        TransactionState.PAYMENT_SUCCESS,
                        TransactionState.RECEIPT_ISSUED,
                        TransactionState.APPROVED,
                        TransactionState.PENDING_APPROVAL,
                    ]),
                    Transaction.transaction_id != txn.transaction_id,  # exclude current
                )
            ).all()
            daily_spent = sum(t.amount_inr or 0 for t in daily_txns)

            # Parse blocked lists
            try:
                blocked_merchants = _json.loads(buyer_profile.blocked_merchants)
            except Exception:
                blocked_merchants = []
            try:
                blocked_categories = _json.loads(buyer_profile.blocked_categories)
            except Exception:
                blocked_categories = []

            buyer_context = BuyerPolicyContext(
                per_transaction_auto_limit_inr=buyer_profile.per_transaction_auto_limit_inr,
                daily_limit_inr=buyer_profile.daily_limit_inr,
                daily_spent_inr=daily_spent,
                blocked_merchants=blocked_merchants,
                blocked_categories=blocked_categories,
            )

    # ── Deterministic policy check (final gate) ───────────────────────────────
    is_approved = txn.state == TransactionState.APPROVED and txn.approval_id is not None
    policy_result = policy_engine.evaluate(
        merchant=merchant,
        product=product,
        amount_inr=txn.amount_inr,
        buyer_limit_inr=buyer_limit_inr,
        is_approved=is_approved,
        buyer_context=buyer_context,
    )

    txn.policy_result = policy_result.decision
    txn.policy_reason_codes = json.dumps(policy_result.reason_codes)

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="agentsetu",
        event_type="policy.decision",
        input_summary={"amount_inr": txn.amount_inr, "is_approved": is_approved, "buyer_limit_inr": buyer_limit_inr},
        decision=policy_result.decision,
        reason_codes=policy_result.reason_codes,
        policy_result=policy_result.decision,
        next_state=(
            "PAYMENT_LINK_CREATED" if policy_result.decision == PolicyDecision.ALLOW
            else "PENDING_APPROVAL" if policy_result.decision == PolicyDecision.NEEDS_APPROVAL
            else "CANCELLED"
        ),
    )

    # ── DENY ──────────────────────────────────────────────────────────────────
    if policy_result.decision == PolicyDecision.DENY:
        txn.state = TransactionState.CANCELLED
        txn.failure_reason = policy_result.message
        txn.updated_at = datetime.utcnow()
        session.add(txn)
        session.commit()
        raise HTTPException(status_code=403, detail=make_error(
            ErrorCode.POLICY_BLOCKED,
            policy_result.message,
            403,
            {"reason_codes": policy_result.reason_codes, "effective_limit_inr": policy_result.effective_limit_inr},
        ).body.decode())

    # ── NEEDS APPROVAL ────────────────────────────────────────────────────────
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

    # ── ALLOW: issue + consume capability atomically ──────────────────────────
    cap = capability_service.issue_capability(
        session=session,
        transaction_id=txn.transaction_id,
        merchant_id=txn.merchant_id,
        product_id=txn.product_id,
        amount_inr=txn.amount_inr,
        approval_id=txn.approval_id,
        buyer_id=current_user.user_id,
    )

    ok, reason = capability_service.consume_capability(
        session=session,
        capability_id=cap.capability_id,
        transaction_id=txn.transaction_id,
        merchant_id=txn.merchant_id,
        amount_inr=txn.amount_inr,
        buyer_id=current_user.user_id,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=make_error(
            reason, f"Capability validation failed: {reason}", 400
        ).body.decode())

    # ── Call Razorpay — server-side only ──────────────────────────────────────
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
        raise HTTPException(status_code=502, detail=make_error(
            ErrorCode.PAYMENT_FAILED,
            "Payment link creation failed. Transaction held safely — no duplicate will be attempted.",
            502,
            {"provider_error": link_result.error},
        ).body.decode())

    # ── Success: persist and audit ────────────────────────────────────────────
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
        input_summary={"amount_inr": txn.amount_inr, "capability_id": cap.capability_id},
        decision="SUCCESS",
        payment_reference=link_result.payment_link_id,
        next_state="PAYMENT_LINK_CREATED",
        result="payment_link_created",
    )

    session.commit()

    success_response = {
        "transaction_id": txn.transaction_id,
        "payment_link_id": link_result.payment_link_id,
        "payment_link_url": link_result.payment_link_url,
        "amount_inr": txn.amount_inr,
        "state": txn.state,
        "policy_decision": policy_result.decision,
        "needs_approval": False,
        "capability_id": cap.capability_id,
    }

    # ── Phase 6: Store idempotency record ────────────────────────────────────
    if idempotency_key:
        record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            endpoint="POST /v1/payments/payment-link",
            user_id=current_user.user_id,
            status_code=200,
            response_body=json.dumps(success_response),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )
        session.add(record)
        session.commit()

    return success_response


@router.post("/verify/{transaction_id}", summary="Verify payment status (no auto-retry)")
async def verify_payment(
    transaction_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Explicitly verify Razorpay payment status.
    NEVER auto-retries. PAYMENT_UNKNOWN is held safely pending reconciliation.
    """
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail=make_error(
            ErrorCode.NOT_FOUND, "Transaction not found.", 404
        ).body.decode())

    _assert_payment_txn_access(txn, current_user, session)

    if not txn.razorpay_payment_link_id:
        raise HTTPException(status_code=400, detail=make_error(
            ErrorCode.VALIDATION, "No payment link found for this transaction.", 400
        ).body.decode())

    link_result = razorpay_adapter.fetch_payment_link(txn.razorpay_payment_link_id)

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
        # UNKNOWN — freeze, do not retry
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

    recovery_message = None
    if new_state in [TransactionState.PAYMENT_FAILED, TransactionState.PAYMENT_UNKNOWN]:
        recovery_message = (
            "Payment status is uncertain. I have NOT retried. "
            "Contact support with your transaction ID or try again once the status is confirmed."
            if new_state == TransactionState.PAYMENT_UNKNOWN
            else "Payment did not complete. No duplicate charge has been attempted. "
                 "You may retry with a fresh payment link or choose an alternative."
        )
        txn.recovery_action = recovery_message
        txn.state = TransactionState.RECOVERY_PROPOSED
        session.add(txn)
        session.commit()

    return {
        "transaction_id": txn.transaction_id,
        "state": txn.state,
        "razorpay_status": link_result.status,
        "payment_link_url": txn.razorpay_payment_link_url,
        "recovery_message": recovery_message,
    }


@router.get("/receipt/{transaction_id}", summary="Get machine-readable commerce receipt")
async def get_receipt(
    transaction_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    import hashlib
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail=make_error(
            ErrorCode.NOT_FOUND, "Transaction not found.", 404
        ).body.decode())

    _assert_payment_txn_access(txn, current_user, session)

    from models.audit import AuditEvent
    events = session.exec(
        select(AuditEvent).where(AuditEvent.transaction_id == transaction_id)
        .order_by(AuditEvent.timestamp)
    ).all()

    receipt_payload = {
        "receipt_version": "0.2",
        "transaction_id": txn.transaction_id,
        "correlation_id": txn.correlation_id,
        "state": txn.state,
        "buyer_intent": txn.buyer_intent,
        "merchant_name": txn.merchant_name,
        "product_name": txn.product_name,
        "amount_inr": txn.amount_inr,
        "currency": "INR",
        "policy_decision": txn.policy_result,
        "approval_id": txn.approval_id,
        "approved_at": txn.approved_at.isoformat() if txn.approved_at else None,
        "payment_link_id": txn.razorpay_payment_link_id,
        "created_at": txn.created_at.isoformat(),
        "audit_event_count": len(events),
    }

    receipt_hash = hashlib.sha256(
        json.dumps(receipt_payload, sort_keys=True).encode()
    ).hexdigest()

    return {
        "receipt": receipt_payload,
        "receipt_hash": receipt_hash,
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


@router.post("/cancel/{transaction_id}", summary="Cancel a pending payment link")
async def cancel_payment(
    transaction_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Phase 8: Cancel a Razorpay payment link before it is paid.
    Only valid when transaction is in PAYMENT_LINK_CREATED state.
    """
    txn = session.exec(
        select(Transaction).where(Transaction.transaction_id == transaction_id)
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail=make_error(
            ErrorCode.NOT_FOUND, "Transaction not found.", 404
        ).body.decode())

    _assert_payment_txn_access(txn, current_user, session)

    if txn.state != TransactionState.PAYMENT_LINK_CREATED:
        raise HTTPException(status_code=400, detail=make_error(
            ErrorCode.VALIDATION,
            f"Cannot cancel payment in state: {txn.state}. Only PAYMENT_LINK_CREATED can be cancelled.",
            400,
        ).body.decode())

    if not txn.razorpay_payment_link_id:
        raise HTTPException(status_code=400, detail=make_error(
            ErrorCode.VALIDATION, "No payment link to cancel.", 400
        ).body.decode())

    # Call Razorpay
    cancelled = razorpay_adapter.cancel_payment_link(txn.razorpay_payment_link_id)

    txn.state = TransactionState.CANCELLED
    txn.failure_reason = "cancelled_by_user"
    txn.updated_at = datetime.utcnow()
    session.add(txn)

    # Revoke any outstanding capabilities
    capability_service.revoke_for_transaction(session, txn.transaction_id, reason="user_cancelled")

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor=current_user.user_id,
        event_type="payment.cancelled",
        input_summary={"razorpay_cancelled": cancelled},
        result="cancelled_by_user",
        next_state="CANCELLED",
    )

    session.commit()
    return {
        "transaction_id": txn.transaction_id,
        "state": txn.state,
        "razorpay_cancelled": cancelled,
    }
