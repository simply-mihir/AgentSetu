# Import all models so SQLModel metadata registers them for migrations.
from models.merchant import Merchant, Product          # noqa: F401
from models.transaction import Transaction, TransactionState  # noqa: F401
from models.audit import AuditEvent                    # noqa: F401
from models.user import User, BuyerProfile, UserRole, UserStatus  # noqa: F401
from models.capability import AuthorizationCapability, CapabilityStatus  # noqa: F401
from models.webhook import WebhookEvent                # noqa: F401
from models.merchant_user import MerchantUser, MerchantUserRole  # noqa: F401
from models.idempotency import IdempotencyRecord               # noqa: F401
