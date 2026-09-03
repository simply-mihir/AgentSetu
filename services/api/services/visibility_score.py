"""
N11: Merchant Visibility Score — deterministic, fully auditable scoring.

The score determines how prominently a merchant appears in discovery results.
It is computed from objective signals, NEVER from LLM output.

Score range: 0–100 (integer).

Signals and weights:
  - catalog_completeness (0–25): Products with descriptions, images, proper pricing
  - policy_quality      (0–20): Well-configured policies (spend limits, refund, categories)
  - transaction_health  (0–25): Success rate and volume of recent transactions
  - arm_freshness       (0–15): ARM manifest is current and complete
  - account_standing    (0–15): Active status, verified email (future), tenure

All weights are constants. The function is pure — given the same inputs, it
always returns the same score.
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import timedelta
from sqlmodel import Session, select, func

from models.merchant import Merchant, Product
from models.transaction import Transaction, TransactionState
from utils.time import utc_now


@dataclass
class ScoreBreakdown:
    """Transparent breakdown so merchants can improve their score."""
    catalog_completeness: int = 0
    policy_quality: int = 0
    transaction_health: int = 0
    arm_freshness: int = 0
    account_standing: int = 0
    total: int = 0
    tips: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "breakdown": {
                "catalog_completeness": self.catalog_completeness,
                "policy_quality": self.policy_quality,
                "transaction_health": self.transaction_health,
                "arm_freshness": self.arm_freshness,
                "account_standing": self.account_standing,
            },
            "tips": self.tips,
        }


def compute_visibility_score(
    merchant_id: str,
    session: Session,
) -> ScoreBreakdown:
    """Compute the visibility score for a merchant. Pure deterministic logic."""

    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()

    if not merchant:
        return ScoreBreakdown(tips=["Merchant not found."])

    breakdown = ScoreBreakdown()

    # ── 1. Catalog Completeness (0–25) ────────────────────────────────────────
    products = session.exec(
        select(Product).where(Product.merchant_id == merchant_id)
    ).all()

    if not products:
        breakdown.tips.append("Add at least one product to your catalog.")
    else:
        # Base: 5 points for having ANY products
        cat_score = 5

        # Up to 5 points for product count (1pt per product, max 5)
        cat_score += min(len(products), 5)

        # Up to 10 points for completeness (description + image on each)
        complete_count = sum(
            1 for p in products
            if p.description and len(p.description) >= 10
            and p.image_url and len(p.image_url) > 5
        )
        completeness_ratio = complete_count / len(products) if products else 0
        cat_score += round(completeness_ratio * 10)

        # Up to 5 points for availability
        available_count = sum(1 for p in products if p.availability and p.inventory_count > 0)
        avail_ratio = available_count / len(products) if products else 0
        cat_score += round(avail_ratio * 5)

        breakdown.catalog_completeness = min(cat_score, 25)

        if completeness_ratio < 0.8:
            breakdown.tips.append("Add descriptions and images to all products for better visibility.")
        if avail_ratio < 0.5:
            breakdown.tips.append("Keep more products in stock — out-of-stock items lower your score.")

    # ── 2. Policy Quality (0–20) ──────────────────────────────────────────────
    pol_score = 0

    # 5 points: sensible spend limits (not using defaults)
    if merchant.max_autonomous_spend_inr > 0:
        pol_score += 3
    if merchant.approval_threshold_inr > merchant.max_autonomous_spend_inr:
        pol_score += 2

    # 5 points: restricted categories configured
    restricted = merchant.get_restricted_categories()
    if restricted:
        pol_score += 5
    else:
        breakdown.tips.append("Configure restricted product categories for better policy scoring.")

    # 5 points: refund authority set to something beyond default
    if merchant.refund_authority and merchant.refund_authority != "human_only":
        pol_score += 5
    elif merchant.refund_authority == "human_only":
        pol_score += 3  # Still a valid policy, just conservative

    # 5 points: description + category filled
    if merchant.description and len(merchant.description) >= 20:
        pol_score += 3
    else:
        breakdown.tips.append("Add a detailed merchant description (20+ characters).")
    if merchant.category:
        pol_score += 2

    breakdown.policy_quality = min(pol_score, 20)

    # ── 3. Transaction Health (0–25) ──────────────────────────────────────────
    # Look at last 30 days of transactions
    cutoff = utc_now() - timedelta(days=30)

    total_txns = session.exec(
        select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff,
        )
    ).one()

    if total_txns == 0:
        breakdown.tips.append("Complete some transactions to build your transaction health score.")
    else:
        # Success count
        success_txns = session.exec(
            select(func.count(Transaction.id)).where(
                Transaction.merchant_id == merchant_id,
                Transaction.created_at >= cutoff,
                Transaction.state.in_([
                    TransactionState.PAYMENT_SUCCESS,
                    TransactionState.RECEIPT_ISSUED,
                ]),
            )
        ).one()

        # Volume score (0–10): 2 pts per txn up to 10
        volume_pts = min(total_txns * 2, 10)

        # Success rate score (0–15)
        success_rate = success_txns / total_txns if total_txns > 0 else 0
        rate_pts = round(success_rate * 15)

        breakdown.transaction_health = min(volume_pts + rate_pts, 25)

        if success_rate < 0.7:
            breakdown.tips.append("Improve your transaction success rate — currently below 70%.")

    # ── 4. ARM Freshness (0–15) ───────────────────────────────────────────────
    arm_score = 0
    if merchant.arm_json:
        arm_score += 10  # ARM exists

        # Freshness: updated in last 24 hours = full marks
        arm_age = (utc_now() - merchant.updated_at).total_seconds()
        if arm_age < 86400:  # 24 hours
            arm_score += 5
        elif arm_age < 604800:  # 7 days
            arm_score += 3
        else:
            arm_score += 1
            breakdown.tips.append("Update your ARM manifest — it's over 7 days old.")
    else:
        breakdown.tips.append("Generate an ARM manifest to make your store AI-discoverable.")

    breakdown.arm_freshness = min(arm_score, 15)

    # ── 5. Account Standing (0–15) ────────────────────────────────────────────
    standing_score = 0

    if merchant.is_active:
        standing_score += 5

    # Tenure bonus: 5 points for 30+ days, 3 for 7+
    tenure_days = (utc_now() - merchant.created_at).days
    if tenure_days >= 30:
        standing_score += 5
    elif tenure_days >= 7:
        standing_score += 3
    else:
        standing_score += 1

    # Logo present
    if merchant.logo_url:
        standing_score += 3
    else:
        breakdown.tips.append("Add a logo to build trust with buyers.")

    # Name quality (not placeholder)
    if merchant.name and len(merchant.name) >= 3:
        standing_score += 2

    breakdown.account_standing = min(standing_score, 15)

    # ── Total ─────────────────────────────────────────────────────────────────
    breakdown.total = (
        breakdown.catalog_completeness
        + breakdown.policy_quality
        + breakdown.transaction_health
        + breakdown.arm_freshness
        + breakdown.account_standing
    )

    return breakdown
