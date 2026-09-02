"""
Phase 14: Public API v1 Hardening Tests
Tests consistent error format, security headers, and request validation.
"""
import pytest
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

from fastapi.testclient import TestClient


# ── Consistent error envelope tests ────────────────────────────────────


class TestErrorEnvelope:
    """All API errors should follow the {error: {code, message, request_id, details}} format."""

    def test_404_has_error_envelope(self, client):
        """Non-existent route returns structured error."""
        resp = client.get("/v1/transactions/nonexistent_txn_12345",
                          headers={"Authorization": "Bearer invalid"})
        # Either 401 (invalid token) or 404 — both should have error envelope
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "request_id" in body["error"]

    def test_401_has_error_envelope(self, client):
        """Unauthenticated request returns structured error."""
        resp = client.get("/v1/transactions/")
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "AUTH_REQUIRED"

    def test_422_validation_has_error_envelope(self, client):
        """Pydantic validation error returns structured error with details."""
        resp = client.post("/v1/auth/signup", json={})  # missing required fields
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "validation_errors" in body["error"]["details"]

    def test_method_not_allowed_has_error_envelope(self, client):
        """405 returns structured error."""
        resp = client.delete("/v1/auth/signup")
        assert resp.status_code == 405
        body = resp.json()
        assert "error" in body


# ── Security headers tests ─────────────────────────────────────────────


class TestSecurityHeaders:
    """All responses should include security headers."""

    def test_x_content_type_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self, client):
        resp = client.get("/health")
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_cache_control(self, client):
        resp = client.get("/health")
        assert resp.headers.get("Cache-Control") == "no-store"

    def test_request_id_on_every_response(self, client):
        resp = client.get("/health")
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req_")

    def test_custom_request_id_echoed(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "test-req-123"})
        assert resp.headers["X-Request-ID"] == "test-req-123"


# ── OpenAPI docs tests ─────────────────────────────────────────────────


class TestOpenAPIDocs:
    """OpenAPI docs should be accessible in non-production mode."""

    def test_docs_available(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json_available(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "AgentSetu API"
        assert spec["info"]["version"] == "1.0.0"
        # Check tag descriptions exist
        tags = {t["name"]: t for t in spec.get("tags", [])}
        assert "Auth" in tags
        assert "Payments" in tags
        assert "description" in tags["Auth"]

    def test_openapi_has_auth_endpoints(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec.get("paths", {})
        assert "/v1/auth/signup" in paths
        assert "/v1/auth/login" in paths
        assert "/v1/auth/logout" in paths
        assert "/v1/auth/me" in paths


# ── Request body size limit ────────────────────────────────────────────


class TestRequestLimits:
    """Request body size should be limited."""

    def test_oversized_body_rejected(self, client):
        """Requests over 1 MB should be rejected with 413."""
        # Simulate oversized content-length header
        resp = client.post(
            "/v1/auth/signup",
            json={"email": "a@b.com", "password": "x"},
            headers={"Content-Length": "2000000"},
        )
        # The middleware checks content-length header, so this should be 413
        assert resp.status_code == 413
        body = resp.json()
        assert body["error"]["code"] == "PAYLOAD_TOO_LARGE"


# ── Health endpoints ───────────────────────────────────────────────────


class TestHealthEndpoints:
    """Health and readiness probes."""

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "agentsetu-api"

    def test_ready(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["checks"]["database"] == "ok"

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "AgentSetu API"
