"""
Phase 4 — Capability hardening tests.
Verify buyer_id binding and consume-with-lock behavior.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from datetime import datetime, timedelta
from utils.time import utc_now
from capability.service import capability_service
from models.capability import AuthorizationCapability, CapabilityStatus


class TestBuyerIdBinding:
    """Capabilities should validate buyer_id when provided."""

    def test_consume_with_matching_buyer_succeeds(self, session):
        cap = capability_service.issue_capability(
            session, transaction_id="txn_b1", merchant_id="m1",
            product_id="p1", amount_inr=100, buyer_id="buyer_a",
        )
        ok, reason = capability_service.consume_capability(
            session, cap.capability_id, "txn_b1", "m1", 100, buyer_id="buyer_a",
        )
        assert ok
        assert reason == "OK"

    def test_consume_with_wrong_buyer_fails(self, session):
        cap = capability_service.issue_capability(
            session, transaction_id="txn_b2", merchant_id="m1",
            product_id="p1", amount_inr=100, buyer_id="buyer_a",
        )
        ok, reason = capability_service.consume_capability(
            session, cap.capability_id, "txn_b2", "m1", 100, buyer_id="buyer_b",
        )
        assert not ok
        assert reason == "CAPABILITY_BUYER_MISMATCH"

    def test_consume_without_buyer_skips_buyer_check(self, session):
        """Legacy path: no buyer_id on consume still works."""
        cap = capability_service.issue_capability(
            session, transaction_id="txn_b3", merchant_id="m1",
            product_id="p1", amount_inr=100, buyer_id="buyer_a",
        )
        ok, reason = capability_service.consume_capability(
            session, cap.capability_id, "txn_b3", "m1", 100,
        )
        assert ok

    def test_consume_with_no_cap_buyer_allows_any(self, session):
        """If capability has no buyer_id, any buyer can consume."""
        cap = capability_service.issue_capability(
            session, transaction_id="txn_b4", merchant_id="m1",
            product_id="p1", amount_inr=100, buyer_id=None,
        )
        ok, reason = capability_service.consume_capability(
            session, cap.capability_id, "txn_b4", "m1", 100, buyer_id="any_buyer",
        )
        assert ok


class TestConsumeAtomicity:
    """Double-consume must fail even under (simulated) concurrency."""

    def test_second_consume_fails(self, session):
        cap = capability_service.issue_capability(
            session, transaction_id="txn_a1", merchant_id="m1",
            product_id="p1", amount_inr=200,
        )
        ok1, _ = capability_service.consume_capability(
            session, cap.capability_id, "txn_a1", "m1", 200,
        )
        assert ok1

        ok2, reason = capability_service.consume_capability(
            session, cap.capability_id, "txn_a1", "m1", 200,
        )
        assert not ok2
        assert reason == "CAPABILITY_CONSUMED"


class TestExpiredCapabilityConsume:
    """Consuming an expired capability through the new path still fails."""

    def test_expired_during_consume_rejected(self, session):
        cap = capability_service.issue_capability(
            session, transaction_id="txn_e1", merchant_id="m1",
            product_id="p1", amount_inr=100, ttl_minutes=0,
        )
        # Force expiry
        refreshed = session.get(AuthorizationCapability, cap.id)
        refreshed.expires_at = utc_now() - timedelta(seconds=1)
        session.add(refreshed)
        session.commit()

        ok, reason = capability_service.consume_capability(
            session, cap.capability_id, "txn_e1", "m1", 100,
        )
        assert not ok
        assert reason == "CAPABILITY_EXPIRED"
