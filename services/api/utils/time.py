"""
N9 FIX: UTC time helper — replaces deprecated datetime.utcnow().

Returns a naive UTC datetime (no timezone info) for backward compatibility
with existing SQLModel/SQLAlchemy DateTime columns that expect naive datetimes.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current UTC time as a naive datetime (no tzinfo).
    Drop-in replacement for the deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
