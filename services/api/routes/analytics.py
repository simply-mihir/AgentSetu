"""
N11: Merchant Analytics & Visibility Score endpoints.

Provides merchants with actionable insights:
  - Transaction stats (volume, success rate, revenue)
  - Visibility score with transparent breakdown
  - Time-series transaction data

All data is scoped to the authenticated merchant owner's merchants.
Identity is ALWAYS derived from auth context — never from client-supplied merchant_id.
"""
import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from database import get_session
from auth.dependencies import get_current_user
from models.user import User
from models.merchant import Merchant
from models.merchant_user import MerchantUser
from models.transaction import Transaction, TransactionState
from services.visibility_score import compute_visibility_score
from utils.time import utc_now

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_merchant_ids_for_user(user: User, session: Session) -> list[str]:
    """Get all merchant_ids the authenticated user owns/manages.
    Identity derived from auth context — never trust client-supplied IDs."""
    memberships = session.exec(
        select(MerchantUser.merchant_id).where(MerchantUser.user_id == user.user_id)
    ).all()
    return list(memberships)


def _verify_merchant_access(user: User, merchant_id: str, session: Session) -> Merchant:
    """Verify the user has access to this merchant. Raises 403 if not."""
    membership = session.exec(
        select(MerchantUser).where(
            MerchantUser.user_id == user.user_id,
            MerchantUser.merchant_id == merchant_id,
        )
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail={
            "error": {"code": "FORBIDDEN", "message": "You do not have access to this merchant."}
        })
    merchant = session.exec(
        select(Merchant).where(Merchant.merchant_id == merchant_id)
    ).first()
    if not merchant:
        raise HTTPException(status_code=404, detail={
            "error": {"code": "NOT_FOUND", "message": "Merchant not found."}
        })
    return merchant


@router.get("/{merchant_id}/overview", summary="Merchant analytics overview")
async def analytics_overview(
    merchant_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Transaction stats + visibility score for a merchant.
    Identity derived from auth context — merchant_id verified against user's memberships."""
    merchant = _verify_merchant_access(user, merchant_id, session)
    now = utc_now()

    # ── Transaction stats (last 30 days) ──────────────────────────────────────
    cutoff_30d = now - timedelta(days=30)
    cutoff_7d = now - timedelta(days=7)

    # Total transactions
    total_30d = session.exec(
        select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff_30d,
        )
    ).one()

    total_7d = session.exec(
        select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff_7d,
        )
    ).one()

    # Successful transactions
    success_states = [TransactionState.PAYMENT_SUCCESS, TransactionState.RECEIPT_ISSUED]
    success_30d = session.exec(
        select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff_30d,
            Transaction.state.in_(success_states),
        )
    ).one()

    # Revenue (sum of amount_inr for successful txns)
    revenue_30d = session.exec(
        select(func.coalesce(func.sum(Transaction.amount_inr), 0)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff_30d,
            Transaction.state.in_(success_states),
        )
    ).one()

    # Failed transactions
    failed_30d = session.exec(
        select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff_30d,
            Transaction.state == TransactionState.PAYMENT_FAILED,
        )
    ).one()

    # Cancelled transactions
    cancelled_30d = session.exec(
        select(func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff_30d,
            Transaction.state == TransactionState.CANCELLED,
        )
    ).one()

    success_rate = round(success_30d / total_30d * 100, 1) if total_30d > 0 else 0.0

    # ── Visibility score ──────────────────────────────────────────────────────
    score = compute_visibility_score(merchant_id, session)

    return {
        "merchant_id": merchant_id,
        "merchant_name": merchant.name,
        "period": "last_30_days",
        "transactions": {
            "total_30d": total_30d,
            "total_7d": total_7d,
            "successful_30d": success_30d,
            "failed_30d": failed_30d,
            "cancelled_30d": cancelled_30d,
            "success_rate_pct": success_rate,
        },
        "revenue": {
            "total_30d_inr": revenue_30d,
            "total_30d_display": f"₹{revenue_30d / 100:.2f}" if revenue_30d else "₹0.00",
        },
        "visibility_score": score.to_dict(),
    }


@router.get("/{merchant_id}/visibility", summary="Visibility score with improvement tips")
async def visibility_score(
    merchant_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Detailed visibility score breakdown with actionable tips."""
    _verify_merchant_access(user, merchant_id, session)
    score = compute_visibility_score(merchant_id, session)
    return score.to_dict()


@router.get("/{merchant_id}/transactions/breakdown", summary="Transaction state breakdown")
async def transaction_breakdown(
    merchant_id: str,
    days: int = 30,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Count of transactions by state for the given period."""
    _verify_merchant_access(user, merchant_id, session)
    days = min(max(days, 1), 90)  # clamp to 1–90

    cutoff = utc_now() - timedelta(days=days)

    # Group by state
    results = session.exec(
        select(Transaction.state, func.count(Transaction.id)).where(
            Transaction.merchant_id == merchant_id,
            Transaction.created_at >= cutoff,
        ).group_by(Transaction.state)
    ).all()

    breakdown = {state.value: 0 for state in TransactionState}
    for state, count in results:
        breakdown[state] = count

    return {
        "merchant_id": merchant_id,
        "period_days": days,
        "breakdown": breakdown,
        "total": sum(breakdown.values()),
    }
