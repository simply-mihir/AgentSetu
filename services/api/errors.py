"""
Consistent error response structure.
Every API error returns: {"error": {"code": "...", "message": "...", "request_id": "...", "details": {}}}
"""
from fastapi.responses import JSONResponse
import uuid


def make_error(code: str, message: str, status_code: int, details: dict = None, request_id: str = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id or f"req_{uuid.uuid4().hex[:8]}",
                "details": details or {},
            }
        },
    )


# Standard error codes
class ErrorCode:
    AUTH_REQUIRED = "AUTH_REQUIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"

    # Merchant / product
    MERCHANT_NOT_FOUND = "MERCHANT_NOT_FOUND"
    MERCHANT_INACTIVE = "MERCHANT_INACTIVE"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    PRODUCT_UNAVAILABLE = "PRODUCT_UNAVAILABLE"
    INVENTORY_CHANGED = "INVENTORY_CHANGED"
    PRICE_CHANGED = "PRICE_CHANGED"

    # Policy
    POLICY_BLOCKED = "POLICY_BLOCKED"
    OVER_AUTO_LIMIT = "OVER_AUTO_LIMIT"
    RESTRICTED_CATEGORY = "RESTRICTED_CATEGORY"

    # Capability
    CAPABILITY_NOT_FOUND = "CAPABILITY_NOT_FOUND"
    CAPABILITY_EXPIRED = "CAPABILITY_EXPIRED"
    CAPABILITY_CONSUMED = "CAPABILITY_CONSUMED"
    CAPABILITY_REVOKED = "CAPABILITY_REVOKED"
    CAPABILITY_AMOUNT_MISMATCH = "CAPABILITY_AMOUNT_MISMATCH"
    CAPABILITY_TRANSACTION_MISMATCH = "CAPABILITY_TRANSACTION_MISMATCH"
    CAPABILITY_MERCHANT_MISMATCH = "CAPABILITY_MERCHANT_MISMATCH"

    # Payment
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PAYMENT_UNKNOWN = "PAYMENT_UNKNOWN"
    PAYMENT_LINK_EXPIRED = "PAYMENT_LINK_EXPIRED"

    # Webhook
    WEBHOOK_INVALID = "WEBHOOK_INVALID"
    WEBHOOK_DUPLICATE = "WEBHOOK_DUPLICATE"

    # ARM
    ARM_INVALID = "ARM_INVALID"
