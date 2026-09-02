"""
Authentication routes — signup, login, me, logout.
Passwords are hashed with bcrypt via passlib. Tokens are JWTs.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from passlib.context import CryptContext

from database import get_session
from models.user import User, BuyerProfile, UserRole, UserStatus
from models.merchant_user import MerchantUser
from auth.jwt import create_access_token
from auth.dependencies import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

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


@router.post("/signup", response_model=TokenResponse, summary="Create a new account")
async def signup(request: SignupRequest, session: Session = Depends(get_session)):
    # Validate role
    allowed_roles = {r.value for r in UserRole} - {"PLATFORM_ADMIN"}
    role = request.role.upper()
    if role not in allowed_roles:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_ROLE", "message": f"Role must be one of {allowed_roles}"}},
        )

    # Check duplicate email
    existing = session.exec(select(User).where(User.email == request.email.lower())).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error": {"code": "EMAIL_TAKEN", "message": "Email already registered."}},
        )

    user = User(
        email=request.email.lower(),
        display_name=request.display_name or request.email.split("@")[0],
        hashed_password=pwd_context.hash(request.password),
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

    token = create_access_token(subject=user.user_id, role=user.role)
    logger.info(f"New user signed up: {user.user_id} ({user.role})")
    return TokenResponse(
        access_token=token,
        user_id=user.user_id,
        role=user.role,
        display_name=user.display_name,
    )


@router.post("/login", response_model=TokenResponse, summary="Login and get access token")
async def login(request: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == request.email.lower())).first()

    if not user or not pwd_context.verify(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."}},
        )

    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCOUNT_SUSPENDED", "message": "Account is suspended."}},
        )

    token = create_access_token(subject=user.user_id, role=user.role)
    logger.info(f"User logged in: {user.user_id}")
    return TokenResponse(
        access_token=token,
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
