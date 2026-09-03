"""
JWT token creation and validation.
Uses python-jose with HS256. Never expose the secret_key.

L8: Added refresh token helpers — generate raw token, hash for storage.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from config import settings
from utils.time import utc_now

ALGORITHM = "HS256"
REFRESH_TOKEN_BYTES = 32  # 256-bit random token
REFRESH_TOKEN_EXPIRY_DAYS = 7


def create_access_token(subject: str, role: str, extra: dict = None) -> str:
    """Create a signed JWT for the given user."""
    expire = utc_now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,           # user_id
        "role": role,
        "exp": expire,
        "iat": utc_now(),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.effective_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT. Returns payload or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.effective_secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# ── L8: Refresh token helpers ────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """Generate a cryptographically random refresh token (URL-safe base64)."""
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def hash_refresh_token(raw_token: str) -> str:
    """SHA-256 hash a raw refresh token for storage. Never store the raw token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()
