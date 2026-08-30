from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}",
        unique=True,
        index=True
    )
    transaction_id: str = Field(index=True)
    correlation_id: str = Field(index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    actor: str  # agentsetu | buyer | merchant | razorpay
    event_type: str  # intent.received | catalog.discovered | policy.decision | etc.

    input_summary: str = "{}"   # JSON
    decision: Optional[str] = None  # ALLOW | DENY | NEEDS_APPROVAL | SUCCESS | FAILED
    reason_codes: str = "[]"    # JSON
    policy_result: Optional[str] = None
    payment_reference: Optional[str] = None
    next_state: Optional[str] = None
    result: Optional[str] = None
    error_code: Optional[str] = None
    metadata_json: str = "{}"   # additional context
