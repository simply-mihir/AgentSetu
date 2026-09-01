"""
Phase 10 — Discovery performance tests.
Verify pagination, filtering, and sensitive field removal on public endpoints.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from models.merchant import Merchant, Product


class TestMerchantListPagination:
    """Phase 10: List endpoint supports limit/offset pagination."""

    def _seed_merchants(self, session, count=5):
        for i in range(count):
            m = Merchant(
                merchant_id=f"disc_m{i}", name=f"Merchant {i}", currency="INR",
                max_autonomous_spend_inr=500, approval_threshold_inr=1500,
                restricted_categories="[]", is_active=True,
                category="grocery" if i % 2 == 0 else "electronics",
            )
            session.add(m)
        session.commit()

    def test_default_pagination(self, client, session):
        self._seed_merchants(session, 5)
        resp = client.get("/v1/merchants/")
        assert resp.status_code == 200
        data = resp.json()
        assert "merchants" in data
        assert "limit" in data
        assert "offset" in data
        assert "count" in data
        assert data["count"] == 5

    def test_limit_and_offset(self, client, session):
        self._seed_merchants(session, 5)
        resp = client.get("/v1/merchants/?limit=2&offset=0")
        data = resp.json()
        assert data["count"] == 2
        assert data["limit"] == 2
        assert data["offset"] == 0

        resp2 = client.get("/v1/merchants/?limit=2&offset=2")
        data2 = resp2.json()
        assert data2["count"] == 2
        assert data2["offset"] == 2

    def test_offset_beyond_results(self, client, session):
        self._seed_merchants(session, 3)
        resp = client.get("/v1/merchants/?offset=100")
        data = resp.json()
        assert data["count"] == 0


class TestMerchantListFiltering:
    """Phase 10: Filter by category and active status."""

    def _seed_mixed_merchants(self, session):
        merchants = [
            Merchant(merchant_id="filt_m1", name="Active Grocery", category="grocery",
                     currency="INR", max_autonomous_spend_inr=500, approval_threshold_inr=1500,
                     restricted_categories="[]", is_active=True),
            Merchant(merchant_id="filt_m2", name="Active Electronics", category="electronics",
                     currency="INR", max_autonomous_spend_inr=500, approval_threshold_inr=1500,
                     restricted_categories="[]", is_active=True),
            Merchant(merchant_id="filt_m3", name="Inactive Grocery", category="grocery",
                     currency="INR", max_autonomous_spend_inr=500, approval_threshold_inr=1500,
                     restricted_categories="[]", is_active=False),
        ]
        for m in merchants:
            session.add(m)
        session.commit()

    def test_filter_by_category(self, client, session):
        self._seed_mixed_merchants(session)
        resp = client.get("/v1/merchants/?category=grocery")
        data = resp.json()
        # Should only return active grocery (active_only defaults to True)
        assert data["count"] == 1
        assert data["merchants"][0]["category"] == "grocery"

    def test_active_only_default(self, client, session):
        self._seed_mixed_merchants(session)
        resp = client.get("/v1/merchants/")
        data = resp.json()
        assert data["count"] == 2  # only 2 active merchants
        for m in data["merchants"]:
            assert m["is_active"] is True

    def test_include_inactive(self, client, session):
        self._seed_mixed_merchants(session)
        resp = client.get("/v1/merchants/?active_only=false")
        data = resp.json()
        assert data["count"] == 3  # all merchants


class TestSensitiveFieldRemoval:
    """Phase 10: Public list must not expose internal policy fields."""

    def test_list_omits_policy_fields(self, client, session):
        m = Merchant(
            merchant_id="sens_m1", name="SensitiveMart", category="grocery",
            currency="INR", max_autonomous_spend_inr=9999,
            approval_threshold_inr=8888, restricted_categories='["weapons"]',
            refund_authority="automated", is_active=True,
        )
        session.add(m)
        session.commit()

        resp = client.get("/v1/merchants/")
        data = resp.json()
        assert data["count"] == 1
        merchant_data = data["merchants"][0]
        # These internal policy fields must NOT appear in the public list
        assert "max_autonomous_spend_inr" not in merchant_data
        assert "approval_threshold_inr" not in merchant_data
        assert "restricted_categories" not in merchant_data
        assert "refund_authority" not in merchant_data

    def test_detail_endpoint_includes_policy_fields(self, client, session):
        """The detail endpoint /{merchant_id} DOES include policy fields (for agents)."""
        m = Merchant(
            merchant_id="sens_m2", name="DetailMart", category="grocery",
            currency="INR", max_autonomous_spend_inr=1000,
            approval_threshold_inr=2000, restricted_categories='["alcohol"]',
            refund_authority="human_only", is_active=True,
        )
        session.add(m)
        session.commit()

        resp = client.get("/v1/merchants/sens_m2")
        data = resp.json()
        # Detail endpoint should include policy fields for agent consumption
        assert data["max_autonomous_spend_inr"] == 1000
        assert data["approval_threshold_inr"] == 2000
        assert "alcohol" in data["restricted_categories"]
