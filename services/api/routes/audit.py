"""Audit trail routes — inspect all material agent and money actions."""
import json
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from database import get_session
from models.audit import AuditEvent
from audit.service import audit_service

router = APIRouter()


@router.get("/{correlation_id}", summary="Get complete audit timeline by correlation ID or transaction ID")
async def get_audit_timeline(correlation_id: str, session: Session = Depends(get_session)):
    events = audit_service.get_timeline(session, correlation_id)
    # Fallback: also try querying by transaction_id if no events found
    if not events:
        events = audit_service.get_by_transaction(session, correlation_id)
    return {
        "correlation_id": correlation_id,
        "event_count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "transaction_id": e.transaction_id,
                "timestamp": e.timestamp.isoformat(),
                "actor": e.actor,
                "event_type": e.event_type,
                "input_summary": json.loads(e.input_summary),
                "decision": e.decision,
                "reason_codes": json.loads(e.reason_codes),
                "policy_result": e.policy_result,
                "payment_reference": e.payment_reference,
                "next_state": e.next_state,
                "result": e.result,
                "error_code": e.error_code,
            }
            for e in events
        ]
    }


@router.get("/", summary="List recent audit events")
async def list_audit_events(
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session)
):
    events = audit_service.get_recent(session, limit=limit)
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
        ]
    }
