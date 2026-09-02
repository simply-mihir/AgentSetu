"""
Phase 20: Commerce Receipt Tests
Tests machine-readable receipt structure, hash integrity, and access control.
"""
import pytest
import json
import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))


@pytest.fixture
def receipt_setup(client, session):
    """Set up a transaction through to APPROVED state for receipt testing."""
    from models.merchant import Merchant, Product
    from models.transaction import Transaction, TransactionState
    from models.user import User, UserRole, UserStatus, BuyerProfile
    from models.merchant_user import MerchantUser

    # Create merchant
    merchant = Merchant(
        merchant_id="rcpt_merchant_01",
        name="ReceiptMart",
        currency="INR",
        category="grocery",
        max_autonomous_spend_inr=500,
        approval_threshold_inr=1500,
        restricted_categories="[]",
        is_active=True,
    )
    session.add(merchant)

    product = Product(
        product_id="rcpt_prod_01",
        merchant_id="rcpt_merchant_01",
        name="Organic Rice 5kg",
        category="grocery",
        price_inr=350,
        inventory_count=10,
        availability=True,
        delivery_sla_days_min=1,
        delivery_sla_days_max=3,
        return_policy="7_days",
        merchant_rating=4.5,
    )
    session.add(product)
    session.commit()

    # Register buyer
    resp = client.post("/v1/auth/signup", json={
        "email": "rcpt_buyer@test.com",
        "password": "TestPass123!",
        "role": "BUYER",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    user_id = resp.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a transaction manually
    txn = Transaction(
        buyer_id=user_id,
        buyer_intent="I want organic rice under 400",
        parsed_constraints=json.dumps({"category": "grocery", "max_budget_inr": 400}),
        merchant_id="rcpt_merchant_01",
        merchant_name="ReceiptMart",
        product_id="rcpt_prod_01",
        product_name="Organic Rice 5kg",
        amount_inr=350,
        state=TransactionState.RECEIPT_ISSUED,
        policy_result="ALLOW",
        policy_reason_codes=json.dumps(["WITHIN_AUTO_LIMIT"]),
        approval_id="appr_test123",
        approved_by=user_id,
        razorpay_payment_link_id="plink_test_123",
        razorpay_payment_link_url="https://rzp.io/test",
        fingerprint="abc123def456",
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    # Add audit events
    from models.audit import AuditEvent
    for i, evt_type in enumerate(["intent.received", "catalog.discovered", "policy.decision", "payment.created", "receipt.issued"]):
        event = AuditEvent(
            transaction_id=txn.transaction_id,
            correlation_id=txn.correlation_id,
            actor="agentsetu" if i > 0 else user_id,
            event_type=evt_type,
            decision="ALLOW" if "policy" in evt_type else None,
            reason_codes=json.dumps(["WITHIN_AUTO_LIMIT"]) if "policy" in evt_type else "[]",
            result="ok",
            next_state="RECEIPT_ISSUED" if i == 4 else None,
        )
        session.add(event)
    session.commit()

    return {
        "txn": txn,
        "headers": headers,
        "user_id": user_id,
    }


class TestCommerceReceipt:
    """Receipt should be a complete, hash-verifiable record."""

    def test_receipt_has_version_and_schema(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["receipt"]["receipt_version"] == "1.0"
        assert body["receipt"]["schema"] == "agentsetu-receipt-v1"

    def test_receipt_has_buyer_and_merchant(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        assert receipt["buyer"]["buyer_id"] == receipt_setup["user_id"]
        assert receipt["merchant"]["merchant_id"] == "rcpt_merchant_01"
        assert receipt["merchant"]["name"] == "ReceiptMart"
        assert receipt["merchant"]["category"] == "grocery"

    def test_receipt_has_line_items(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        items = receipt["line_items"]
        assert len(items) == 1
        assert items[0]["product_id"] == "rcpt_prod_01"
        assert items[0]["name"] == "Organic Rice 5kg"
        assert items[0]["unit_price_inr"] == 350
        assert items[0]["quantity"] == 1
        assert items[0]["return_policy"] == "7_days"
        assert items[0]["delivery_sla_days"] == [1, 3]

    def test_receipt_has_total(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        assert receipt["total_amount_inr"] == 350
        assert receipt["currency"] == "INR"

    def test_receipt_has_policy_chain(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        assert receipt["policy"]["decision"] == "ALLOW"
        assert "WITHIN_AUTO_LIMIT" in receipt["policy"]["reason_codes"]

    def test_receipt_has_approval(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        assert receipt["approval"]["approval_id"] == "appr_test123"
        assert receipt["approval"]["approved_by"] == receipt_setup["user_id"]

    def test_receipt_has_payment_details(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        assert receipt["payment"]["provider"] == "razorpay"
        assert receipt["payment"]["payment_link_id"] == "plink_test_123"

    def test_receipt_hash_is_verifiable(self, client, receipt_setup):
        """receipt_hash should match SHA-256 of receipt payload."""
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        body = resp.json()
        receipt = body["receipt"]
        reported_hash = body["receipt_hash"]

        recomputed = hashlib.sha256(
            json.dumps(receipt, sort_keys=True, default=str).encode()
        ).hexdigest()
        assert reported_hash == recomputed

    def test_receipt_has_audit_trail(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        body = resp.json()
        assert len(body["audit_trail"]) == 5
        event_types = [e["event_type"] for e in body["audit_trail"]]
        assert "intent.received" in event_types
        assert "policy.decision" in event_types
        assert "receipt.issued" in event_types

    def test_receipt_has_fingerprint(self, client, receipt_setup):
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=receipt_setup["headers"],
        )
        receipt = resp.json()["receipt"]
        assert receipt["fingerprint"] == "abc123def456"

    def test_receipt_requires_auth(self, client, receipt_setup):
        """Receipt must not be accessible without auth."""
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
        )
        assert resp.status_code == 401

    def test_receipt_cross_buyer_blocked(self, client, receipt_setup):
        """Another buyer should not see this receipt."""
        resp = client.post("/v1/auth/signup", json={
            "email": "other_buyer_rcpt@test.com",
            "password": "TestPass123!",
            "role": "BUYER",
        })
        other_headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        resp = client.get(
            f"/v1/payments/receipt/{receipt_setup['txn'].transaction_id}",
            headers=other_headers,
        )
        assert resp.status_code == 403
