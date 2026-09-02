"""WebhookEvent model — idempotent event store for all incoming provider webhooks."""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class WebhookProcessingStatus(str):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"


class WebhookEvent(SQLModel, table=True):
    __tablename__ = "webhook_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    webhook_id: str = Field(
        default_factory=lambda: f"wh_{uuid.uuid4().hex[:12]}",
        unique=True,
        index=True,
    )

    provider: str                           # razorpay | stripe | etc.
    provider_event_id: str = Field(index=True)  # Razorpay event ID for dedup
    event_type: str                         # payment_link.paid, etc.
    payload_hash: str                       # SHA-256 of raw body for integrity

    signature_valid: bool = False
    processing_status: str = "RECEIVED"
    error_message: Optional[str] = None

    # Correlation
    transaction_id: Optional[str] = Field(default=None, index=True)
    payment_link_id: Optional[str] = None

    received_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
