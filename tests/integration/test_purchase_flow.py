"""
Integration test — complete purchase flows:
1. Auto-approved flow (within spending limit)
2. Approval-required flow (over auto-limit)
3. Blocked flow (merchant inactive)
4. Duplicate payment link request (idempotent)

Uses the shared conftest.py fixtures (StaticPool in-memory engine + setup_db).
Do NOT override app.dependency_overrides or create a module-level engine here —
doing so pollutes the shared app singleton and breaks subsequent test modules.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

# Import models and app via conftest-provided fixtures; do NOT import here directly
# to avoid triggering a second dependency_overrides assignment.
import models  # noqa — ensures all SQLModel metadata is registered


@pytest.fixture
def seeded_merchant(session):
    """Insert test merchant + products using the shared session fixture."""
    from models.merchant import Merchant, Product

    m = Merchant(
        merchant_id="int_merch_01", name="IntegrationMart",
        currency="INR",
        max_autonomous_spend_inr=500,
        approval_threshold_inr=1500,
        restricted_categories="[]",
        is_active=True,
    )
    session.add(m)

    session.add(Product(
        product_id="int_prod_cheap", merchant_id="int_merch_01",
        name="Cheap Item", category="grocery", price_inr=299,
        inventory_count=10, availability=True, merchant_rating=4.5,
        delivery_sla_days_min=1, delivery_sla_days_max=3,
    ))
    session.add(Product(
        product_id="int_prod_expensive", merchant_id="int_merch_01",
        name="Expensive Item", category="grocery", price_inr=699,
        inventory_count=5, availability=True, merchant_rating=4.5,
        delivery_sla_days_min=1, delivery_sla_days_max=3,
    ))
    session.commit()
    return m


class TestAutoApprovedFlow:
    def test_cheap_product_gets_allow(self, client, seeded_merchant):
        """Product within auto-limit should get ALLOW without approval."""
        r = client.post("/v1/transactions/intent", json={"message": "buy cheap grocery"})
        assert r.status_code == 200
        txn_id = r.json()["transaction_id"]

        r = client.post("/v1/transactions/select", json={
            "transaction_id": txn_id,
            "product_id": "int_prod_cheap",
            "merchant_id": "int_merch_01",
        })
        assert r.status_code == 200

        r = client.post("/v1/payments/payment-link", json={"transaction_id": txn_id})
        # 502 = Razorpay demo key fails (expected in test mode); not a DENY
        assert r.status_code in (200, 400, 502)
        data = r.json()
        if r.status_code == 200:
            assert data.get("needs_approval") is False or data.get("needs_approval") is None


class TestApprovalRequiredFlow:
    def test_expensive_product_needs_approval(self, client, seeded_merchant):
        """Product above auto-limit should require approval."""
        r = client.post("/v1/transactions/intent", json={"message": "buy expensive item"})
        assert r.status_code == 200
        txn_id = r.json()["transaction_id"]

        r = client.post("/v1/transactions/select", json={
            "transaction_id": txn_id,
            "product_id": "int_prod_expensive",
            "merchant_id": "int_merch_01",
        })
        assert r.status_code == 200

        r = client.post("/v1/payments/payment-link", json={"transaction_id": txn_id})
        assert r.status_code == 200
        data = r.json()
        assert data["needs_approval"] is True
        assert data["state"] == "PENDING_APPROVAL"

    def test_approval_then_payment_allowed(self, client, seeded_merchant):
        """After buyer approves, payment should be allowed."""
        r = client.post("/v1/transactions/intent", json={"message": "buy expensive"})
        txn_id = r.json()["transaction_id"]

        client.post("/v1/transactions/select", json={
            "transaction_id": txn_id,
            "product_id": "int_prod_expensive",
            "merchant_id": "int_merch_01",
        })

        r = client.post("/v1/transactions/approve", json={
            "transaction_id": txn_id,
            "approved_by": "buyer",
        })
        assert r.status_code == 200
        assert r.json()["state"] == "APPROVED"

        # With demo keys, Razorpay will fail → 502 is expected
        r = client.post("/v1/payments/payment-link", json={"transaction_id": txn_id})
        assert r.status_code in (200, 502)


class TestBlockedFlow:
    def test_inactive_merchant_blocked(self, client, session):
        """Inactive merchant products should be DENIED."""
        from models.merchant import Merchant, Product

        m = Merchant(
            merchant_id="inactive_merch", name="Inactive",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=False,
        )
        session.add(m)
        session.add(Product(
            product_id="inactive_prod", merchant_id="inactive_merch",
            name="Item", category="grocery", price_inr=100,
            inventory_count=5, availability=True, merchant_rating=4.0,
        ))
        session.commit()

        r = client.post("/v1/transactions/intent", json={"message": "buy from inactive"})
        txn_id = r.json()["transaction_id"]
        client.post("/v1/transactions/select", json={
            "transaction_id": txn_id,
            "product_id": "inactive_prod",
            "merchant_id": "inactive_merch",
        })

        r = client.post("/v1/payments/payment-link", json={"transaction_id": txn_id})
        assert r.status_code == 403
        body = r.json()
        assert "POLICY_BLOCKED" in str(body) or "MERCHANT_INACTIVE" in str(body)


class TestIdempotency:
    def test_duplicate_payment_link_request_returns_same(self, client, session, seeded_merchant):
        """Second payment-link request for same transaction should return existing link."""
        from models.transaction import Transaction, TransactionState

        txn = Transaction(
            buyer_intent="test",
            merchant_id="int_merch_01",
            product_id="int_prod_cheap",
            amount_inr=299,
            merchant_name="IntegrationMart",
            product_name="Cheap Item",
            razorpay_payment_link_id="plink_existing_001",
            razorpay_payment_link_url="https://rzp.io/test",
            state=TransactionState.PAYMENT_LINK_CREATED,
        )
        session.add(txn)
        session.commit()
        session.refresh(txn)
        txn_id = txn.transaction_id

        r = client.post("/v1/payments/payment-link", json={"transaction_id": txn_id})
        assert r.status_code == 200
        data = r.json()
        assert data["idempotent"] is True
        assert data["payment_link_id"] == "plink_existing_001"
