"""
Audit trail routes — inspect all material agent and money actions.

SECURITY (C4 fix): All endpoints require authentication.
- BUYER sees only their own transactions' audit events.
- MERCHANT_OWNER/ADMIN sees only their merchant's transaction events.
- PLATFORM_ADMIN sees all events.
"""
import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select

from database import get_session
from models.audit import AuditEvent
from models.user import User, UserRole
from models.transaction import Transaction
from models.merchant_user import MerchantUser
from audit.service import audit_service
from auth.dependencies import get_current_user

router = APIRouter()


def _filter_events_by_access(events: list, user: User, session: Session) -> list:
    """Filter audit events to only those the user is authorized to see."""
    if user.role == UserRole.PLATFORM_ADMIN:
        return events

    if user.role == UserRole.BUYER:
        # Get all transaction_ids owned by this buyer
        buyer_txns = session.exec(
            select(Transaction.transaction_id).where(Transaction.buyer_id == user.user_id)
        ).all()
        allowed_txn_ids = set(buyer_txns)
        return [e for e in events if e.transaction_id in allowed_txn_ids]

    # Merchant roles — get their merchant_ids, then allowed transaction_ids
    memberships = session.exec(
        select(MerchantUser).where(MerchantUser.user_id == user.user_id)
    ).all()
    merchant_ids = {m.merchant_id for m in memberships}
    if not merchant_ids:
        return []

    merchant_txns = session.exec(
        select(Transaction.transaction_id).where(Transaction.merchant_id.in_(merchant_ids))
    ).all()
    allowed_txn_ids = set(merchant_txns)
    return [e for e in events if e.transaction_id in allowed_txn_ids]


def _serialize_event(e: AuditEvent) -> dict:
    return {
        "event_id": e.event_id,
        "transaction_id": e.transaction_id,
        "correlation_id": e.correlation_id,
        "timestamp": e.timestamp.isoformat(),
        "actor": e.actor,
        "event_type": e.event_type,
        "input_summary": json.loads(e.input_summary) if e.input_summary else {},
        "decision": e.decision,
        "reason_codes": json.loads(e.reason_codes) if e.reason_codes else [],
        "policy_result": e.policy_result,
        "payment_reference": e.payment_reference,
        "next_state": e.next_state,
        "result": e.result,
        "error_code": e.error_code,
    }


@router.get("/{correlation_id}", summary="Get complete audit timeline by correlation ID or transaction ID")
async def get_audit_timeline(
    correlation_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    events = audit_service.get_timeline(session, correlation_id)
    # Fallback: also try querying by transaction_id if no events found
    if not events:
        events = audit_service.get_by_transaction(session, correlation_id)

    # Tenant filtering
    events = _filter_events_by_access(events, current_user, session)

    return {
        "correlation_id": correlation_id,
        "event_count": len(events),
        "events": [_serialize_event(e) for e in events],
    }


@router.get("/", summary="List recent audit events")
async def list_audit_events(
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    events = audit_service.get_recent(session, limit=limit)

    # Tenant filtering
    events = _filter_events_by_access(events, current_user, session)

    return {
        "count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "transaction_id": e.transaction_id,
                "correlation_id": e.correlation_id,
                "timestamp": e.timestamp.isoformat(),
                "actor": e.actor,
                "event_type": e.event_type,
                "decision": e.decision,
                "result": e.result,
                "next_state": e.next_state,
            }
            for e in events
        ],
    }
