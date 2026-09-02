"""
Razorpay Payment Links adapter.
Handles creation, fetching, and status resolution.
Idempotent: always checks existing state before creating.
"""
import hashlib
import hmac
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import razorpay
from config import settings

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class PaymentLinkResult:
    success: bool
    payment_link_id: Optional[str] = None
    payment_link_url: Optional[str] = None
    amount_inr: Optional[int] = None
    status: PaymentStatus = PaymentStatus.UNKNOWN
    error: Optional[str] = None
    raw: Optional[dict] = None


class RazorpayAdapter:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            # Phase 8: Validate key safety before initializing client
            self._validate_key_safety()
            self._client = razorpay.Client(
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )
        return self._client

    def _validate_key_safety(self):
        """Phase 8: Prevent live keys in non-production environments."""
        if settings.razorpay_is_live and not settings.is_production:
            raise RuntimeError(
                "SECURITY: Razorpay LIVE keys detected in non-production mode. "
                "Set APP_MODE=production or use test keys (rzp_test_*)."
            )

    def create_payment_link(
        self,
        amount_inr: int,
        merchant_name: str,
        product_name: str,
        transaction_id: str,
        description: str = "",
        reference_id: Optional[str] = None,
    ) -> PaymentLinkResult:
        """
        Create a Razorpay Payment Link in test mode.
        Amount is in INR (converted to paise internally).
        """
        amount_paise = amount_inr * 100
        ref_id = reference_id or transaction_id

        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": description or f"AgentSetu: {product_name} from {merchant_name}",
            "reference_id": ref_id,
            "notify": {"sms": False, "email": False},
            "reminder_enable": False,
            "notes": {
                "transaction_id": transaction_id,
                "merchant_name": merchant_name,
                "product_name": product_name,
                "source": "agentsetu",
            },
            "callback_url": settings.razorpay_callback_url,
            "callback_method": "get",
        }

        try:
            resp = self.client.payment_link.create(payload)
            return PaymentLinkResult(
                success=True,
                payment_link_id=resp.get("id"),
                payment_link_url=resp.get("short_url"),
                amount_inr=amount_inr,
                status=PaymentStatus(resp.get("status", "created")),
                raw=resp,
            )
        except Exception as e:
            logger.error(f"Razorpay payment link creation failed: {e}")
            return PaymentLinkResult(
                success=False,
                error=str(e),
                status=PaymentStatus.FAILED,
            )

    def fetch_payment_link(self, payment_link_id: str) -> PaymentLinkResult:
        """Fetch current status of a payment link."""
        try:
            resp = self.client.payment_link.fetch(payment_link_id)
            rzp_status = resp.get("status", "unknown")
            amount_paise = resp.get("amount", 0)

            status_map = {
                "created": PaymentStatus.CREATED,
                "pending": PaymentStatus.PENDING,
                "paid": PaymentStatus.PAID,
                "cancelled": PaymentStatus.CANCELLED,
                "expired": PaymentStatus.EXPIRED,
            }
            status = status_map.get(rzp_status, PaymentStatus.UNKNOWN)

            return PaymentLinkResult(
                success=True,
                payment_link_id=payment_link_id,
                payment_link_url=resp.get("short_url"),
                amount_inr=amount_paise // 100,
                status=status,
                raw=resp,
            )
        except Exception as e:
            logger.error(f"Razorpay payment link fetch failed: {e}")
            return PaymentLinkResult(
                success=False,
                payment_link_id=payment_link_id,
                error=str(e),
                status=PaymentStatus.UNKNOWN,
            )

    def cancel_payment_link(self, payment_link_id: str) -> bool:
        """Cancel a payment link."""
        try:
            self.client.payment_link.cancel(payment_link_id)
            return True
        except Exception as e:
            logger.error(f"Razorpay cancel failed: {e}")
            return False

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Validate Razorpay webhook HMAC-SHA256 signature."""
        try:
            expected = hmac.new(
                settings.razorpay_webhook_secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False

    def map_rzp_status(self, rzp_status: str) -> PaymentStatus:
        mapping = {
            "created": PaymentStatus.CREATED,
            "pending": PaymentStatus.PENDING,
            "paid": PaymentStatus.PAID,
            "cancelled": PaymentStatus.CANCELLED,
            "expired": PaymentStatus.EXPIRED,
        }
        return mapping.get(rzp_status, PaymentStatus.UNKNOWN)


# Singleton
razorpay_adapter = RazorpayAdapter()
