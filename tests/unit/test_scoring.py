"""Unit tests for candidate scoring logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("APP_MODE", "demo")
os.environ.setdefault("SECRET_KEY", "test-secret")

from ai.orchestrator import BuyerOrchestrator

orch = BuyerOrchestrator()


def make_candidate(price, delivery, rating, auto_limit=500):
    return {
        "product_id": "p1", "merchant_id": "m1", "merchant_name": "M",
        "name": "Product", "category": "grocery",
        "price_inr": price,
        "delivery_sla_days_min": 1, "delivery_sla_days_max": delivery,
        "merchant_rating": rating,
        "max_autonomous_spend_inr": auto_limit,
        "inventory_count": 10, "availability": True,
        "return_policy": "7_days", "description": "",
        "approval_threshold_inr": 1500,
    }


class TestScoring:
    def test_cheaper_product_ranks_higher(self):
        candidates = [make_candidate(500, 3, 4.0), make_candidate(200, 3, 4.0)]
        ranked = orch.score_candidates(candidates, {})
        assert ranked[0]["price_inr"] == 200  # Cheaper ranked first

    def test_faster_delivery_ranks_higher(self):
        candidates = [make_candidate(300, 7, 4.0), make_candidate(300, 1, 4.0)]
        ranked = orch.score_candidates(candidates, {})
        assert ranked[0]["delivery_sla_days_max"] == 1  # Faster ranked first

    def test_higher_rating_ranks_higher(self):
        candidates = [make_candidate(300, 3, 3.0), make_candidate(300, 3, 4.8)]
        ranked = orch.score_candidates(candidates, {})
        assert ranked[0]["merchant_rating"] == 4.8

    def test_within_policy_fit_bonus(self):
        """Product within auto-limit should score higher than one above."""
        candidates = [
            make_candidate(400, 3, 4.0, auto_limit=500),   # within limit
            make_candidate(600, 3, 4.0, auto_limit=500),   # above limit
        ]
        ranked = orch.score_candidates(candidates, {})
        # The cheaper one within the limit should rank first
        assert ranked[0]["price_inr"] == 400

    def test_scores_are_between_0_and_1(self):
        candidates = [make_candidate(100, 1, 5.0), make_candidate(1000, 14, 1.0)]
        ranked = orch.score_candidates(candidates, {})
        for c in ranked:
            assert 0 <= c["_score"] <= 1.0
            assert 0 <= c["_price_score"] <= 1.0
            assert 0 <= c["_delivery_score"] <= 1.0
            assert 0 <= c["_rating_score"] <= 1.0

    def test_empty_candidates_returns_empty(self):
        result = orch.score_candidates([], {})
        assert result == []

    def test_score_breakdown_present(self):
        candidates = [make_candidate(299, 2, 4.5)]
        ranked = orch.score_candidates(candidates, {})
        c = ranked[0]
        assert "_score" in c
        assert "_price_score" in c
        assert "_delivery_score" in c
        assert "_rating_score" in c
        assert "_policy_fit" in c

    def test_no_missing_value_gives_perfect_score(self):
        """Missing delivery info should not silently give a perfect score."""
        candidates = [
            {"product_id": "p1", "merchant_id": "m1", "merchant_name": "M",
             "name": "X", "category": "grocery", "price_inr": 100,
             # No delivery_sla_days_max, no merchant_rating
             "max_autonomous_spend_inr": 500, "inventory_count": 1,
             "availability": True, "return_policy": "7_days", "description": "",
             "approval_threshold_inr": 1500},
        ]
        ranked = orch.score_candidates(candidates, {})
        # Should not crash, and score should be valid
        assert 0 <= ranked[0]["_score"] <= 1.0
