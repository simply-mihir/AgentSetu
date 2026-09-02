"""
AI Buyer Orchestrator.
Uses OpenAI structured outputs to extract buyer intent and generate explanations.
The LLM ONLY reasons and recommends — it never makes financial decisions.
"""
import json
import logging
from typing import List, Optional
from openai import OpenAI
from config import settings

logger = logging.getLogger(__name__)


class BuyerOrchestrator:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def parse_intent(self, user_message: str) -> dict:
        """
        Extract structured constraints from natural language buyer intent.
        Returns: {category, max_budget_inr, delivery_sla_days, quantity, keywords, confidence}
        """
        system_prompt = """You are an intent parser for an AI commerce agent called AgentSetu.
Extract structured purchase constraints from the user's natural language request.

Return a JSON object with these fields:
- category: string (e.g. "grocery", "electronics", "spices", "staples") or null
- max_budget_inr: integer (maximum price in INR) or null
- delivery_sla_days: integer (max days for delivery) or null
- quantity: integer (default 1)
- keywords: list of strings (product keywords)
- quality_preferences: list of strings (e.g. ["organic", "premium"])
- confidence: float 0-1

Rules:
- Extract ONLY what the user stated explicitly or very clearly implied
- Do NOT invent constraints not mentioned
- max_budget_inr should be the exact numeric value if stated (e.g. "under 500" → 500)
- For "deliver in 2 days" → delivery_sla_days: 2
"""

        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=300,
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"Intent parsing failed: {e}")
            # Deterministic fallback
            return {
                "category": None,
                "max_budget_inr": None,
                "delivery_sla_days": None,
                "quantity": 1,
                "keywords": [],
                "quality_preferences": [],
                "confidence": 0.0,
                "parse_error": str(e),
            }

    def generate_comparison(
        self,
        candidates: List[dict],
        constraints: dict,
        selected_product: dict,
    ) -> str:
        """Generate a human-readable explanation of the recommendation."""
        system_prompt = """You are an AI commerce agent explaining a product recommendation.
Be concise (2-4 sentences), factual, and cite specific product attributes.
Do NOT mention prices calculated differently from the data.
Do NOT claim payment status or inventory facts beyond what's provided.
Focus on why this product best matches the buyer's constraints."""

        user_content = f"""
Buyer constraints: {json.dumps(constraints, indent=2)}

Selected product: {json.dumps(selected_product, indent=2)}

Other options considered: {json.dumps(candidates[:3], indent=2)}

Explain why the selected product is the best match in 2-4 sentences.
Cite price, delivery time, rating, and any relevant quality aspects.
"""
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Comparison generation failed: {e}")
            return (
                f"Selected {selected_product.get('name', 'this product')} from "
                f"{selected_product.get('merchant_name', 'merchant')} at "
                f"₹{selected_product.get('price_inr', 'N/A')} — "
                f"best match for your constraints."
            )

    def generate_recovery_suggestion(
        self,
        failure_reason: str,
        transaction: dict,
        alternative_products: List[dict],
    ) -> str:
        """Generate a safe recovery suggestion after a payment failure."""
        system_prompt = """You are an AI commerce agent handling a payment failure.
Explain the situation clearly and suggest ONE safe next action.
Never suggest retrying automatically. Never claim payment succeeded.
Be calm, factual, and focused on what the buyer can do next."""

        user_content = f"""
Failure reason: {failure_reason}
Transaction: {json.dumps(transaction, indent=2)}
Alternative products available: {json.dumps(alternative_products[:2], indent=2)}

Suggest a safe recovery action in 2-3 sentences.
"""
        try:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Recovery generation failed: {e}")
            return (
                "Your payment did not complete. "
                "I have held the transaction safely without retrying. "
                "You may try again with a verified payment method or choose an alternative product."
            )

    def score_candidates(
        self,
        candidates: List[dict],
        constraints: dict,
    ) -> List[dict]:
        """
        Deterministic scoring of candidates.
        score = 0.45 * price_score + 0.25 * delivery_score + 0.20 * rating_score + 0.10 * policy_fit
        """
        if not candidates:
            return []

        max_budget = constraints.get("max_budget_inr") or 99999
        max_delivery = constraints.get("delivery_sla_days") or 7

        # Price scores (cheaper is better relative to budget)
        prices = [c["price_inr"] for c in candidates]
        max_price = max(prices) or 1
        min_price = min(prices) or 1

        # Delivery scores
        deliveries = [c.get("delivery_sla_days_max", 7) for c in candidates]
        max_del = max(deliveries) or 7

        # Rating scores
        ratings = [c.get("merchant_rating", 3.0) for c in candidates]
        max_rating = max(ratings) or 5.0

        for c in candidates:
            price = c["price_inr"]
            delivery = c.get("delivery_sla_days_max", 7)
            rating = c.get("merchant_rating", 3.0)

            # Normalized scores (1.0 = best)
            price_score = 1.0 - (price - min_price) / (max_price - min_price + 1)
            delivery_score = 1.0 - (delivery - 1) / (max_del)
            rating_score = rating / 5.0
            policy_fit = 1.0 if price <= c.get("max_autonomous_spend_inr", 500) else 0.5

            score = (
                0.45 * price_score
                + 0.25 * delivery_score
                + 0.20 * rating_score
                + 0.10 * policy_fit
            )

            c["_score"] = round(score, 4)
            c["_price_score"] = round(price_score, 3)
            c["_delivery_score"] = round(delivery_score, 3)
            c["_rating_score"] = round(rating_score, 3)
            c["_policy_fit"] = policy_fit

        candidates.sort(key=lambda x: x["_score"], reverse=True)
        return candidates


# Singleton
buyer_orchestrator = BuyerOrchestrator()
