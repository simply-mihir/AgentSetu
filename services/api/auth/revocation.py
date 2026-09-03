"""
N4 FIX: Token revocation store — Redis-backed with in-memory fallback.

Revoked JTIs are stored with a TTL matching the token's remaining lifetime,
so they auto-expire from Redis and never accumulate unboundedly.

In multi-process deployments (gunicorn workers, multiple pods), the Redis
store ensures a JTI revoked in one process is seen by all others.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── In-memory fallback ──────────────────────────────────────────────────────
_fallback_jtis: set[str] = set()
_redis_client = None
_JTI_PREFIX = "agentsetu:jti:revoked:"


def _get_redis():
    """Lazy Redis connection — returns None if Redis is unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    from config import settings
    if not settings.redis_url:
        logger.info("No REDIS_URL configured — using in-memory JTI revocation (not safe for multi-process)")
        return None

    try:
        import redis
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=2,
        )
        # Test connection
        _redis_client.ping()
        logger.info("Redis JTI revocation store connected")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis unavailable for JTI revocation — falling back to in-memory: {e}")
        _redis_client = None
        return None


def revoke_jti(jti: str, ttl_seconds: int = 86400) -> None:
    """
    Mark a JTI as revoked.

    Args:
        jti: The JWT ID to revoke.
        ttl_seconds: How long to keep the revocation (should match token's remaining TTL).
                     Defaults to 24 hours (the default token expiry).
    """
    r = _get_redis()
    if r:
        try:
            r.setex(f"{_JTI_PREFIX}{jti}", ttl_seconds, "1")
            return
        except Exception as e:
            logger.warning(f"Redis revoke failed, falling back to in-memory: {e}")

    _fallback_jtis.add(jti)


def is_revoked(jti: str) -> bool:
    """Check if a JTI has been revoked."""
    r = _get_redis()
    if r:
        try:
            return r.exists(f"{_JTI_PREFIX}{jti}") > 0
        except Exception as e:
            logger.warning(f"Redis check failed, falling back to in-memory: {e}")

    return jti in _fallback_jtis
