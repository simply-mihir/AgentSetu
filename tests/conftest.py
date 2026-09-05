"""
Shared test fixtures.
Uses an in-memory SQLite database with StaticPool so every connection
shares the same in-memory store — avoids cross-test table-not-found errors
that occur with file-based SQLite when the pool recycles connections after
drop_all/create_all cycles.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/api')))

os.environ["DATABASE_URL"] = "sqlite://"       # in-memory, overridden by StaticPool engine
os.environ["APP_MODE"] = "demo"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-prod"
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_demo"
os.environ["RAZORPAY_KEY_SECRET"] = "demo_secret"
os.environ["OPENAI_API_KEY"] = "sk-demo"
os.environ["TESTING"] = "1"  # Phase 12: Disable rate limiting in tests

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, SQLModel

# Import app AFTER env vars are set
from main import app
from database import get_session
import models  # noqa: registers all table metadata

# Single shared in-memory SQLite engine — StaticPool ensures every
# connection (from the fixture session AND from the app's override_get_session)
# sees the same in-memory database.
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    with Session(test_engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Create all tables before each test; drop them after for isolation."""
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session():
    with Session(test_engine) as s:
        yield s


@pytest.fixture
def demo_merchant(session):
    """Insert a demo merchant for tests."""
    from models.merchant import Merchant, Product

    merchant = Merchant(
        merchant_id="test_merchant_01",
        name="TestMart",
        currency="INR",
        max_autonomous_spend_inr=500,
        approval_threshold_inr=1500,
        restricted_categories="[]",
        is_active=True,
    )
    session.add(merchant)
    session.commit()

    product = Product(
        product_id="prod_test_01",
        merchant_id="test_merchant_01",
        name="Test Product",
        category="grocery",
        price_inr=299,
        inventory_count=10,
        availability=True,
        delivery_sla_days_min=1,
        delivery_sla_days_max=3,
        merchant_rating=4.5,
    )
    session.add(product)
    session.commit()
    return merchant, product


@pytest.fixture
def demo_buyer(client):
    """Register and log in a buyer, return auth headers."""
    resp = client.post("/v1/auth/signup", json={
        "email": "buyer@test.com",
        "password": "TestPass123!",
        "role": "BUYER",
    })
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}", "user_id": resp.json()["user_id"]}


@pytest.fixture
def buyer_headers(client):
    """Convenience: just the auth headers dict for a buyer."""
    resp = client.post("/v1/auth/signup", json={
        "email": "integ_buyer@test.com",
        "password": "TestPass123!",
        "role": "BUYER",
    })
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def merchant_owner_headers(client, session):
    """Register a merchant owner and return auth headers + user_id."""
    resp = client.post("/v1/auth/signup", json={
        "email": "owner@test.com",
        "password": "TestPass123!",
        "role": "MERCHANT_OWNER",
    })
    assert resp.status_code == 200, resp.text
    return {
        "Authorization": f"Bearer {resp.json()['access_token']}",
        "user_id": resp.json()["user_id"],
    }
