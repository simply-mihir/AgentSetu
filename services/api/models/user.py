"""User and BuyerProfile models."""
import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from utils.time import utc_now


class UserRole(str, Enum):
    BUYER = "BUYER"
    MERCHANT_OWNER = "MERCHANT_OWNER"
    MERCHANT_ADMIN = "MERCHANT_ADMIN"
    MERCHANT_OPERATOR = "MERCHANT_OPERATOR"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(
        default_factory=lambda: f"usr_{uuid.uuid4().hex[:12]}",
        unique=True,
        index=True,
    )
    email: str = Field(unique=True, index=True)
    display_name: str = ""
    hashed_password: str = ""
    role: UserRole = UserRole.BUYER
    status: UserStatus = UserStatus.ACTIVE
    email_verified: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BuyerProfile(SQLModel, table=True):
    __tablename__ = "buyer_profiles"

    id: int | None = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id", unique=True, index=True)

    # Spending limits
    daily_limit_inr: int = 5000
    per_transaction_auto_limit_inr: int = 500
    approval_threshold_inr: int = 2000

    # Restrictions (JSON arrays stored as strings)
    blocked_categories: str = "[]"
    blocked_merchants: str = "[]"

    default_currency: str = "INR"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
