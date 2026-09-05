"""Idempotency-Key support — prevents duplicate side-effects from retried requests."""
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from utils.time import utc_now


class IdempotencyRecord(SQLModel, table=True):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_idempotency_key"),
    )

    id: int | None = Field(default=None, primary_key=True)
    idempotency_key: str = Field(index=True)
    endpoint: str                          # e.g. "POST /v1/payments/payment-link"
    user_id: str                           # scoped per user
    status_code: int = 200
    response_body: str = ""                # JSON-serialized response
    created_at: datetime = Field(default_factory=utc_now)

    # Auto-expire after 24h for cleanup (enforced in query, not TTL)
    expires_at: datetime | None = None
