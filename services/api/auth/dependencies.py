"""
FastAPI authentication dependencies.
Import get_current_user, require_merchant_access, etc. in route handlers.
"""
import logging
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from database import get_session
from models.user import User, UserRole, UserStatus
from models.merchant_user import MerchantUser
from auth.jwt import decode_access_token

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


def _get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """Returns the authenticated User or None (does not raise)."""
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    # Phase 12: Check JTI revocation
    jti = payload.get("jti")
    if jti:
        from routes.auth import is_token_revoked
        if is_token_revoked(jti):
            return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    user = session.exec(select(User).where(User.user_id == user_id)).first()
    if not user or user.status != UserStatus.ACTIVE:
        return None
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    session: Session = Depends(get_session),
) -> User:
    """Raises 401 if not authenticated."""
    user = _get_optional_user(credentials, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "AUTH_REQUIRED", "message": "Authentication required."}},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    session: Session = Depends(get_session),
) -> Optional[User]:
    """Returns User or None — for endpoints that work both authenticated and anonymous."""
    return _get_optional_user(credentials, session)


def require_role(*roles: UserRole):
    """Dependency factory: raises 403 if user doesn't have one of the specified roles."""
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Insufficient role."}},
            )
        return user
    return _check


def get_merchant_access(merchant_id: str, user: User, session: Session) -> MerchantUser:
    """
    Verify user has access to merchant_id.
    PLATFORM_ADMIN bypasses the check.
    Raises 403 if no access.
    """
    if user.role == UserRole.PLATFORM_ADMIN:
        # Admins have read access everywhere; return a virtual ADMIN membership
        return MerchantUser(merchant_id=merchant_id, user_id=user.user_id, role="ADMIN")

    membership = session.exec(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_id,
            MerchantUser.user_id == user.user_id,
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "No access to this merchant."}},
        )
    return membership


def assert_merchant_owner_or_admin(merchant_id: str, user: User, session: Session):
    """Raises 403 unless user is OWNER or ADMIN of merchant_id (or platform admin)."""
    membership = get_merchant_access(merchant_id, user, session)
    if membership.role not in ("OWNER", "ADMIN") and user.role != UserRole.PLATFORM_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Only merchant owner/admin can perform this action."}},
        )
