"""MerchantUser join table — links users to merchants with a role."""
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint
from typing import Optional
from datetime import datetime
from enum import Enum
from utils.time import utc_now


class MerchantUserRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"


class MerchantUser(SQLModel, table=True):
    __tablename__ = "merchant_users"
    __table_args__ = (
        UniqueConstraint("merchant_id", "user_id", name="uq_merchant_user"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.merchant_id", index=True)
    user_id: str = Field(foreign_key="users.user_id", index=True)
    role: MerchantUserRole = MerchantUserRole.OPERATOR
    created_at: datetime = Field(default_factory=utc_now)
