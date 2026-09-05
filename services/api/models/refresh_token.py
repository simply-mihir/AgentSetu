"""
Refresh token model — L8 FIX.
Supports token rotation: each refresh token is single-use.
Reuse of a revoked token triggers family-wide revocation (compromise detection).
"""
import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from utils.time import utc_now


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: int | None = Field(default=None, primary_key=True)
    token_hash: str = Field(unique=True, index=True)  # SHA-256 of the raw token
    user_id: str = Field(index=True, foreign_key="users.user_id")

    # Token family — all tokens in a rotation chain share a family_id.
    # If a revoked token is reused, ALL tokens in the family are revoked.
    family_id: str = Field(
        default_factory=lambda: f"rtf_{uuid.uuid4().hex[:12]}",
        index=True,
    )

    is_revoked: bool = False
    device_info: str = ""  # User-Agent or device fingerprint (optional)

    created_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime  # Typically 7 days from creation
    revoked_at: datetime | None = None
