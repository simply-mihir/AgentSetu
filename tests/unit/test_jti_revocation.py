"""N4: JTI revocation tests — in-memory fallback when Redis unavailable."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_jti.db")
os.environ.setdefault("APP_MODE", "demo")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("REDIS_URL", "")  # Force in-memory fallback

import pytest


class TestJTIRevocationFallback:
    """When Redis is unavailable, JTI revocation uses in-memory set."""

    def test_revoke_and_check(self):
        from auth.revocation import revoke_jti, is_revoked, _fallback_jtis
        _fallback_jtis.clear()

        revoke_jti("jti_test_001", ttl_seconds=60)
        assert is_revoked("jti_test_001") is True

    def test_unknown_jti_not_revoked(self):
        from auth.revocation import is_revoked
        assert is_revoked("jti_never_existed") is False

    def test_revoke_multiple(self):
        from auth.revocation import revoke_jti, is_revoked, _fallback_jtis
        _fallback_jtis.clear()

        revoke_jti("jti_a", ttl_seconds=60)
        revoke_jti("jti_b", ttl_seconds=60)
        assert is_revoked("jti_a") is True
        assert is_revoked("jti_b") is True
        assert is_revoked("jti_c") is False
