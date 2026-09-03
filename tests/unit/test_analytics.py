"""
Tests for N11 — Merchant Analytics & Visibility Score.

Covers:
  - Visibility score computation (deterministic, all signal paths)
  - Analytics overview endpoint (auth + data)
  - Visibility endpoint
  - Transaction breakdown endpoint
  - Access control (user can only see their own merchants)
"""
import time
import pytest
from datetime import timedelta
from sqlmodel import Session

from models.merchant import Merchant, Product
from models.transaction import Transaction, TransactionState
from models.merchant_user import MerchantUser, MerchantUserRole
from services.visibility_score import compute_visibility_score, ScoreBreakdown
from utils.time import utc_now


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_merchant_with_owner(client, session, suffix="") -> dict:
    """Create a merchant owner user, a merchant, and link them. Return metadata."""
    ts = int(time.time() * 1000)
    email = f"analytics_owner_{ts}{suffix}@test.com"

    # Sign up as merchant owner
    resp = client.post("/v1/auth/signup", json={
        "email": email,
        "password": "StrongPass1",
        "role": "MERCHANT_OWNER",
    })
    assert resp.status_code == 200, resp.text
    user_data = resp.json()

    # Create merchant
    merchant_id = f"m_analytics_{ts}{suffix}"
    merchant = Merchant(
        merchant_id=merchant_id,
        name=f"Analytics Test Store {suffix}",
        description="A test store for analytics testing with enough chars",
        category="electronics",
        max_autonomous_spend_inr=500,
        approval_threshold_inr=1500,
        restricted_categories='["weapons"]',
        is_active=True,
    )
    session.add(merchant)
    session.flush()

    # Link user to merchant
    mu = MerchantUser(
        user_id=user_data["user_id"],
        merchant_id=merchant_id,
        role=MerchantUserRole.OWNER,
    )
    session.add(mu)
    session.commit()

    return {
        "merchant_id": merchant_id,
        "user_id": user_data["user_id"],
        "access_token": user_data["access_token"],
        "headers": {"Authorization": f"Bearer {user_data['access_token']}"},
    }


def _add_products(session, merchant_id, count=3, complete=True):
    """Add products to a merchant."""
    for i in range(count):
        p = Product(
            product_id=f"prod_{merchant_id}_{i}",
            merchant_id=merchant_id,
            name=f"Product {i}",
            category="gadgets",
            price_inr=1000 + i * 100,
            inventory_count=10,
            availability=True,
            description="A detailed product description for testing" if complete else "",
            image_url="https://example.com/img.jpg" if complete else "",
        )
        session.add(p)
    session.commit()


def _add_transactions(session, merchant_id, buyer_id="buyer_1", success=3, failed=1, cancelled=0):
    """Add transactions for a merchant."""
    for i in range(success):
        txn = Transaction(
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            state=TransactionState.RECEIPT_ISSUED,
            amount_inr=1000,
        )
        session.add(txn)
    for i in range(failed):
        txn = Transaction(
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            state=TransactionState.PAYMENT_FAILED,
            amount_inr=500,
        )
        session.add(txn)
    for i in range(cancelled):
        txn = Transaction(
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            state=TransactionState.CANCELLED,
            amount_inr=0,
        )
        session.add(txn)
    session.commit()


# ── Visibility Score Unit Tests ───────────────────────────────────────────────

def test_visibility_score_empty_merchant(client, session):
    """A bare merchant with no products/transactions gets a low score."""
    info = _create_merchant_with_owner(client, session, suffix="_empty")
    score = compute_visibility_score(info["merchant_id"], session)

    assert isinstance(score, ScoreBreakdown)
    assert score.catalog_completeness == 0
    assert score.transaction_health == 0
    assert score.total < 50
    assert len(score.tips) > 0  # should have improvement tips


def test_visibility_score_with_products(client, session):
    """Adding complete products increases catalog_completeness."""
    info = _create_merchant_with_owner(client, session, suffix="_prods")
    _add_products(session, info["merchant_id"], count=5, complete=True)

    score = compute_visibility_score(info["merchant_id"], session)
    assert score.catalog_completeness > 15  # should be high with 5 complete products


def test_visibility_score_incomplete_products(client, session):
    """Products without descriptions/images score lower."""
    info = _create_merchant_with_owner(client, session, suffix="_incomplete")
    _add_products(session, info["merchant_id"], count=3, complete=False)

    score = compute_visibility_score(info["merchant_id"], session)
    # Should be lower than complete products
    assert score.catalog_completeness < 20
    assert any("description" in t.lower() or "image" in t.lower() for t in score.tips)


def test_visibility_score_with_transactions(client, session):
    """Successful transactions increase transaction_health."""
    info = _create_merchant_with_owner(client, session, suffix="_txns")
    _add_transactions(session, info["merchant_id"], success=5, failed=0)

    score = compute_visibility_score(info["merchant_id"], session)
    assert score.transaction_health > 10


def test_visibility_score_deterministic(client, session):
    """Same merchant data always produces the same score."""
    info = _create_merchant_with_owner(client, session, suffix="_det")
    _add_products(session, info["merchant_id"], count=3)
    _add_transactions(session, info["merchant_id"], success=2, failed=1)

    score1 = compute_visibility_score(info["merchant_id"], session)
    score2 = compute_visibility_score(info["merchant_id"], session)
    assert score1.total == score2.total
    assert score1.catalog_completeness == score2.catalog_completeness


def test_visibility_score_nonexistent_merchant(session):
    """Non-existent merchant gets a zero score with tips."""
    score = compute_visibility_score("nonexistent_merchant", session)
    assert score.total == 0
    assert "not found" in score.tips[0].lower()


def test_visibility_score_to_dict(client, session):
    """to_dict() returns the expected structure."""
    info = _create_merchant_with_owner(client, session, suffix="_dict")
    score = compute_visibility_score(info["merchant_id"], session)
    d = score.to_dict()

    assert "total" in d
    assert "breakdown" in d
    assert "tips" in d
    assert set(d["breakdown"].keys()) == {
        "catalog_completeness",
        "policy_quality",
        "transaction_health",
        "arm_freshness",
        "account_standing",
    }


# ── Analytics Endpoint Tests ──────────────────────────────────────────────────

def test_analytics_overview(client, session):
    """GET /analytics/{id}/overview returns full analytics."""
    info = _create_merchant_with_owner(client, session, suffix="_overview")
    _add_products(session, info["merchant_id"])
    _add_transactions(session, info["merchant_id"], success=3, failed=1, cancelled=1)

    resp = client.get(
        f"/v1/analytics/{info['merchant_id']}/overview",
        headers=info["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["merchant_id"] == info["merchant_id"]
    assert data["transactions"]["total_30d"] == 5
    assert data["transactions"]["successful_30d"] == 3
    assert data["transactions"]["failed_30d"] == 1
    assert data["transactions"]["cancelled_30d"] == 1
    assert "visibility_score" in data
    assert "total" in data["visibility_score"]


def test_analytics_visibility(client, session):
    """GET /analytics/{id}/visibility returns score breakdown."""
    info = _create_merchant_with_owner(client, session, suffix="_vis")
    resp = client.get(
        f"/v1/analytics/{info['merchant_id']}/visibility",
        headers=info["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "breakdown" in data
    assert "tips" in data


def test_analytics_transaction_breakdown(client, session):
    """GET /analytics/{id}/transactions/breakdown returns per-state counts."""
    info = _create_merchant_with_owner(client, session, suffix="_bkdn")
    _add_transactions(session, info["merchant_id"], success=2, failed=1)

    resp = client.get(
        f"/v1/analytics/{info['merchant_id']}/transactions/breakdown",
        headers=info["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["breakdown"]["RECEIPT_ISSUED"] == 2
    assert data["breakdown"]["PAYMENT_FAILED"] == 1


def test_analytics_requires_auth(client):
    """Analytics endpoints require authentication."""
    resp = client.get("/v1/analytics/m_fake/overview")
    assert resp.status_code in (401, 403)


def test_analytics_denies_wrong_merchant(client, session):
    """User cannot access a merchant they don't own."""
    info = _create_merchant_with_owner(client, session, suffix="_deny")

    # Create a second merchant the user does NOT own
    other_merchant = Merchant(
        merchant_id="m_other_merchant",
        name="Other Store",
        is_active=True,
    )
    session.add(other_merchant)
    session.commit()

    resp = client.get(
        "/v1/analytics/m_other_merchant/overview",
        headers=info["headers"],
    )
    assert resp.status_code == 403
