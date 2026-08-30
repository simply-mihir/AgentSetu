"""
Security tests — cross-tenant access attempts.
No merchant A should be able to read or modify merchant B's data.
Uses shared conftest.py fixtures.
"""
import sys
import os
# Env vars must be set BEFORE importing app modules
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_agentsetu.db")
os.environ.setdefault("APP_MODE", "demo")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
import json
import hmac
import hashlib
from fastapi.testclient import TestClient
from sqlmodel import Session


def signup_and_get_token(client: TestClient, email: str, role: str = "MERCHANT_OWNER") -> str:
    r = client.post("/v1/auth/signup", json={"email": email, "password": "Pass123!", "role": role})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


class TestCrossTenantPolicyUpdate:
    def test_merchant_cannot_update_other_merchants_policy(self, client, session):
        """Merchant A must not be able to update Merchant B's policy."""
        from models.merchant import Merchant
        from models.merchant_user import MerchantUser, MerchantUserRole
        from models.user import User
        from sqlmodel import select

        # Create two merchants
        m_a = Merchant(
            merchant_id="merch_a", name="Merchant A",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]",
        )
        m_b = Merchant(
            merchant_id="merch_b", name="Merchant B",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]",
        )
        session.add(m_a)
        session.add(m_b)
        session.commit()

        # Register user for merchant A
        token_a = signup_and_get_token(client, "owner_a@test.com", "MERCHANT_OWNER")

        # Find user_a
        user_a = session.exec(select(User).where(User.email == "owner_a@test.com")).first()
        assert user_a is not None

        # Give user_a access to merch_a ONLY
        mu = MerchantUser(merchant_id="merch_a", user_id=user_a.user_id, role=MerchantUserRole.OWNER)
        session.add(mu)
        session.commit()

        # user_a tries to update merch_b's policy — must be 403
        resp = client.put(
            "/v1/merchants/merch_b/policy",
            json={
                "max_autonomous_spend_inr": 9999,
                "approval_threshold_inr": 9999,
                "restricted_categories": [],
                "refund_authority": "human_only",
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert resp.status_code in (401, 403), (
            f"Expected 403 but got {resp.status_code}: {resp.text}"
        )


class TestWebhookReplay:
    def test_duplicate_webhook_is_harmless(self, client, session):
        """Same webhook event ID submitted twice must not double-process."""
        from models.merchant import Merchant, Product
        from models.transaction import Transaction, TransactionState

        m = Merchant(
            merchant_id="merch_wh", name="WH Merchant",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]",
        )
        session.add(m)
        p = Product(
            product_id="prod_wh", merchant_id="merch_wh",
            name="WH Product", category="grocery", price_inr=200,
            inventory_count=5, availability=True, merchant_rating=4.0,
        )
        session.add(p)
        txn = Transaction(
            buyer_intent="test webhook",
            merchant_id="merch_wh", product_id="prod_wh", amount_inr=200,
            merchant_name="WH Merchant", product_name="WH Product",
            razorpay_payment_link_id="plink_test123",
            state=TransactionState.PAYMENT_LINK_CREATED,
        )
        session.add(txn)
        session.commit()
        session.refresh(txn)

        # Build fake Razorpay webhook
        body = json.dumps({
            "id": "evt_unique_001",      # Same event ID for both requests
            "event": "payment_link.paid",
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": "plink_test123",
                        "reference_id": txn.transaction_id,
                        "status": "paid",
                    }
                }
            }
        }).encode()

        # Use the same webhook secret as the test environment
        webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret").encode()
        sig = hmac.new(webhook_secret, body, hashlib.sha256).hexdigest()
        headers = {"X-Razorpay-Signature": sig, "Content-Type": "application/json"}

        # First webhook — process
        r1 = client.post("/v1/webhooks/razorpay", content=body, headers=headers)
        assert r1.status_code == 200
        assert r1.json().get("duplicate") is not True

        # Second webhook — same event ID — must be DUPLICATE
        r2 = client.post("/v1/webhooks/razorpay", content=body, headers=headers)
        assert r2.status_code == 200
        assert r2.json().get("duplicate") is True


class TestInvalidWebhookSignature:
    def test_invalid_signature_rejected(self, client):
        body = b'{"event": "payment_link.paid", "id": "evt_bad_sig"}'
        headers = {"X-Razorpay-Signature": "badhash", "Content-Type": "application/json"}
        resp = client.post("/v1/webhooks/razorpay", content=body, headers=headers)
        assert resp.status_code == 400
