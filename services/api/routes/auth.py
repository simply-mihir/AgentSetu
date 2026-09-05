"""
Authentication routes — signup, login, me, logout, refresh.
Passwords are hashed with argon2 via passlib. Tokens are JWTs.

Phase 12 hardening:
- Login rate limiting (5/minute per IP)
- Logout / token revocation (JTI blocklist)
- Password strength validation

L8: Refresh token rotation with family-based compromise detection.
"""
import logging
import os
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlmodel import Session, select

from auth.dependencies import get_current_user
from auth.jwt import (
    REFRESH_TOKEN_EXPIRY_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from auth.revocation import is_revoked, revoke_jti
from database import get_session
from models.merchant_user import MerchantUser
from models.refresh_token import RefreshToken
from models.user import BuyerProfile, User, UserRole, UserStatus
from utils.time import utc_now

router = APIRouter()
logger = logging.getLogger(__name__)
# Phase 12: Rate limiter — disabled in test to avoid cross-test exhaustion
_testing = os.environ.get("TESTING", "").lower() in ("1", "true")
limiter = Limiter(key_func=get_remote_address, enabled=not _testing)

# N4 FIX: Redis-backed JTI revocation (falls back to in-memory if Redis unavailable)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""
    role: str = "BUYER"


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
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


def _issue_refresh_token(session: Session, user: User, device_info: str = "") -> str:
    """Create a new refresh token for a user. Returns the RAW token (send to client).
    Only the SHA-256 hash is stored in the DB."""
    raw_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_token)

    rt = RefreshToken(
        token_hash=token_hash,
        user_id=user.user_id,
        device_info=device_info,
        expires_at=utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
    )
    session.add(rt)
    session.flush()  # caller commits
    return raw_token


def _revoke_token_family(session: Session, family_id: str) -> int:
    """Revoke ALL tokens in a family (compromise detection). Returns count revoked."""
    tokens = session.exec(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
            RefreshToken.is_revoked.is_(False),
        )
    ).all()
    now = utc_now()
    for t in tokens:
        t.is_revoked = True
        t.revoked_at = now
        session.add(t)
    session.flush()
    return len(tokens)


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

    # L8: Issue refresh token
    device_info = request.headers.get("User-Agent", "")[:200]
    raw_refresh = _issue_refresh_token(session, user, device_info=device_info)
    session.commit()

    logger.info(f"New user signed up: {user.user_id} ({user.role})")
    return TokenResponse(
        access_token=token,
        refresh_token=raw_refresh,
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

    # L8: Issue refresh token
    device_info = request.headers.get("User-Agent", "")[:200]
    raw_refresh = _issue_refresh_token(session, user, device_info=device_info)
    session.commit()

    logger.info(f"User logged in: {user.user_id}")
    return TokenResponse(
        access_token=token,
        refresh_token=raw_refresh,
        user_id=user.user_id,
        role=user.role,
        display_name=user.display_name,
    )


@router.post("/logout", summary="Revoke current access token and all refresh tokens")
async def logout(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    session: Session = Depends(get_session),
):
    """N4 FIX: Logout by revoking the current token's JTI via Redis-backed store.
    L8: Also revokes ALL active refresh tokens for this user."""
    from auth.jwt import decode_access_token
    payload = decode_access_token(credentials.credentials)
    if payload and payload.get("jti"):
        # Calculate remaining TTL so Redis auto-cleans expired revocations
        import time
        exp = payload.get("exp", 0)
        remaining = max(int(exp - time.time()), 60)  # at least 60s
        revoke_jti(payload["jti"], ttl_seconds=remaining)
        logger.info(f"Token revoked for user {user.user_id} (jti={payload['jti']}, ttl={remaining}s)")

    # L8: Revoke all active refresh tokens for this user
    now = utc_now()
    active_rts = session.exec(
        select(RefreshToken).where(
            RefreshToken.user_id == user.user_id,
            RefreshToken.is_revoked.is_(False),
        )
    ).all()
    for rt in active_rts:
        rt.is_revoked = True
        rt.revoked_at = now
        session.add(rt)
    session.commit()
    logger.info(f"Logout: revoked {len(active_rts)} refresh tokens for user {user.user_id}")

    return {"success": True, "message": "Token revoked."}


@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
@limiter.limit("10/minute")
async def refresh_token_endpoint(
    request: Request,
    body: RefreshRequest,
    session: Session = Depends(get_session),
):
    """L8: Refresh token rotation with family-based compromise detection.

    Client sends the raw refresh token. If valid:
    1. Old refresh token is revoked (single-use).
    2. New refresh + access tokens are issued in the same family.
    3. If the old token was ALREADY revoked (replay attack), the ENTIRE family is revoked.
    """
    token_hash = hash_refresh_token(body.refresh_token)

    stored = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).first()

    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token not recognised."}},
        )

    # ── Compromise detection: if this token was already revoked, someone replayed it ──
    if stored.is_revoked:
        family_count = _revoke_token_family(session, stored.family_id)
        session.commit()
        logger.warning(
            f"REFRESH TOKEN REUSE DETECTED — user={stored.user_id} family={stored.family_id} "
            f"revoked {family_count} tokens in family"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_REUSE_DETECTED", "message": "Suspicious activity — all sessions revoked. Please log in again."}},
        )

    # ── Expired? ──
    if stored.expires_at < utc_now():
        stored.is_revoked = True
        stored.revoked_at = utc_now()
        session.add(stored)
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "REFRESH_TOKEN_EXPIRED", "message": "Refresh token expired. Please log in again."}},
        )

    # ── Look up the user ──
    user = session.exec(select(User).where(User.user_id == stored.user_id)).first()
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "ACCOUNT_UNAVAILABLE", "message": "Account is suspended or deleted."}},
        )

    # ── Rotate: revoke old, issue new in the SAME family ──
    stored.is_revoked = True
    stored.revoked_at = utc_now()
    session.add(stored)

    # New refresh token inherits the family_id
    raw_new = generate_refresh_token()
    new_rt = RefreshToken(
        token_hash=hash_refresh_token(raw_new),
        user_id=user.user_id,
        family_id=stored.family_id,  # same family for compromise detection
        device_info=request.headers.get("User-Agent", "")[:200],
        expires_at=utc_now() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
    )
    session.add(new_rt)

    # New access token
    jti = uuid.uuid4().hex
    access = create_access_token(subject=user.user_id, role=user.role, extra={"jti": jti})

    session.commit()
    logger.info(f"Refresh token rotated for user {user.user_id} (family={stored.family_id})")

    return TokenResponse(
        access_token=access,
        refresh_token=raw_new,
        user_id=user.user_id,
        role=user.role,
        display_name=user.display_name,
    )


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
