from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import json


class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: str = Field(index=True)
    merchant_id: str = Field(foreign_key="merchants.merchant_id", index=True)

    name: str
    category: str
    price_inr: int  # in paise / normalized INR
    inventory_count: int = 0
    availability: bool = True
    delivery_sla_days_min: int = 1
    delivery_sla_days_max: int = 3
    return_policy: str = "7_days"
    merchant_rating: float = 4.0
    description: str = ""
    image_url: str = ""

    # Razorpay payment link mapping
    payment_link_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    merchant: Optional["Merchant"] = Relationship(back_populates="products")


class Merchant(SQLModel, table=True):
    __tablename__ = "merchants"

    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: str = Field(unique=True, index=True)
    name: str
    currency: str = "INR"
    description: str = ""
    category: str = ""
    logo_url: str = ""

    # Policies
    max_autonomous_spend_inr: int = 500
    approval_threshold_inr: int = 500
    restricted_categories: str = "[]"  # JSON array stored as string
    refund_authority: str = "human_only"

    # ARM
    arm_json: Optional[str] = None  # Full ARM manifest cached
    arm_version: str = "arm-0.1"
    is_active: bool = True

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    products: List[Product] = Relationship(back_populates="merchant")

    def get_restricted_categories(self) -> List[str]:
        try:
            return json.loads(self.restricted_categories)
        except Exception:
            return []

    def set_restricted_categories(self, cats: List[str]):
        self.restricted_categories = json.dumps(cats)
