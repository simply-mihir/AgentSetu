"""
Deterministic Policy Engine.
The LLM may propose; this code approves.
All money-movement decisions go through here — no exceptions.

6-step gate (expanded in Phase 3):
1. Product availability / stock
2. Merchant active
3. Merchant restricted category
4. Buyer blocked merchant        ← Phase 3
5. Buyer blocked category        ← Phase 3
6. Amount vs product price
7. Buyer daily limit             ← Phase 3
8. Effective spend limit (min of merchant + buyer per-txn)
9. Approval threshold
"""
import json
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field
from models.merchant import Merchant, Product


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


@dataclass
class BuyerPolicyContext:
    """Buyer-side policy data loaded from BuyerProfile (server-side only)."""
    per_transaction_auto_limit_inr: Optional[int] = None
    daily_limit_inr: Optional[int] = None
    daily_spent_inr: int = 0  # sum of today's successful/pending txns
    blocked_merchants: List[str] = field(default_factory=list)
    blocked_categories: List[str] = field(default_factory=list)


@dataclass
class PolicyResult:
    decision: PolicyDecision
    reason_codes: List[str] = field(default_factory=list)
    effective_limit_inr: Optional[int] = None
    message: str = ""
    requires_approval_above: Optional[int] = None


class PolicyEngine:
    """
    Deterministic authorization engine.
    Rules are evaluated in order; first DENY wins.
    """

    def evaluate(
        self,
        merchant: Merchant,
        product: Product,
        amount_inr: int,
        buyer_limit_inr: Optional[int] = None,
        is_approved: bool = False,
        buyer_context: Optional[BuyerPolicyContext] = None,
    ) -> PolicyResult:
        reason_codes = []

        # ── 1. Product availability ──────────────────────────────────────────
        if not product.availability:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["PRODUCT_UNAVAILABLE"],
                message="Product is not available."
            )

        if product.inventory_count <= 0:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["OUT_OF_STOCK"],
                message="Product is out of stock."
            )

        # ── 2. Merchant active ───────────────────────────────────────────────
        if not merchant.is_active:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["MERCHANT_INACTIVE"],
                message="Merchant is not currently accepting agent orders."
            )

        # ── 3. Merchant restricted category ──────────────────────────────────
        restricted = merchant.get_restricted_categories()
        if product.category.lower() in [r.lower() for r in restricted]:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["RESTRICTED_CATEGORY"],
                message=f"Category '{product.category}' is restricted for autonomous purchase."
            )

        # ── 4. Buyer blocked merchant (Phase 3) ─────────────────────────────
        if buyer_context and buyer_context.blocked_merchants:
            if merchant.merchant_id in buyer_context.blocked_merchants:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason_codes=["BUYER_BLOCKED_MERCHANT"],
                    message=f"You have blocked purchases from '{merchant.name}'."
                )

        # ── 5. Buyer blocked category (Phase 3) ─────────────────────────────
        if buyer_context and buyer_context.blocked_categories:
            if product.category.lower() in [c.lower() for c in buyer_context.blocked_categories]:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason_codes=["BUYER_BLOCKED_CATEGORY"],
                    message=f"You have blocked purchases in category '{product.category}'."
                )

        # ── 6. Exact amount vs product price ─────────────────────────────────
        if amount_inr != product.price_inr:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["AMOUNT_MISMATCH"],
                message=f"Requested amount ₹{amount_inr} does not match product price ₹{product.price_inr}."
            )

        # ── 7. Buyer daily limit (Phase 3) ───────────────────────────────────
        if buyer_context and buyer_context.daily_limit_inr is not None:
            projected = buyer_context.daily_spent_inr + amount_inr
            if projected > buyer_context.daily_limit_inr:
                remaining = max(0, buyer_context.daily_limit_inr - buyer_context.daily_spent_inr)
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason_codes=["DAILY_LIMIT_EXCEEDED"],
                    effective_limit_inr=buyer_context.daily_limit_inr,
                    message=(
                        f"This purchase (₹{amount_inr}) would exceed your daily limit "
                        f"of ₹{buyer_context.daily_limit_inr}. "
                        f"Spent today: ₹{buyer_context.daily_spent_inr}. "
                        f"Remaining: ₹{remaining}."
                    ),
                )

        # ── 8. Effective spend limit (min of merchant + buyer per-txn) ───────
        merchant_limit = merchant.max_autonomous_spend_inr
        # buyer_limit_inr (legacy param) or buyer_context.per_transaction_auto_limit_inr
        effective_buyer_limit = buyer_limit_inr
        if buyer_context and buyer_context.per_transaction_auto_limit_inr is not None:
            effective_buyer_limit = buyer_context.per_transaction_auto_limit_inr
        effective_limit = min(merchant_limit, effective_buyer_limit) if effective_buyer_limit else merchant_limit
        approval_threshold = merchant.approval_threshold_inr

        # ── 9. Over effective limit — DENY without explicit approval ─────────
        if amount_inr > effective_limit and not is_approved:
            reason_codes.append("OVER_LIMIT")
            if amount_inr <= approval_threshold or is_approved:
                return PolicyResult(
                    decision=PolicyDecision.NEEDS_APPROVAL,
                    reason_codes=["NEEDS_APPROVAL", "OVER_AUTO_LIMIT"],
                    effective_limit_inr=effective_limit,
                    requires_approval_above=effective_limit,
                    message=f"Amount ₹{amount_inr} exceeds autonomous limit ₹{effective_limit}. Buyer approval required."
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason_codes=["OVER_LIMIT", "EXCEEDS_APPROVAL_THRESHOLD"],
                    effective_limit_inr=effective_limit,
                    message=f"Amount ₹{amount_inr} exceeds approval threshold ₹{approval_threshold}."
                )

        # ── 10. Needs approval (within threshold but above auto limit) ───────
        if amount_inr > merchant.max_autonomous_spend_inr and not is_approved:
            return PolicyResult(
                decision=PolicyDecision.NEEDS_APPROVAL,
                reason_codes=["NEEDS_APPROVAL", "OVER_AUTO_LIMIT"],
                effective_limit_inr=merchant.max_autonomous_spend_inr,
                requires_approval_above=merchant.max_autonomous_spend_inr,
                message=f"Amount ₹{amount_inr} requires explicit buyer approval."
            )

        # ── 11. All checks passed ────────────────────────────────────────────
        reason_codes.append("WITHIN_SPEND_CAP")
        reason_codes.append("CATEGORY_ALLOWED")
        if is_approved:
            reason_codes.append("BUYER_APPROVED")

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason_codes=reason_codes,
            effective_limit_inr=effective_limit,
            message="Transaction authorized."
        )

    def evaluate_by_values(
        self,
        amount_inr: int,
        merchant_max_auto_spend: int,
        merchant_approval_threshold: int,
        restricted_categories: List[str],
        product_category: str,
        product_available: bool,
        inventory_count: int,
        buyer_limit_inr: Optional[int] = None,
        is_approved: bool = False,
    ) -> PolicyResult:
        """Evaluate policy without DB models (for API-level checks)."""

        if not product_available:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["PRODUCT_UNAVAILABLE"],
                message="Product is not available."
            )

        if inventory_count <= 0:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["OUT_OF_STOCK"],
                message="Product is out of stock."
            )

        if product_category.lower() in [r.lower() for r in restricted_categories]:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["RESTRICTED_CATEGORY"],
                message=f"Category '{product_category}' is restricted."
            )

        effective_limit = min(merchant_max_auto_spend, buyer_limit_inr) if buyer_limit_inr else merchant_max_auto_spend

        if amount_inr > effective_limit and not is_approved:
            if amount_inr <= merchant_approval_threshold:
                return PolicyResult(
                    decision=PolicyDecision.NEEDS_APPROVAL,
                    reason_codes=["NEEDS_APPROVAL", "OVER_AUTO_LIMIT"],
                    effective_limit_inr=effective_limit,
                    requires_approval_above=effective_limit,
                    message=f"Amount ₹{amount_inr} exceeds autonomous limit ₹{effective_limit}. Approval required."
                )
            else:
                return PolicyResult(
                    decision=PolicyDecision.DENY,
                    reason_codes=["OVER_LIMIT", "EXCEEDS_APPROVAL_THRESHOLD"],
                    effective_limit_inr=effective_limit,
                    message=f"Amount ₹{amount_inr} exceeds approval threshold ₹{merchant_approval_threshold}."
                )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason_codes=["WITHIN_SPEND_CAP", "CATEGORY_ALLOWED"] + (["BUYER_APPROVED"] if is_approved else []),
            effective_limit_inr=effective_limit,
            message="Transaction authorized."
        )
