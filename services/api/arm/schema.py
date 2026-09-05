"""
ARM (Agent-Readable Manifest) schema definitions.
arm-0.2: Added manifest_id, generated_at, manifest_hash, removed payment_link_id
from product-level data (internal implementation detail).
"""
import hashlib
import json
import uuid

from pydantic import BaseModel, Field

from utils.time import utc_now


class ARMProduct(BaseModel):
    product_id: str
    name: str
    category: str
    price_inr: int
    inventory_count: int
    availability: bool
    delivery_sla_days: list[int]  # [min, max]
    return_policy: str
    merchant_rating: float
    description: str = ""
    # Phase 9: payment_link_id REMOVED from ARM products.
    # It is an internal Razorpay reference that must never leak into the manifest.
    # The payment provider info lives at manifest level only.


class ARMPolicies(BaseModel):
    max_autonomous_spend_inr: int = 500
    approval_required_above_inr: int = 500
    restricted_categories: list[str] = []
    refund_authority: str = "human_only"


class ARMMerchant(BaseModel):
    id: str
    name: str
    currency: str = "INR"
    description: str = ""
    category: str = ""


class ARMManifest(BaseModel):
    schema_version: str = "arm-0.2"
    manifest_id: str = Field(default_factory=lambda: f"arm_{uuid.uuid4().hex[:12]}")
    generated_at: str = Field(default_factory=lambda: utc_now().isoformat() + "Z")
    manifest_hash: str = ""     # Computed after serialization
    merchant: ARMMerchant
    products: list[ARMProduct]
    policies: ARMPolicies
    payment: dict = Field(default_factory=lambda: {
        "provider": "razorpay",
        "type": "payment_link"
    })

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of manifest content (excluding per-generation fields)."""
        data = self.model_dump()
        data.pop("manifest_hash", None)
        data.pop("manifest_id", None)   # unique per generation
        data.pop("generated_at", None)  # timestamp per generation
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()


class MerchantImportRequest(BaseModel):
    merchant_id: str
    merchant_name: str
    currency: str = "INR"
    description: str = ""
    category: str = ""
    max_autonomous_spend_inr: int = 500
    approval_threshold_inr: int = 500
    restricted_categories: list[str] = []
    products: list[dict]


class PolicyUpdateRequest(BaseModel):
    max_autonomous_spend_inr: int
    approval_threshold_inr: int
    restricted_categories: list[str] = []
    refund_authority: str = "human_only"
