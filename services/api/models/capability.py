"""
Authorization Capability model.
A capability is a bounded, one-time, expiring authorization token
that gates payment execution. It cannot be replayed or transferred.
"""
import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from utils.time import utc_now


class CapabilityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CONSUMED = "CONSUMED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class AuthorizationCapability(SQLModel, table=True):
    __tablename__ = "authorization_capabilities"

    id: int | None = Field(default=None, primary_key=True)
    capability_id: str = Field(
        default_factory=lambda: f"cap_{uuid.uuid4().hex[:16]}",
        unique=True,
        index=True,
    )

    # Binding — must all match at consumption time
    buyer_id: str | None = Field(default=None, index=True)    # user_id
    merchant_id: str = Field(index=True)
    product_id: str
    transaction_id: str = Field(index=True)
    approval_id: str | None = None

    # Amount binding
    amount_inr: int
    currency: str = "INR"

    # Cryptographic proof
    nonce: str = Field(default_factory=lambda: uuid.uuid4().hex)
    payload_hash: str = ""     # SHA-256 of canonical payload

    # Lifecycle
    status: CapabilityStatus = CapabilityStatus.ACTIVE
    expires_at: datetime
    consumed_at: datetime | None = None
    revoked_at: datetime | None = None
    revoke_reason: str | None = None

    created_at: datetime = Field(default_factory=utc_now)
