"""
Phase 3 — Buyer Policy Engine tests.
Verify that buyer-side restrictions (daily limit, blocked merchants,
blocked categories) are enforced by the deterministic policy engine.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

import pytest
from policy.engine import PolicyEngine, PolicyDecision, BuyerPolicyContext
from models.merchant import Merchant, Product


@pytest.fixture
def engine():
    return PolicyEngine()


@pytest.fixture
def merchant():
    return Merchant(
        merchant_id="test_m", name="TestMart", currency="INR",
        max_autonomous_spend_inr=500, approval_threshold_inr=1500,
        restricted_categories="[]", is_active=True,
    )


@pytest.fixture
def product():
    return Product(
        product_id="test_p", merchant_id="test_m",
        name="Widget", category="grocery", price_inr=300,
        inventory_count=10, availability=True, merchant_rating=4.5,
    )


class TestBuyerBlockedMerchant:
    def test_blocked_merchant_denied(self, engine, merchant, product):
        ctx = BuyerPolicyContext(blocked_merchants=["test_m"])
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "BUYER_BLOCKED_MERCHANT" in result.reason_codes

    def test_unblocked_merchant_allowed(self, engine, merchant, product):
        ctx = BuyerPolicyContext(blocked_merchants=["other_merchant"])
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW

    def test_empty_blocked_list_allowed(self, engine, merchant, product):
        ctx = BuyerPolicyContext(blocked_merchants=[])
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW


class TestBuyerBlockedCategory:
    def test_blocked_category_denied(self, engine, merchant, product):
        ctx = BuyerPolicyContext(blocked_categories=["grocery"])
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "BUYER_BLOCKED_CATEGORY" in result.reason_codes

    def test_blocked_category_case_insensitive(self, engine, merchant, product):
        ctx = BuyerPolicyContext(blocked_categories=["GROCERY"])
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "BUYER_BLOCKED_CATEGORY" in result.reason_codes

    def test_unblocked_category_allowed(self, engine, merchant, product):
        ctx = BuyerPolicyContext(blocked_categories=["electronics"])
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW


class TestBuyerDailyLimit:
    def test_within_daily_limit_allowed(self, engine, merchant, product):
        ctx = BuyerPolicyContext(daily_limit_inr=5000, daily_spent_inr=1000)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW

    def test_exceeds_daily_limit_denied(self, engine, merchant, product):
        ctx = BuyerPolicyContext(daily_limit_inr=5000, daily_spent_inr=4800)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "DAILY_LIMIT_EXCEEDED" in result.reason_codes
        assert "4800" in result.message  # shows spent
        assert "5000" in result.message  # shows limit

    def test_exact_daily_limit_allowed(self, engine, merchant, product):
        """Spending exactly up to the daily limit is OK."""
        ctx = BuyerPolicyContext(daily_limit_inr=5000, daily_spent_inr=4700)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW

    def test_one_over_daily_limit_denied(self, engine, merchant, product):
        """Even ₹1 over the daily limit is denied."""
        ctx = BuyerPolicyContext(daily_limit_inr=5000, daily_spent_inr=4701)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "DAILY_LIMIT_EXCEEDED" in result.reason_codes

    def test_no_daily_limit_allowed(self, engine, merchant, product):
        """None daily_limit_inr means no daily cap."""
        ctx = BuyerPolicyContext(daily_limit_inr=None, daily_spent_inr=99999)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW

    def test_daily_limit_message_shows_remaining(self, engine, merchant, product):
        ctx = BuyerPolicyContext(daily_limit_inr=5000, daily_spent_inr=4900)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "Remaining: ₹100" in result.message


class TestBuyerContextWithPerTxnLimit:
    """Buyer context per_transaction_auto_limit_inr should override legacy param."""

    def test_buyer_context_per_txn_limit_triggers_approval(self, engine, merchant, product):
        ctx = BuyerPolicyContext(per_transaction_auto_limit_inr=200)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.NEEDS_APPROVAL

    def test_buyer_context_per_txn_limit_allows_when_under(self, engine, merchant, product):
        ctx = BuyerPolicyContext(per_transaction_auto_limit_inr=500)
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.ALLOW


class TestNoBuyerContext:
    """Without buyer_context, engine should behave as before (backward compat)."""

    def test_no_context_under_merchant_limit_allows(self, engine, merchant, product):
        result = engine.evaluate(merchant, product, 300)
        assert result.decision == PolicyDecision.ALLOW

    def test_no_context_over_merchant_limit_needs_approval(self, engine, merchant, product):
        product.price_inr = 600
        result = engine.evaluate(merchant, product, 600)
        assert result.decision == PolicyDecision.NEEDS_APPROVAL


class TestPriorityOrder:
    """Buyer blocks should fire before spend limit checks."""

    def test_blocked_merchant_fires_before_daily_limit(self, engine, merchant, product):
        """Even if daily limit is fine, blocked merchant should DENY."""
        ctx = BuyerPolicyContext(
            daily_limit_inr=50000, daily_spent_inr=0,
            blocked_merchants=["test_m"],
        )
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "BUYER_BLOCKED_MERCHANT" in result.reason_codes

    def test_blocked_category_fires_before_spend_limit(self, engine, merchant, product):
        ctx = BuyerPolicyContext(
            per_transaction_auto_limit_inr=9999,
            blocked_categories=["grocery"],
        )
        result = engine.evaluate(merchant, product, 300, buyer_context=ctx)
        assert result.decision == PolicyDecision.DENY
        assert "BUYER_BLOCKED_CATEGORY" in result.reason_codes
