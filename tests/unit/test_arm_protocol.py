"""
Phase 9 — ARM protocol tests.
Verify manifest metadata, payment_link_id removal, hash integrity.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from models.merchant import Merchant, Product
from arm.generator import generate_arm
from arm.schema import ARMManifest


class TestARMManifestMetadata:
    """Phase 9: ARM manifests must include metadata fields."""

    def _make_merchant_and_products(self):
        merchant = Merchant(
            merchant_id="arm_m1", name="ArmMart", currency="INR",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=True,
        )
        products = [Product(
            product_id="arm_p1", merchant_id="arm_m1", name="Gadget",
            category="electronics", price_inr=499, inventory_count=5,
            availability=True, delivery_sla_days_min=1, delivery_sla_days_max=3,
            merchant_rating=4.2, payment_link_id="plink_should_not_appear",
        )]
        return merchant, products

    def test_schema_version_is_0_2(self):
        merchant, products = self._make_merchant_and_products()
        manifest = generate_arm(merchant, products)
        assert manifest.schema_version == "arm-0.2"

    def test_manifest_has_id(self):
        merchant, products = self._make_merchant_and_products()
        manifest = generate_arm(merchant, products)
        assert manifest.manifest_id.startswith("arm_")

    def test_manifest_has_generated_at(self):
        merchant, products = self._make_merchant_and_products()
        manifest = generate_arm(merchant, products)
        assert manifest.generated_at.endswith("Z")

    def test_manifest_hash_is_populated(self):
        merchant, products = self._make_merchant_and_products()
        manifest = generate_arm(merchant, products)
        assert len(manifest.manifest_hash) == 64  # SHA-256 hex

    def test_manifest_hash_is_deterministic(self):
        """Same content should produce the same hash (excluding timestamp)."""
        merchant, products = self._make_merchant_and_products()
        m1 = generate_arm(merchant, products)
        m2 = generate_arm(merchant, products)
        assert m1.manifest_hash == m2.manifest_hash

    def test_manifest_hash_changes_with_content(self):
        """Different content should produce different hashes."""
        merchant, products = self._make_merchant_and_products()
        m1 = generate_arm(merchant, products)
        products[0].price_inr = 999
        m2 = generate_arm(merchant, products)
        assert m1.manifest_hash != m2.manifest_hash


class TestARMPaymentLinkRemoval:
    """Phase 9: payment_link_id must NOT appear in ARM products."""

    def test_payment_link_id_not_in_arm_product(self):
        """ARM products should not expose internal payment_link_id."""
        merchant = Merchant(
            merchant_id="arm_m2", name="SecretMart", currency="INR",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=True,
        )
        product = Product(
            product_id="arm_p2", merchant_id="arm_m2", name="Secret Item",
            category="misc", price_inr=200, inventory_count=3,
            availability=True, delivery_sla_days_min=2, delivery_sla_days_max=5,
            merchant_rating=4.0, payment_link_id="plink_INTERNAL_SECRET",
        )
        manifest = generate_arm(merchant, [product])
        arm_dict = manifest.model_dump()

        # Check that no product contains payment_link_id
        for p in arm_dict["products"]:
            assert "payment_link_id" not in p, "payment_link_id leaked into ARM product"
            # Also verify there's no nested payment dict with payment_link_id
            if "payment" in p:
                assert "payment_link_id" not in p["payment"], "payment_link_id in payment dict"

    def test_unavailable_products_excluded(self):
        """Products with availability=False should not appear in ARM."""
        merchant = Merchant(
            merchant_id="arm_m3", name="FilterMart", currency="INR",
            max_autonomous_spend_inr=500, approval_threshold_inr=1500,
            restricted_categories="[]", is_active=True,
        )
        products = [
            Product(
                product_id="arm_p_avail", merchant_id="arm_m3", name="Available",
                category="misc", price_inr=100, inventory_count=5,
                availability=True, delivery_sla_days_min=1, delivery_sla_days_max=2,
                merchant_rating=4.0,
            ),
            Product(
                product_id="arm_p_unavail", merchant_id="arm_m3", name="Unavailable",
                category="misc", price_inr=200, inventory_count=0,
                availability=False, delivery_sla_days_min=1, delivery_sla_days_max=2,
                merchant_rating=4.0,
            ),
        ]
        manifest = generate_arm(merchant, products)
        assert len(manifest.products) == 1
        assert manifest.products[0].product_id == "arm_p_avail"
