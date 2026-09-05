import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from utils.time import utc_now


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}",
        unique=True,
        index=True
    )
    transaction_id: str = Field(index=True)
    correlation_id: str = Field(index=True)
    timestamp: datetime = Field(default_factory=utc_now)

    actor: str = Field(index=True)  # agentsetu | buyer | merchant | razorpay
    event_type: str = Field(index=True)  # intent.received | catalog.discovered | etc.

    input_summary: str = "{}"   # JSON
    decision: str | None = None  # ALLOW | DENY | NEEDS_APPROVAL | SUCCESS | FAILED
    reason_codes: str = "[]"    # JSON
    policy_result: str | None = None
    payment_reference: str | None = None
    next_state: str | None = None
    result: str | None = None
    error_code: str | None = None
    metadata_json: str = "{}"   # additional context
