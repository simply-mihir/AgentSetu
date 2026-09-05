import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from utils.time import utc_now


class TransactionState(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CANCELLED = "CANCELLED"
    PAYMENT_LINK_CREATED = "PAYMENT_LINK_CREATED"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_UNKNOWN = "PAYMENT_UNKNOWN"
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFIED_FAILED = "VERIFIED_FAILED"
    RECEIPT_ISSUED = "RECEIPT_ISSUED"
    RECOVERY_PROPOSED = "RECOVERY_PROPOSED"


# ── Allowed state transitions ────────────────────────────────────────────────
# Phase 5: explicit transition map — any transition not listed here is illegal.
ALLOWED_TRANSITIONS: dict[TransactionState, set[TransactionState]] = {
    TransactionState.DRAFT: {
        TransactionState.PENDING_APPROVAL,
        TransactionState.APPROVED,
        TransactionState.CANCELLED,
    },
    TransactionState.PENDING_APPROVAL: {
        TransactionState.APPROVED,
        TransactionState.CANCELLED,
        TransactionState.PAYMENT_LINK_CREATED,  # auto-approved path
    },
    TransactionState.APPROVED: {
        TransactionState.PAYMENT_LINK_CREATED,
        TransactionState.CANCELLED,
        TransactionState.DRAFT,  # price change → reset to DRAFT
    },
    TransactionState.PAYMENT_LINK_CREATED: {
        TransactionState.PAYMENT_SUCCESS,
        TransactionState.PAYMENT_FAILED,
        TransactionState.PAYMENT_UNKNOWN,
        TransactionState.CANCELLED,  # Phase 8: user/merchant can cancel unpaid link
    },
    TransactionState.PAYMENT_SUCCESS: {
        TransactionState.RECEIPT_ISSUED,
    },
    TransactionState.PAYMENT_FAILED: {
        TransactionState.RECOVERY_PROPOSED,
    },
    TransactionState.PAYMENT_UNKNOWN: {
        TransactionState.RECOVERY_PROPOSED,
        TransactionState.PAYMENT_SUCCESS,  # resolved via webhook/verify
        TransactionState.PAYMENT_FAILED,
    },
    TransactionState.RECEIPT_ISSUED: set(),  # terminal
    TransactionState.RECOVERY_PROPOSED: set(),  # terminal (buyer starts new txn)
    TransactionState.CANCELLED: set(),  # terminal
    TransactionState.VERIFIED_SUCCESS: set(),  # legacy
    TransactionState.VERIFIED_FAILED: set(),  # legacy
}


def validate_transition(current: TransactionState, target: TransactionState) -> bool:
    """Return True if the transition from current → target is legal."""
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    return target in allowed


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: int | None = Field(default=None, primary_key=True)
    transaction_id: str = Field(
        default_factory=lambda: f"txn_{uuid.uuid4().hex[:8]}",
        unique=True,
        index=True
    )
    correlation_id: str = Field(
        default_factory=lambda: f"tx_{uuid.uuid4().hex[:10]}",
        index=True
    )

    # Buyer identity — set from auth context, never from client
    buyer_id: str | None = Field(
        default=None, index=True,
        foreign_key="users.user_id",
    )

    # Buyer intent
    buyer_intent: str = ""
    parsed_constraints: str = "{}"  # JSON

    # Merchant/product selection
    merchant_id: str | None = Field(
        default=None, index=True,
        foreign_key="merchants.merchant_id",
    )
    merchant_name: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    amount_inr: int | None = None  # Final approved amount

    # Comparison results (JSON)
    candidates_json: str = "[]"
    selected_reason: str = ""

    # Policy decision
    policy_result: str | None = None  # ALLOW / DENY / NEEDS_APPROVAL
    policy_reason_codes: str = "[]"  # JSON

    # Approval
    approval_id: str | None = None
    approved_by: str | None = "buyer"
    approved_at: datetime | None = None

    # Razorpay
    razorpay_payment_link_id: str | None = None
    razorpay_payment_link_url: str | None = None
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None

    # Transaction fingerprint (idempotency)
    fingerprint: str | None = None

    # State machine
    state: TransactionState = TransactionState.DRAFT

    # Recovery
    recovery_action: str | None = None
    failure_reason: str | None = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
