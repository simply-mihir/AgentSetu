"""L1: ARM cache TTL tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_arm_cache.db")
os.environ.setdefault("APP_MODE", "demo")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from datetime import timedelta
from sqlmodel import Session, create_engine, SQLModel, select
from utils.time import utc_now

TEST_DB = "sqlite:///./test_arm_cache.db"
test_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})

import models  # noqa — registers metadata


@pytest.fixture(autouse=True)
def db():
    SQLModel.metadata.create_all(test_engine)
    yield
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture
def session():
    with Session(test_engine) as s:
        yield s


def _seed_merchant(session):
    from models.merchant import Merchant, Product
    merchant = Merchant(
        merchant_id="m_cache_01",
        name="Cache Test Merchant",
        max_autonomous_spend_inr=500,
        approval_threshold_inr=1000,
    )
    session.add(merchant)
    session.commit()

    product = Product(
        product_id="p_cache_01",
        merchant_id="m_cache_01",
        name="Widget",
        category="electronics",
        price_inr=299,
        inventory_count=5,
    )
    session.add(product)
    session.commit()
    return merchant


class TestARMCacheTTL:
    def test_first_call_generates_arm(self, session):
        _seed_merchant(session)
        from arm.generator import get_or_generate_arm
        arm = get_or_generate_arm("m_cache_01", session)
        assert arm is not None
        assert arm.schema_version == "arm-0.2"
        assert len(arm.products) == 1

    def test_second_call_returns_cached(self, session):
        _seed_merchant(session)
        from arm.generator import get_or_generate_arm
        arm1 = get_or_generate_arm("m_cache_01", session)
        arm2 = get_or_generate_arm("m_cache_01", session)
        # Same manifest_id because content didn't change
        assert arm1.manifest_id == arm2.manifest_id

    def test_force_refresh_regenerates(self, session):
        _seed_merchant(session)
        from arm.generator import get_or_generate_arm
        arm1 = get_or_generate_arm("m_cache_01", session)
        arm2 = get_or_generate_arm("m_cache_01", session, force_refresh=True)
        # Content hash is the same but it's a fresh generation
        assert arm2.manifest_hash == arm1.manifest_hash

    def test_nonexistent_merchant_returns_none(self, session):
        from arm.generator import get_or_generate_arm
        result = get_or_generate_arm("m_nonexistent", session)
        assert result is None

    def test_cache_updates_on_product_change(self, session):
        """When product data changes, the ARM content hash changes."""
        merchant = _seed_merchant(session)
        from arm.generator import get_or_generate_arm
        from models.merchant import Product

        arm1 = get_or_generate_arm("m_cache_01", session)
        hash1 = arm1.manifest_hash

        # Change product price
        product = session.exec(
            select(Product).where(Product.product_id == "p_cache_01")
        ).first()
        product.price_inr = 399
        session.add(product)
        session.commit()

        arm2 = get_or_generate_arm("m_cache_01", session, force_refresh=True)
        assert arm2.manifest_hash != hash1
