"""Razorpay webhook handler — validates signature and processes payment state changes."""
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session, select

from database import get_session
from models.transaction import Transaction, TransactionState
from payments.razorpay_adapter import razorpay_adapter, PaymentStatus
from audit.service import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/razorpay", summary="Razorpay webhook endpoint")
async def razorpay_webhook(request: Request, session: Session = Depends(get_session)):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Validate signature
    if not razorpay_adapter.verify_webhook_signature(body, signature):
        logger.warning("Webhook signature validation failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event", "")
    entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})
    reference_id = entity.get("reference_id") or payload.get("payload", {}).get("payment", {}).get("entity", {}).get("description", "")
    rzp_status = entity.get("status", "unknown")
    payment_link_id = entity.get("id")

    # Find transaction
    txn = None
    if reference_id:
        txn = session.exec(
            select(Transaction).where(Transaction.transaction_id == reference_id)
        ).first()

    if not txn and payment_link_id:
        txn = session.exec(
            select(Transaction).where(Transaction.razorpay_payment_link_id == payment_link_id)
        ).first()

    if not txn:
        logger.warning(f"Webhook: no transaction found for reference_id={reference_id}")
        return {"received": True, "matched": False}

    # Map Razorpay status to internal state
    status = razorpay_adapter.map_rzp_status(rzp_status)
    if status == PaymentStatus.PAID:
        txn.state = TransactionState.PAYMENT_SUCCESS
        result = "payment_captured"
    elif status in [PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
        txn.state = TransactionState.PAYMENT_FAILED
        result = f"payment_{status.value}"
    elif status == PaymentStatus.EXPIRED:
        txn.state = TransactionState.PAYMENT_FAILED
        result = "payment_link_expired"
    else:
        txn.state = TransactionState.PAYMENT_UNKNOWN
        result = "status_unknown"

    txn.updated_at = datetime.utcnow()
    session.add(txn)

    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="razorpay",
        event_type="payment.status",
        input_summary={"webhook_event": event_type, "rzp_status": rzp_status},
        payment_reference=payment_link_id,
        result=result,
        next_state=txn.state,
    )

    if txn.state == TransactionState.PAYMENT_SUCCESS:
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
    logger.info(f"Webhook processed: txn={txn.transaction_id} → {txn.state}")
    return {"received": True, "matched": True, "new_state": txn.state}
