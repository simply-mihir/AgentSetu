"""
JWT token creation and validation.
Uses python-jose with HS256. Never expose the secret_key.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from config import settings
from utils.time import utc_now

ALGORITHM = "HS256"


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
