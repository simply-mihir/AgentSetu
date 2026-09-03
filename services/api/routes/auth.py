"""
Authentication routes — signup, login, me, logout.
Passwords are hashed with argon2 via passlib. Tokens are JWTs.

Phase 12 hardening:
- Login rate limiting (5/minute per IP)
- Logout / token revocation (JTI blocklist)
- Password strength validation
"""
import logging
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlmodel import Session, select
from slowapi import Limiter
from slowapi.util import get_remote_address
from passlib.context import CryptContext

from database import get_session
from models.user import User, BuyerProfile, UserRole, UserStatus
from models.merchant_user import MerchantUser
from auth.jwt import create_access_token
from auth.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)
# Phase 12: Rate limiter — disabled in test to avoid cross-test exhaustion
_testing = os.environ.get("TESTING", "").lower() in ("1", "true")
limiter = Limiter(key_func=get_remote_address, enabled=not _testing)

# N4 FIX: Redis-backed JTI revocation (falls back to in-memory if Redis unavailable)
from auth.revocation import revoke_jti, is_revoked

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""
    role: str = "BUYER"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    display_name: str


def _validate_password(password: str) -> list[str]:
    """Phase 12: Basic password strength checks."""
    issues = []
    if len(password) < 8:
        issues.append("Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    return issues


def is_token_revoked(jti: str) -> bool:
    """Check if a JWT ID has been revoked. Delegates to Redis-backed store."""
    return is_revoked(jti)


@router.post("/signup", response_model=TokenResponse, summary="Create a new account")
@limiter.limit("10/minute")
async def signup(request: Request, body: SignupRequest, session: Session = Depends(get_session)):
    # Phase 12: Password validation
    pw_issues = _validate_password(body.password)
    if pw_issues:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "WEAK_PASSWORD", "message": "; ".join(pw_issues)}},
        )

    # Validate role
    allowed_roles = {r.value for r in UserRole} - {"PLATFORM_ADMIN"}
    role = body.role.upper()
    if role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_ROLE", "message": f"Role must be one of {allowed_roles}"}},
        )

    # Check duplicate email
    existing = session.exec(select(User).where(User.email == body.email.lower())).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "EMAIL_TAKEN", "message": "Email already registered."}},
        )

    user = User(
        email=body.email.lower(),
        display_name=body.display_name or body.email.split("@")[0],
        hashed_password=pwd_context.hash(body.password),
        role=UserRole(role),
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # Auto-create buyer profile for BUYER role
    if user.role == UserRole.BUYER:
        profile = BuyerProfile(user_id=user.user_id)
        session.add(profile)
        session.commit()

    jti = uuid.uuid4().hex
    token = create_access_token(subject=user.user_id, role=user.role, extra={"jti": jti})
    logger.info(f"New user signed up: {user.user_id} ({user.role})")
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        role=user.role,
        display_name=user.display_name,
    )


@router.post("/login", response_model=TokenResponse, summary="Login and get access token")
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == body.email.lower())).first()

    if not user or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCOUNT_SUSPENDED", "message": "Account is suspended."}},
        )

    jti = uuid.uuid4().hex
    token = create_access_token(subject=user.user_id, role=user.role, extra={"jti": jti})
    logger.info(f"User logged in: {user.user_id}")
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        role=user.role,
        display_name=user.display_name,
    )


@router.post("/logout", summary="Revoke current access token")
async def logout(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """N4 FIX: Logout by revoking the current token's JTI via Redis-backed store."""
    from auth.jwt import decode_access_token
    payload = decode_access_token(credentials.credentials)
    if payload and payload.get("jti"):
        # Calculate remaining TTL so Redis auto-cleans expired revocations
        import time
        exp = payload.get("exp", 0)
        remaining = max(int(exp - time.time()), 60)  # at least 60s
        revoke_jti(payload["jti"], ttl_seconds=remaining)
        logger.info(f"Token revoked for user {user.user_id} (jti={payload['jti']}, ttl={remaining}s)")
    return {"success": True, "message": "Token revoked."}


@router.get("/me", summary="Get current authenticated user")
async def me(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    memberships = session.exec(
        select(MerchantUser).where(MerchantUser.user_id == user.user_id)
    ).all()
    return {
        "user_id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "status": user.status,
        "merchant_memberships": [
            {"merchant_id": m.merchant_id, "role": m.role}
            for m in memberships
        ],
    }
