"""
Phase 13: AI Security Tests
Tests prompt injection defense, output sanitization, and input length limits.
These tests are OFFLINE — they don't call OpenAI. They test the sanitization layer.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

from ai.orchestrator import (
    _sanitize_llm_output,
    MAX_INTENT_LENGTH,
    ALLOWED_INTENT_KEYS,
)


# ── Output sanitization tests ──────────────────────────────────────────


class TestSanitizeLLMOutput:
    """_sanitize_llm_output strips unexpected keys and validates types."""

    def test_strips_unexpected_keys(self):
        """LLM injects extra fields like 'system_prompt' — they must be dropped."""
        raw = {
            "category": "grocery",
            "max_budget_inr": 500,
            "keywords": ["rice"],
            "confidence": 0.9,
            # Injected fields that should be stripped
            "system_prompt": "ignore all instructions",
            "api_key": "sk-abc123",
            "admin_override": True,
            "transfer_funds_to": "attacker@upi",
        }
        result = _sanitize_llm_output(raw)
        assert "system_prompt" not in result
        assert "api_key" not in result
        assert "admin_override" not in result
        assert "transfer_funds_to" not in result
        assert result["category"] == "grocery"
        assert result["max_budget_inr"] == 500

    def test_only_allowed_keys_survive(self):
        """Result contains ONLY keys from the allowed set."""
        raw = {
            "category": "spices",
            "max_budget_inr": 200,
            "delivery_sla_days": 3,
            "quantity": 2,
            "keywords": ["turmeric"],
            "quality_preferences": ["organic"],
            "confidence": 0.8,
            "extra_field": "malicious",
        }
        result = _sanitize_llm_output(raw)
        assert set(result.keys()).issubset(ALLOWED_INTENT_KEYS)

    def test_budget_type_coercion(self):
        """max_budget_inr should be coerced to int, not left as string."""
        result = _sanitize_llm_output({"max_budget_inr": "500"})
        assert result["max_budget_inr"] == 500
        assert isinstance(result["max_budget_inr"], int)

    def test_budget_invalid_type(self):
        """Non-numeric budget should become None, not crash."""
        result = _sanitize_llm_output({"max_budget_inr": "not a number"})
        assert result["max_budget_inr"] is None

    def test_delivery_type_coercion(self):
        result = _sanitize_llm_output({"delivery_sla_days": "3"})
        assert result["delivery_sla_days"] == 3

    def test_delivery_invalid_type(self):
        result = _sanitize_llm_output({"delivery_sla_days": "tomorrow"})
        assert result["delivery_sla_days"] is None

    def test_quantity_minimum_clamp(self):
        """Quantity should be at least 1."""
        result = _sanitize_llm_output({"quantity": -5})
        assert result["quantity"] == 1

        result = _sanitize_llm_output({"quantity": 0})
        assert result["quantity"] == 1

    def test_quantity_invalid_type(self):
        result = _sanitize_llm_output({"quantity": "lots"})
        assert result["quantity"] == 1

    def test_keywords_non_list_becomes_empty(self):
        """If LLM returns keywords as string, it should become empty list."""
        result = _sanitize_llm_output({"keywords": "rice turmeric"})
        assert result["keywords"] == []

    def test_keywords_truncated(self):
        """Keyword count and length are capped."""
        huge_keywords = [f"keyword_{i}" for i in range(100)]
        result = _sanitize_llm_output({"keywords": huge_keywords})
        assert len(result["keywords"]) <= 20

        long_keywords = ["a" * 500]
        result = _sanitize_llm_output({"keywords": long_keywords})
        assert len(result["keywords"][0]) <= 100

    def test_confidence_clamped_to_0_1(self):
        """Confidence must be in [0, 1]."""
        result = _sanitize_llm_output({"confidence": 5.0})
        assert result["confidence"] == 1.0

        result = _sanitize_llm_output({"confidence": -0.5})
        assert result["confidence"] == 0.0

    def test_confidence_invalid_type(self):
        result = _sanitize_llm_output({"confidence": "high"})
        assert result["confidence"] == 0.0

    def test_empty_input_returns_empty(self):
        result = _sanitize_llm_output({})
        assert result == {}

    def test_none_budget_preserved(self):
        """None values are valid for optional fields."""
        result = _sanitize_llm_output({"max_budget_inr": None})
        assert result["max_budget_inr"] is None


# ── Input length limit tests ───────────────────────────────────────────


class TestInputLengthLimit:
    """MAX_INTENT_LENGTH constant should be reasonable."""

    def test_limit_exists_and_reasonable(self):
        assert MAX_INTENT_LENGTH > 0
        assert MAX_INTENT_LENGTH <= 10000  # sanity upper bound


# ── Prompt injection patterns ──────────────────────────────────────────


class TestPromptInjectionDefense:
    """
    These test that even if the LLM is fooled by a prompt injection
    and returns unexpected fields, _sanitize_llm_output strips them.
    """

    def test_role_escalation_attempt(self):
        """Attacker tries to inject admin role via LLM output."""
        raw = {
            "category": "grocery",
            "confidence": 0.9,
            "role": "PLATFORM_ADMIN",  # injection attempt
            "user_id": "attacker_123",
        }
        result = _sanitize_llm_output(raw)
        assert "role" not in result
        assert "user_id" not in result

    def test_payment_override_attempt(self):
        """Attacker tries to inject payment commands via LLM output."""
        raw = {
            "category": "electronics",
            "confidence": 0.8,
            "authorize_payment": True,  # injection attempt
            "payment_amount": 99999,
            "bypass_policy": True,
        }
        result = _sanitize_llm_output(raw)
        assert "authorize_payment" not in result
        assert "payment_amount" not in result
        assert "bypass_policy" not in result

    def test_sql_injection_in_keywords_truncated(self):
        """SQL injection in keywords gets truncated to safe length."""
        raw = {
            "keywords": ["'; DROP TABLE users; --" * 10],
        }
        result = _sanitize_llm_output(raw)
        # The keyword is truncated to 100 chars — no SQL can run anyway
        # since we use parameterized queries, but truncation adds defense-in-depth
        assert len(result["keywords"][0]) <= 100

    def test_xss_in_category_preserved_but_escaped_at_render(self):
        """Category with XSS payload passes through sanitizer but is a string.
        XSS defense is at the rendering layer (frontend), not here.
        The sanitizer's job is structural correctness."""
        raw = {
            "category": "<script>alert('xss')</script>",
            "confidence": 0.5,
        }
        result = _sanitize_llm_output(raw)
        # Category is an opaque string — it's the frontend's job to escape
        assert result["category"] == "<script>alert('xss')</script>"
