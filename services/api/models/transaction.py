from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


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

    id: Optional[int] = Field(default=None, primary_key=True)
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
    buyer_id: Optional[str] = Field(
        default=None, index=True,
        foreign_key="users.user_id",
    )

    # Buyer intent
    buyer_intent: str = ""
    parsed_constraints: str = "{}"  # JSON

    # Merchant/product selection
    merchant_id: Optional[str] = Field(
        default=None, index=True,
        foreign_key="merchants.merchant_id",
    )
    merchant_name: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    amount_inr: Optional[int] = None  # Final approved amount

    # Comparison results (JSON)
    candidates_json: str = "[]"
    selected_reason: str = ""

    # Policy decision
    policy_result: Optional[str] = None  # ALLOW / DENY / NEEDS_APPROVAL
    policy_reason_codes: str = "[]"  # JSON

    # Approval
    approval_id: Optional[str] = None
    approved_by: Optional[str] = "buyer"
    approved_at: Optional[datetime] = None

    # Razorpay
    razorpay_payment_link_id: Optional[str] = None
    razorpay_payment_link_url: Optional[str] = None
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None

    # Transaction fingerprint (idempotency)
    fingerprint: Optional[str] = None

    # State machine
    state: TransactionState = TransactionState.DRAFT

    # Recovery
    recovery_action: Optional[str] = None
    failure_reason: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
