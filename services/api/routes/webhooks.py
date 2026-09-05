"""
Razorpay webhook handler.
Security: HMAC-SHA256 signature verified BEFORE any state mutation.
Idempotency: Provider event ID stored; duplicate events are safely skipped.
"""
import hashlib
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from audit.service import audit_service
from database import get_session
from errors import ErrorCode, make_error
from models.transaction import Transaction, TransactionState, validate_transition
from models.webhook import WebhookEvent
from payments.razorpay_adapter import PaymentStatus, razorpay_adapter
from utils.time import utc_now

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/razorpay", summary="Razorpay webhook endpoint")
async def razorpay_webhook(request: Request, session: Session = Depends(get_session)):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # ── 1. Verify signature BEFORE touching any state ─────────────────────────
    sig_valid = razorpay_adapter.verify_webhook_signature(body, signature)
    if not sig_valid:
        logger.warning("Webhook signature validation FAILED — request rejected")
        # Persist the invalid attempt for security auditing
        try:
            _persist_webhook_event(
                session, body, provider_event_id="INVALID",
                event_type="unknown", sig_valid=False,
                status="INVALID_SIGNATURE"
            )
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=make_error(
            ErrorCode.WEBHOOK_INVALID,
            "Invalid webhook signature.",
            400,
        ).body.decode())

    # ── 2. Parse payload ───────────────────────────────────────────────────────
    try:
        payload = json.loads(body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event", "unknown")
    # Extract provider event ID (Razorpay sends this as payload.event_id in recent API)
    provider_event_id = payload.get("id") or payload.get("event_id") or hashlib.sha256(body).hexdigest()[:32]

    # ── 3. Idempotency check — skip duplicate events ──────────────────────────
    # Phase 7 fix: check BOTH RECEIVED (in-flight) and PROCESSED to prevent
    # concurrent duplicate processing. A webhook in RECEIVED state is already
    # being handled by another request.
    existing = session.exec(
        select(WebhookEvent).where(
            WebhookEvent.provider == "razorpay",
            WebhookEvent.provider_event_id == provider_event_id,
        )
    ).first()
    if existing:
        if existing.processing_status in ("RECEIVED", "PROCESSED"):
            logger.info(f"Webhook duplicate skipped: {provider_event_id} (status={existing.processing_status})")
            return {"received": True, "duplicate": True, "webhook_id": existing.webhook_id}
        # FAILED records can be retried — reuse the existing record
        logger.info(f"Webhook retry for FAILED event: {provider_event_id}")
        existing.processing_status = "RECEIVED"
        existing.error_message = None
        existing.processed_at = None
        session.add(existing)
        session.commit()
        wh_event = existing
    else:
        # ── 4. Persist the raw event ──────────────────────────────────────────
        wh_event = _persist_webhook_event(
            session, body, provider_event_id=provider_event_id,
            event_type=event_type, sig_valid=True, status="RECEIVED"
        )

    # ── 5. Extract entity data ────────────────────────────────────────────────
    entity = (
        payload.get("payload", {}).get("payment_link", {}).get("entity", {})
        or payload.get("payload", {}).get("payment", {}).get("entity", {})
    )
    reference_id = entity.get("reference_id") or entity.get("description", "")
    rzp_status = entity.get("status", "unknown")
    payment_link_id = entity.get("id")

    # ── 6. Locate transaction ──────────────────────────────────────────────────
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
        logger.warning(f"Webhook: no transaction for reference_id={reference_id} payment_link_id={payment_link_id}")
        _mark_webhook_processed(session, wh_event, status="FAILED", error="transaction_not_found")
        return {"received": True, "matched": False}

    # ── 7. Map status and update transaction ──────────────────────────────────
    status_obj = razorpay_adapter.map_rzp_status(rzp_status)
    old_state = txn.state

    if status_obj == PaymentStatus.PAID:
        new_state = TransactionState.PAYMENT_SUCCESS
        result = "payment_captured"
    elif status_obj in [PaymentStatus.FAILED, PaymentStatus.CANCELLED]:
        new_state = TransactionState.PAYMENT_FAILED
        result = f"payment_{status_obj.value}"
    elif status_obj == PaymentStatus.EXPIRED:
        new_state = TransactionState.PAYMENT_FAILED
        result = "payment_link_expired"
    else:
        new_state = TransactionState.PAYMENT_UNKNOWN
        result = "status_unknown"

    # Phase 7: Validate state transition before mutating
    if not validate_transition(old_state, new_state):
        logger.warning(
            f"Webhook: illegal transition {old_state}→{new_state} for txn={txn.transaction_id}, skipping"
        )
        _mark_webhook_processed(session, wh_event, status="FAILED", error=f"illegal_transition:{old_state}→{new_state}")
        session.commit()
        return {"received": True, "matched": True, "skipped": True, "reason": "illegal_transition"}

    txn.state = new_state
    txn.updated_at = utc_now()
    session.add(txn)

    # L2 FIX: flush_only — webhook handler commits once at the end
    audit_service.record(
        session=session,
        transaction_id=txn.transaction_id,
        correlation_id=txn.correlation_id,
        actor="razorpay",
        event_type="payment.status",
        input_summary={"webhook_event": event_type, "rzp_status": rzp_status, "prev_state": old_state},
        payment_reference=payment_link_id,
        result=result,
        next_state=new_state,
        flush_only=True,
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
            flush_only=True,
        )

    wh_event.transaction_id = txn.transaction_id
    wh_event.payment_link_id = payment_link_id
    _mark_webhook_processed(session, wh_event, status="PROCESSED")

    session.commit()
    logger.info(f"Webhook processed: {provider_event_id} | txn={txn.transaction_id} | {old_state}→{txn.state}")
    return {"received": True, "matched": True, "new_state": txn.state, "webhook_id": wh_event.webhook_id}


def _persist_webhook_event(
    session: Session,
    body: bytes,
    provider_event_id: str,
    event_type: str,
    sig_valid: bool,
    status: str,
) -> WebhookEvent:
    payload_hash = hashlib.sha256(body).hexdigest()
    wh = WebhookEvent(
        provider="razorpay",
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        signature_valid=sig_valid,
        processing_status=status,
    )
    session.add(wh)
    session.commit()
    session.refresh(wh)
    return wh


def _mark_webhook_processed(session: Session, wh: WebhookEvent, status: str, error: str = None):
    wh.processing_status = status
    wh.processed_at = utc_now()
    if error:
        wh.error_message = error
    session.add(wh)
    session.commit()
