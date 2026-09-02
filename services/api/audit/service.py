"""
Audit Service — append-only event store.
Every material agent and money action must be recorded here.
"""
import json
import logging
from datetime import datetime
from typing import List, Optional
from sqlmodel import Session, select
from models.audit import AuditEvent

logger = logging.getLogger(__name__)


class AuditService:
    def record(
        self,
        session: Session,
        transaction_id: str,
        correlation_id: str,
        actor: str,
        event_type: str,
        input_summary: dict = None,
        decision: Optional[str] = None,
        reason_codes: List[str] = None,
        policy_result: Optional[str] = None,
        payment_reference: Optional[str] = None,
        next_state: Optional[str] = None,
        result: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: dict = None,
    ) -> AuditEvent:
        event = AuditEvent(
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            actor=actor,
            event_type=event_type,
            input_summary=json.dumps(input_summary or {}),
            decision=decision,
            reason_codes=json.dumps(reason_codes or []),
            policy_result=policy_result,
            payment_reference=payment_reference,
            next_state=next_state,
            result=result,
            error_code=error_code,
            metadata_json=json.dumps(metadata or {}),
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        logger.info(
            f"AUDIT [{event.event_id}] {event_type} | txn={transaction_id} | "
            f"actor={actor} | decision={decision} | result={result}"
        )
        return event

    def get_timeline(
        self,
        session: Session,
        correlation_id: str
    ) -> List[AuditEvent]:
        events = session.exec(
            select(AuditEvent)
            .where(AuditEvent.correlation_id == correlation_id)
            .order_by(AuditEvent.timestamp)
        ).all()
        return list(events)

    def get_by_transaction(
        self,
        session: Session,
        transaction_id: str
    ) -> List[AuditEvent]:
        events = session.exec(
            select(AuditEvent)
            .where(AuditEvent.transaction_id == transaction_id)
            .order_by(AuditEvent.timestamp)
        ).all()
        return list(events)

    def get_recent(
        self,
        session: Session,
        limit: int = 50
    ) -> List[AuditEvent]:
        events = session.exec(
            select(AuditEvent)
            .order_by(AuditEvent.timestamp.desc())
            .limit(limit)
        ).all()
        return list(events)


# Singleton
audit_service = AuditService()
