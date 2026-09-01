"""
Authorization Capability Service.

A capability is a bounded, one-time, expiring token that permits exactly ONE
payment execution. It cannot be replayed, transferred, or exceed the approved amount.

Rules:
- Issued only after policy ALLOW or explicit buyer approval.
- Expires in 15 minutes by default (configurable).
- Consumed exactly once; second consume raises CAPABILITY_CONSUMED.
- Revoked immediately on price change, inventory change, or order mutation.
- Payment execution MUST validate a capability before calling Razorpay.
"""
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session, select

from models.capability import AuthorizationCapability, CapabilityStatus

logger = logging.getLogger(__name__)

CAPABILITY_TTL_MINUTES = 15


def _canonical_payload(cap: AuthorizationCapability) -> str:
    """Deterministic JSON string for hashing."""
    return json.dumps({
        "buyer_id": cap.buyer_id,
        "merchant_id": cap.merchant_id,
        "product_id": cap.product_id,
        "transaction_id": cap.transaction_id,
        "amount_inr": cap.amount_inr,
        "currency": cap.currency,
        "nonce": cap.nonce,
        "approval_id": cap.approval_id,
    }, sort_keys=True)


class CapabilityService:

    def issue_capability(
        self,
        session: Session,
        transaction_id: str,
        merchant_id: str,
        product_id: str,
        amount_inr: int,
        approval_id: Optional[str] = None,
        buyer_id: Optional[str] = None,
        ttl_minutes: int = CAPABILITY_TTL_MINUTES,
    ) -> AuthorizationCapability:
        """
        Issue a new capability for a specific approved transaction.
        Revokes any previously active capability for the same transaction.
        """
        # Revoke existing active capability for this transaction
        existing = session.exec(
            select(AuthorizationCapability).where(
                AuthorizationCapability.transaction_id == transaction_id,
                AuthorizationCapability.status == CapabilityStatus.ACTIVE,
            )
        ).first()
        if existing:
            self.revoke_capability(session, existing.capability_id, reason="superseded")

        cap = AuthorizationCapability(
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            transaction_id=transaction_id,
            approval_id=approval_id,
            amount_inr=amount_inr,
            expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )
        # Compute payload hash for integrity
        cap.payload_hash = hashlib.sha256(_canonical_payload(cap).encode()).hexdigest()

        session.add(cap)
        session.commit()
        session.refresh(cap)
        logger.info(f"Capability issued: {cap.capability_id} | txn={transaction_id} | amount=₹{amount_inr}")
        return cap

    def validate_capability(
        self,
        session: Session,
        capability_id: str,
        transaction_id: str,
        merchant_id: str,
        amount_inr: int,
    ) -> tuple[bool, str]:
        """
        Validate a capability.
        Returns (is_valid, reason).
        Does NOT consume — call consume_capability() separately.
        """
        cap = session.exec(
            select(AuthorizationCapability).where(
                AuthorizationCapability.capability_id == capability_id
            )
        ).first()

        if not cap:
            return False, "CAPABILITY_NOT_FOUND"

        if cap.status == CapabilityStatus.CONSUMED:
            return False, "CAPABILITY_CONSUMED"

        if cap.status == CapabilityStatus.REVOKED:
            return False, "CAPABILITY_REVOKED"

        if cap.status == CapabilityStatus.EXPIRED or datetime.utcnow() > cap.expires_at:
            # Lazily mark expired
            if cap.status == CapabilityStatus.ACTIVE:
                cap.status = CapabilityStatus.EXPIRED
                session.add(cap)
                session.commit()
            return False, "CAPABILITY_EXPIRED"

        # Binding checks
        if cap.transaction_id != transaction_id:
            return False, "CAPABILITY_TRANSACTION_MISMATCH"

        if cap.merchant_id != merchant_id:
            return False, "CAPABILITY_MERCHANT_MISMATCH"

        if cap.amount_inr != amount_inr:
            return False, "CAPABILITY_AMOUNT_MISMATCH"

        return True, "OK"

    def consume_capability(
        self,
        session: Session,
        capability_id: str,
        transaction_id: str,
        merchant_id: str,
        amount_inr: int,
        buyer_id: Optional[str] = None,
    ) -> tuple[bool, str]:
        """
        Validate and atomically consume a capability.
        Returns (success, reason). Second call always returns False, "CAPABILITY_CONSUMED".

        Uses SELECT ... FOR UPDATE on PostgreSQL for row-level locking to prevent
        double-consume under concurrent requests. Safe no-op on SQLite.
        """
        # Row-level lock: FOR UPDATE prevents two concurrent requests from both
        # reading ACTIVE and both writing CONSUMED.
        cap = session.exec(
            select(AuthorizationCapability)
            .where(AuthorizationCapability.capability_id == capability_id)
            .with_for_update()
        ).first()

        if not cap:
            return False, "CAPABILITY_NOT_FOUND"

        if cap.status == CapabilityStatus.CONSUMED:
            return False, "CAPABILITY_CONSUMED"

        if cap.status == CapabilityStatus.REVOKED:
            return False, "CAPABILITY_REVOKED"

        if cap.status == CapabilityStatus.EXPIRED or datetime.utcnow() > cap.expires_at:
            if cap.status == CapabilityStatus.ACTIVE:
                cap.status = CapabilityStatus.EXPIRED
                session.add(cap)
                session.flush()
            return False, "CAPABILITY_EXPIRED"

        # Binding checks
        if cap.transaction_id != transaction_id:
            return False, "CAPABILITY_TRANSACTION_MISMATCH"

        if cap.merchant_id != merchant_id:
            return False, "CAPABILITY_MERCHANT_MISMATCH"

        if cap.amount_inr != amount_inr:
            return False, "CAPABILITY_AMOUNT_MISMATCH"

        # Phase 4: buyer_id binding validation
        if buyer_id and cap.buyer_id and cap.buyer_id != buyer_id:
            return False, "CAPABILITY_BUYER_MISMATCH"

        # Atomically consume
        cap.status = CapabilityStatus.CONSUMED
        cap.consumed_at = datetime.utcnow()
        session.add(cap)
        session.flush()  # flush within transaction — caller commits
        logger.info(f"Capability consumed: {capability_id} | txn={transaction_id}")
        return True, "OK"

    def revoke_capability(
        self,
        session: Session,
        capability_id: str,
        reason: str = "revoked",
    ) -> bool:
        """Revoke a capability. Safe to call on already-revoked/expired capabilities."""
        cap = session.exec(
            select(AuthorizationCapability).where(
                AuthorizationCapability.capability_id == capability_id
            )
        ).first()
        if not cap:
            return False
        if cap.status not in (CapabilityStatus.ACTIVE,):
            return False

        cap.status = CapabilityStatus.REVOKED
        cap.revoked_at = datetime.utcnow()
        cap.revoke_reason = reason
        session.add(cap)
        session.commit()
        logger.info(f"Capability revoked: {capability_id} | reason={reason}")
        return True

    def revoke_for_transaction(
        self,
        session: Session,
        transaction_id: str,
        reason: str = "transaction_mutated",
    ):
        """Revoke all active capabilities for a transaction."""
        caps = session.exec(
            select(AuthorizationCapability).where(
                AuthorizationCapability.transaction_id == transaction_id,
                AuthorizationCapability.status == CapabilityStatus.ACTIVE,
            )
        ).all()
        for cap in caps:
            self.revoke_capability(session, cap.capability_id, reason=reason)


# Singleton
capability_service = CapabilityService()
