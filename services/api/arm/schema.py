"""ARM (Agent-Readable Manifest) schema definitions."""
from pydantic import BaseModel, Field
from typing import List, Optional


class ARMProduct(BaseModel):
    product_id: str
    name: str
    category: str
    price_inr: int
    inventory_count: int
    availability: bool
    delivery_sla_days: List[int]  # [min, max]
    return_policy: str
    merchant_rating: float
    description: str = ""
    payment: Optional[dict] = None


class ARMPolicies(BaseModel):
    max_autonomous_spend_inr: int = 500
    approval_required_above_inr: int = 500
    restricted_categories: List[str] = []
    refund_authority: str = "human_only"


class ARMMerchant(BaseModel):
    id: str
    name: str
    currency: str = "INR"
    description: str = ""
    category: str = ""


class ARMManifest(BaseModel):
    schema_version: str = "arm-0.1"
    merchant: ARMMerchant
    products: List[ARMProduct]
    policies: ARMPolicies
    payment: dict = Field(default_factory=lambda: {
        "provider": "razorpay",
        "type": "payment_link"
    })


class MerchantImportRequest(BaseModel):
    merchant_id: str
    merchant_name: str
    currency: str = "INR"
    description: str = ""
    category: str = ""
    max_autonomous_spend_inr: int = 500
    approval_threshold_inr: int = 500
    restricted_categories: List[str] = []
    products: List[dict]


class PolicyUpdateRequest(BaseModel):
    max_autonomous_spend_inr: int
    approval_threshold_inr: int
    restricted_categories: List[str] = []
    refund_authority: str = "human_only"
