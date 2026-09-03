"""
Phase 2 — Tenant isolation tests.
Verify that:
1. Unique constraints prevent duplicate MerchantUser memberships
2. Unique constraints prevent duplicate Product records
3. Buyer A cannot list/view Buyer B's transactions
4. Merchant A admin cannot access Merchant B's data
5. Audit events are tenant-scoped
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select


class TestMerchantUserUnique:
    """Duplicate merchant-user memberships must be rejected."""

    def test_duplicate_membership_rejected(self, session):
        from models.merchant import Merchant
        from models.merchant_user import MerchantUser, MerchantUserRole
        from models.user import User, UserRole, UserStatus

        # Create user and merchant
        user = User(
            email="uniq_test@test.com", hashed_password="x",
            role=UserRole.MERCHANT_OWNER, status=UserStatus.ACTIVE,
        )
        session.add(user)
        merchant = Merchant(
            merchant_id="uniq_merch", name="UniqMart",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=True,
        )
        session.add(merchant)
        session.commit()

        # First membership OK
        m1 = MerchantUser(
            merchant_id="uniq_merch", user_id=user.user_id,
            role=MerchantUserRole.OWNER,
        )
        session.add(m1)
        session.commit()

        # Duplicate must fail
        m2 = MerchantUser(
            merchant_id="uniq_merch", user_id=user.user_id,
            role=MerchantUserRole.ADMIN,
        )
        session.add(m2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


class TestProductUnique:
    """Duplicate product_id + merchant_id must be rejected at DB level."""

    def test_duplicate_product_rejected(self, session):
        from models.merchant import Merchant, Product

        merchant = Merchant(
            merchant_id="prod_uniq_merch", name="ProdMart",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=True,
        )
        session.add(merchant)
        session.commit()

        p1 = Product(
            product_id="dup_prod", merchant_id="prod_uniq_merch",
            name="Item A", category="test", price_inr=100,
            inventory_count=5, availability=True, merchant_rating=4.0,
        )
        session.add(p1)
        session.commit()

        p2 = Product(
            product_id="dup_prod", merchant_id="prod_uniq_merch",
            name="Item B", category="test", price_inr=200,
            inventory_count=3, availability=True, merchant_rating=3.5,
        )
        session.add(p2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_same_product_id_different_merchant_ok(self, session):
        """product_id can be reused across different merchants."""
        from models.merchant import Merchant, Product

        for mid in ["cross_merch_a", "cross_merch_b"]:
            session.add(Merchant(
                merchant_id=mid, name=f"Merchant {mid}",
                max_autonomous_spend_inr=500, approval_threshold_inr=1500,
                restricted_categories="[]", is_active=True,
            ))
        session.commit()

        for mid in ["cross_merch_a", "cross_merch_b"]:
            session.add(Product(
                product_id="shared_prod", merchant_id=mid,
                name="Same ID", category="test", price_inr=100,
                inventory_count=5, availability=True, merchant_rating=4.0,
            ))
        session.commit()  # Must not raise

        products = session.exec(
            select(Product).where(Product.product_id == "shared_prod")
        ).all()
        assert len(products) == 2


class TestBuyerTransactionIsolation:
    """Buyer A sees only their own transactions; Buyer B sees only theirs."""

    def test_transaction_list_is_tenant_scoped(self, client, session):
        # Create two buyers
        r = client.post("/v1/auth/signup", json={
            "email": "iso_buyer_a@test.com", "password": "TestPass123!", "role": "BUYER",
        })
        buyer_a = {"Authorization": f"Bearer {r.json()['access_token']}"}

        r = client.post("/v1/auth/signup", json={
            "email": "iso_buyer_b@test.com", "password": "TestPass123!", "role": "BUYER",
        })
        buyer_b = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Buyer A creates an intent (auth required — N1 fix)
        r = client.post("/v1/transactions/intent", json={"message": "buyer a item"}, headers=buyer_a)
        txn_a = r.json()["transaction_id"]
        client.post("/v1/transactions/approve", json={"transaction_id": txn_a}, headers=buyer_a)

        # Buyer B creates an intent
        r = client.post("/v1/transactions/intent", json={"message": "buyer b item"}, headers=buyer_b)
        txn_b = r.json()["transaction_id"]
        client.post("/v1/transactions/approve", json={"transaction_id": txn_b}, headers=buyer_b)

        # Buyer A list should only show their transaction
        r = client.get("/v1/transactions/", headers=buyer_a)
        assert r.status_code == 200
        a_txns = r.json()
        a_ids = {t["transaction_id"] for t in a_txns}
        assert txn_a in a_ids
        assert txn_b not in a_ids

        # Buyer B list should only show their transaction
        r = client.get("/v1/transactions/", headers=buyer_b)
        assert r.status_code == 200
        b_txns = r.json()
        b_ids = {t["transaction_id"] for t in b_txns}
        assert txn_b in b_ids
        assert txn_a not in b_ids


class TestMerchantCrossAccess:
    """Merchant A admin cannot update Merchant B's policy."""

    def test_cross_merchant_policy_rejected(self, client, session):
        from models.merchant import Merchant
        from models.merchant_user import MerchantUser, MerchantUserRole

        # Create two merchants
        for mid, name in [("iso_merch_a", "MerchantA"), ("iso_merch_b", "MerchantB")]:
            session.add(Merchant(
                merchant_id=mid, name=name,
                max_autonomous_spend_inr=500, approval_threshold_inr=1500,
                restricted_categories="[]", is_active=True,
            ))
        session.commit()

        # Create merchant A owner
        r = client.post("/v1/auth/signup", json={
            "email": "owner_a@test.com", "password": "TestPass123!", "role": "MERCHANT_OWNER",
        })
        owner_a_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        owner_a_id = r.json()["user_id"]

        # Link owner A to merchant A only
        session.add(MerchantUser(
            merchant_id="iso_merch_a", user_id=owner_a_id,
            role=MerchantUserRole.OWNER,
        ))
        session.commit()

        # Owner A can update merchant A's policy
        r = client.put("/v1/merchants/iso_merch_a/policy", json={
            "max_autonomous_spend_inr": 1000,
            "approval_threshold_inr": 3000,
            "restricted_categories": [],
            "refund_authority": "human_only",
        }, headers=owner_a_headers)
        assert r.status_code == 200

        # Owner A must NOT be able to update merchant B's policy
        r = client.put("/v1/merchants/iso_merch_b/policy", json={
            "max_autonomous_spend_inr": 99999,
            "approval_threshold_inr": 99999,
            "restricted_categories": [],
            "refund_authority": "merchant",
        }, headers=owner_a_headers)
        assert r.status_code == 403, f"Cross-merchant policy update allowed! Got {r.status_code}"


class TestAuditTenantScoping:
    """Audit events are filtered by tenant — buyer sees only their txn events."""

    def test_audit_scoped_to_buyer(self, client, session):
        # Create buyer
        r = client.post("/v1/auth/signup", json={
            "email": "audit_buyer@test.com", "password": "TestPass123!", "role": "BUYER",
        })
        buyer_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Create a transaction that will generate audit events (auth required — N1 fix)
        r = client.post("/v1/transactions/intent", json={"message": "test audit scoping"}, headers=buyer_headers)
        txn_id = r.json()["transaction_id"]
        # Approve to generate an audit event
        client.post("/v1/transactions/approve", json={"transaction_id": txn_id}, headers=buyer_headers)

        # Fetch audit — should only show this buyer's events
        r = client.get("/v1/audit/", headers=buyer_headers)
        assert r.status_code == 200
        events = r.json().get("events", [])
        # All events should belong to our transaction
        for evt in events:
            assert evt["transaction_id"] == txn_id
