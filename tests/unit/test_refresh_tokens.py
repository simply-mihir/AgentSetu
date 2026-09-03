"""
Tests for L8 — Refresh Token Rotation with family-based compromise detection.

Covers:
  - Token generation and hashing
  - Login/signup return refresh_token
  - POST /auth/refresh rotates tokens (old revoked, new issued)
  - Replay detection: reusing a revoked token revokes the entire family
  - Expired tokens are rejected
  - Logout revokes all refresh tokens
"""
import time
import pytest
from datetime import timedelta
from sqlmodel import select

from auth.jwt import generate_refresh_token, hash_refresh_token
from models.refresh_token import RefreshToken
from utils.time import utc_now


# ── Unit tests for helpers ────────────────────────────────────────────────────

def test_generate_refresh_token_is_unique():
    """Each call produces a distinct, URL-safe token."""
    t1 = generate_refresh_token()
    t2 = generate_refresh_token()
    assert t1 != t2
    assert len(t1) > 30  # 32 bytes → ~43 chars in base64


def test_hash_refresh_token_deterministic():
    """Same input always produces the same SHA-256 hash."""
    raw = "test-token-abc123"
    assert hash_refresh_token(raw) == hash_refresh_token(raw)


def test_hash_refresh_token_different_for_different_input():
    """Different tokens produce different hashes."""
    h1 = hash_refresh_token("token-a")
    h2 = hash_refresh_token("token-b")
    assert h1 != h2


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.fixture
def _user_creds(client):
    """Create a test user and return credentials + tokens."""
    email = f"rt_test_{int(time.time() * 1000)}@example.com"
    password = "StrongPass1"
    resp = client.post("/v1/auth/signup", json={
        "email": email,
        "password": password,
        "role": "BUYER",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return {
        "email": email,
        "password": password,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "user_id": data["user_id"],
    }


def test_signup_returns_refresh_token(client):
    """Signup must return a refresh_token alongside the access_token."""
    resp = client.post("/v1/auth/signup", json={
        "email": f"rt_signup_{int(time.time() * 1000)}@example.com",
        "password": "StrongPass1",
        "role": "BUYER",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "refresh_token" in data
    assert data["refresh_token"] is not None
    assert len(data["refresh_token"]) > 30


def test_login_returns_refresh_token(_user_creds, client):
    """Login must return a refresh_token."""
    resp = client.post("/v1/auth/login", json={
        "email": _user_creds["email"],
        "password": _user_creds["password"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["refresh_token"] is not None


def test_refresh_rotates_token(_user_creds, client):
    """POST /auth/refresh returns new tokens and revokes the old."""
    old_rt = _user_creds["refresh_token"]
    resp = client.post("/v1/auth/refresh", json={"refresh_token": old_rt})
    assert resp.status_code == 200
    data = resp.json()

    # New tokens returned
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["refresh_token"] != old_rt  # rotated


def test_refresh_replay_detected(_user_creds, client):
    """Replaying a used refresh token returns TOKEN_REUSE_DETECTED."""
    old_rt = _user_creds["refresh_token"]

    # First use: succeeds
    resp1 = client.post("/v1/auth/refresh", json={"refresh_token": old_rt})
    assert resp1.status_code == 200

    # Replay: fails with reuse detection
    replay = client.post("/v1/auth/refresh", json={"refresh_token": old_rt})
    assert replay.status_code == 401
    assert "TOKEN_REUSE_DETECTED" in replay.text


def test_refresh_reuse_revokes_entire_family(_user_creds, client):
    """Replaying a used refresh token must revoke the ENTIRE family."""
    old_rt = _user_creds["refresh_token"]

    # First refresh: succeeds and gives new token
    resp1 = client.post("/v1/auth/refresh", json={"refresh_token": old_rt})
    assert resp1.status_code == 200
    new_rt = resp1.json()["refresh_token"]

    # Replay the OLD token — triggers family-wide revocation
    replay = client.post("/v1/auth/refresh", json={"refresh_token": old_rt})
    assert replay.status_code == 401

    # The NEW token should ALSO be revoked (family compromised)
    resp2 = client.post("/v1/auth/refresh", json={"refresh_token": new_rt})
    assert resp2.status_code == 401


def test_refresh_invalid_token_rejected(client):
    """A completely unknown refresh token returns 401."""
    resp = client.post("/v1/auth/refresh", json={"refresh_token": "bogus-token-xyz"})
    assert resp.status_code == 401
    assert "INVALID_REFRESH_TOKEN" in resp.text


def test_refresh_expired_token_rejected(_user_creds, client, session):
    """An expired refresh token returns 401."""
    token_hash = hash_refresh_token(_user_creds["refresh_token"])
    stored = session.exec(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).first()
    assert stored is not None
    stored.expires_at = utc_now() - timedelta(hours=1)
    session.add(stored)
    session.commit()

    resp = client.post("/v1/auth/refresh", json={"refresh_token": _user_creds["refresh_token"]})
    assert resp.status_code == 401
    assert "REFRESH_TOKEN_EXPIRED" in resp.text


def test_logout_revokes_refresh_tokens(_user_creds, client):
    """Logout should revoke all active refresh tokens for the user."""
    headers = {"Authorization": f"Bearer {_user_creds['access_token']}"}
    resp = client.post("/v1/auth/logout", headers=headers)
    assert resp.status_code == 200

    # The refresh token should no longer work
    resp2 = client.post("/v1/auth/refresh", json={"refresh_token": _user_creds["refresh_token"]})
    assert resp2.status_code == 401
