"""
Deterministic Policy Engine.
The LLM may propose; this code approves.
All money-movement decisions go through here — no exceptions.
"""
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field
from models.merchant import Merchant, Product


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


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

        # ── 3. Restricted category check ─────────────────────────────────────
        restricted = merchant.get_restricted_categories()
        if product.category.lower() in [r.lower() for r in restricted]:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["RESTRICTED_CATEGORY"],
                message=f"Category '{product.category}' is restricted for autonomous purchase."
            )

        # ── 4. Exact amount vs product price ─────────────────────────────────
        if amount_inr != product.price_inr:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason_codes=["AMOUNT_MISMATCH"],
                message=f"Requested amount ₹{amount_inr} does not match product price ₹{product.price_inr}."
            )

        # ── 5. Effective spend limit (min of merchant + buyer) ───────────────
        merchant_limit = merchant.max_autonomous_spend_inr
        effective_limit = min(merchant_limit, buyer_limit_inr) if buyer_limit_inr else merchant_limit
        approval_threshold = merchant.approval_threshold_inr

        # ── 6. Over effective limit — DENY without explicit approval ─────────
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

        # ── 7. Needs approval (within threshold but above auto limit) ────────
        if amount_inr > merchant.max_autonomous_spend_inr and not is_approved:
            return PolicyResult(
                decision=PolicyDecision.NEEDS_APPROVAL,
                reason_codes=["NEEDS_APPROVAL", "OVER_AUTO_LIMIT"],
                effective_limit_inr=merchant.max_autonomous_spend_inr,
                requires_approval_above=merchant.max_autonomous_spend_inr,
                message=f"Amount ₹{amount_inr} requires explicit buyer approval."
            )

        # ── 8. All checks passed ─────────────────────────────────────────────
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
