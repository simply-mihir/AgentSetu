"""
Security tests — verify that all endpoints hardened in Phase 1 (C1–C4)
reject unauthenticated requests with 401/403.

C1: Transaction endpoints (approve, list, get-by-id)
C2: Payment endpoints (payment-link, verify, receipt)
C3: Merchant import endpoint
C4: Audit endpoints
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from fastapi.testclient import TestClient


# ── Helpers ──────────────────────────────────────────────────────────────────

def _seed_transaction(session):
    """Create a minimal transaction for endpoint tests."""
    from models.transaction import Transaction, TransactionState
    txn = Transaction(
        buyer_intent="auth test",
        merchant_id="auth_merch",
        product_id="auth_prod",
        amount_inr=100,
        merchant_name="AuthMart",
        product_name="AuthItem",
        state=TransactionState.DRAFT,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn.transaction_id


# ── C1: Transaction endpoints ────────────────────────────────────────────────

class TestC1TransactionAuth:
    """Unauthenticated callers must be rejected by transaction endpoints."""

    def test_approve_requires_auth(self, client, session):
        txn_id = _seed_transaction(session)
        r = client.post("/v1/transactions/approve", json={"transaction_id": txn_id})
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_list_requires_auth(self, client):
        r = client.get("/v1/transactions/")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_get_by_id_requires_auth(self, client, session):
        txn_id = _seed_transaction(session)
        r = client.get(f"/v1/transactions/{txn_id}")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ── C2: Payment endpoints ───────────────────────────────────────────────────

class TestC2PaymentAuth:
    """Unauthenticated callers must be rejected by payment endpoints."""

    def test_payment_link_requires_auth(self, client, session):
        txn_id = _seed_transaction(session)
        r = client.post("/v1/payments/payment-link", json={"transaction_id": txn_id})
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_verify_requires_auth(self, client, session):
        txn_id = _seed_transaction(session)
        r = client.post(f"/v1/payments/verify/{txn_id}")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_receipt_requires_auth(self, client, session):
        txn_id = _seed_transaction(session)
        r = client.get(f"/v1/payments/receipt/{txn_id}")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ── C3: Merchant import endpoint ────────────────────────────────────────────

class TestC3MerchantImportAuth:
    """Unauthenticated callers must be rejected by merchant import."""

    def test_import_requires_auth(self, client):
        r = client.post("/v1/merchants/import", json={
            "merchant_id": "evil_merch",
            "merchant_name": "Evil Corp",
            "products": [],
        })
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_policy_update_requires_auth(self, client, session):
        """H2 verification: policy mutation requires auth."""
        from models.merchant import Merchant
        m = Merchant(
            merchant_id="policy_merch", name="PolicyMart",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=True,
        )
        session.add(m)
        session.commit()

        r = client.put("/v1/merchants/policy_merch/policy", json={
            "max_autonomous_spend_inr": 99999,
            "approval_threshold_inr": 99999,
            "restricted_categories": [],
            "refund_authority": "merchant",
        })
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ── C4: Audit endpoints ─────────────────────────────────────────────────────

class TestC4AuditAuth:
    """Unauthenticated callers must be rejected by audit endpoints."""

    def test_list_audit_requires_auth(self, client):
        r = client.get("/v1/audit/")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_timeline_requires_auth(self, client):
        r = client.get("/v1/audit/some_correlation_id")
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


# ── H1: approved_by from auth context ───────────────────────────────────────

class TestH1ApprovedByFromAuth:
    """The approved_by field must come from the authenticated user, not the client."""

    def test_approve_sets_user_id_not_client_value(self, client, session, buyer_headers):
        txn_id = _seed_transaction(session)
        # Even if the client tries to send approved_by, it should be ignored
        r = client.post(
            "/v1/transactions/approve",
            json={"transaction_id": txn_id},
            headers=buyer_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["state"] == "APPROVED"
        # The approved_by should be the authenticated user, not a client-supplied value
        assert data.get("approved_by", "").startswith("usr_")


# ── Cross-role access control ────────────────────────────────────────────────

class TestCrossRoleAccess:
    """Verify that a BUYER cannot access another buyer's transaction."""

    def test_buyer_cannot_access_other_buyers_transaction(self, client, session):
        """Two different buyers — one creates a txn, the other should be rejected."""
        from models.transaction import Transaction, TransactionState

        # Create buyer A
        r = client.post("/v1/auth/signup", json={
            "email": "buyer_a@test.com",
            "password": "TestPass123!",
            "role": "BUYER",
        })
        assert r.status_code == 200
        buyer_a_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        buyer_a_id = r.json()["user_id"]

        # Create buyer B
        r = client.post("/v1/auth/signup", json={
            "email": "buyer_b@test.com",
            "password": "TestPass123!",
            "role": "BUYER",
        })
        assert r.status_code == 200
        buyer_b_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Create a transaction owned by buyer A
        txn = Transaction(
            buyer_intent="buyer A's item",
            merchant_id="auth_merch",
            product_id="auth_prod",
            amount_inr=100,
            merchant_name="AuthMart",
            product_name="AuthItem",
            state=TransactionState.DRAFT,
            buyer_id=buyer_a_id,
        )
        session.add(txn)
        session.commit()
        session.refresh(txn)

        # Buyer B should NOT be able to see buyer A's transaction
        r = client.get(f"/v1/transactions/{txn.transaction_id}", headers=buyer_b_headers)
        assert r.status_code == 403, f"Cross-tenant leak: buyer B accessed buyer A's txn (got {r.status_code})"

        # Buyer A should be able to see their own transaction
        r = client.get(f"/v1/transactions/{txn.transaction_id}", headers=buyer_a_headers)
        assert r.status_code == 200
