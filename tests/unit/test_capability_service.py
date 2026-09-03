"""Unit tests for the CapabilityService."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_cap.db")
os.environ.setdefault("APP_MODE", "demo")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, SQLModel
from utils.time import utc_now
from capability.service import CapabilityService
from models.capability import AuthorizationCapability, CapabilityStatus

TEST_DB = "sqlite:///./test_cap_unit.db"
test_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})

import models  # noqa — registers metadata


@pytest.fixture(autouse=True)
def db():
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def session():
    with Session(test_engine) as s:
        yield s


@pytest.fixture
def svc():
    return CapabilityService()


class TestIssueCapability:
    def test_issue_creates_active_capability(self, svc, session):
        cap = svc.issue_capability(
            session, "txn_01", "merch_01", "prod_01", 299, ttl_minutes=15
        )
        assert cap.capability_id.startswith("cap_")
        assert cap.status == CapabilityStatus.ACTIVE
        assert cap.amount_inr == 299
        assert cap.payload_hash != ""

    def test_issue_revokes_previous_active(self, svc, session):
        cap1 = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        cap2 = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)

        # Reload cap1
        from sqlmodel import select
        refreshed = session.exec(
            select(AuthorizationCapability).where(
                AuthorizationCapability.capability_id == cap1.capability_id
            )
        ).first()
        assert refreshed.status == CapabilityStatus.REVOKED
        assert cap2.status == CapabilityStatus.ACTIVE


class TestConsumeCapability:
    def test_consume_valid_succeeds(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_01", "merch_01", 299)
        assert ok is True
        assert reason == "OK"

    def test_consume_twice_fails(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        svc.consume_capability(session, cap.capability_id, "txn_01", "merch_01", 299)
        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_01", "merch_01", 299)
        assert ok is False
        assert reason == "CAPABILITY_CONSUMED"

    def test_consume_wrong_amount_fails(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_01", "merch_01", 999)
        assert ok is False
        assert reason == "CAPABILITY_AMOUNT_MISMATCH"

    def test_consume_wrong_merchant_fails(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_01", "merch_EVIL", 299)
        assert ok is False
        assert reason == "CAPABILITY_MERCHANT_MISMATCH"

    def test_consume_wrong_transaction_fails(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_DIFFERENT", "merch_01", 299)
        assert ok is False
        assert reason == "CAPABILITY_TRANSACTION_MISMATCH"

    def test_consume_expired_capability_fails(self, svc, session):
        from sqlmodel import select
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299, ttl_minutes=15)
        # Force-expire
        refreshed = session.exec(
            select(AuthorizationCapability).where(
                AuthorizationCapability.capability_id == cap.capability_id
            )
        ).first()
        refreshed.expires_at = utc_now() - timedelta(seconds=1)
        session.add(refreshed)
        session.commit()

        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_01", "merch_01", 299)
        assert ok is False
        assert reason == "CAPABILITY_EXPIRED"

    def test_consume_revoked_capability_fails(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        svc.revoke_capability(session, cap.capability_id, reason="test")
        ok, reason = svc.consume_capability(session, cap.capability_id, "txn_01", "merch_01", 299)
        assert ok is False
        assert reason == "CAPABILITY_REVOKED"


class TestRevokeCapability:
    def test_revoke_active(self, svc, session):
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        result = svc.revoke_capability(session, cap.capability_id, "price_changed")
        assert result is True

    def test_revoke_already_revoked_is_idempotent(self, svc, session):
        """L6 FIX: revoke on already-terminal capability returns True (idempotent)."""
        cap = svc.issue_capability(session, "txn_01", "merch_01", "prod_01", 299)
        svc.revoke_capability(session, cap.capability_id)
        result = svc.revoke_capability(session, cap.capability_id)  # Second call
        assert result is True  # L6: idempotent — already revoked is success
