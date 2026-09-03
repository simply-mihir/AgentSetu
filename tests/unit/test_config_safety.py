"""Config safety tests — M6, M9, L9, N5, N6 fixes."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/api"))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_config.db")
os.environ.setdefault("APP_MODE", "demo")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest


class TestCallbackVsWebhookURL:
    """M9: callback_url (browser redirect) must NOT point to the webhook endpoint."""

    def test_callback_url_points_to_frontend(self):
        from config import Settings
        s = Settings(
            cors_origins="http://localhost:3000",
            razorpay_payment_callback_url="",
        )
        # Should default to frontend callback page, not webhook
        assert "/payment/callback" in s.razorpay_callback_url
        assert "/v1/webhooks" not in s.razorpay_callback_url

    def test_callback_url_uses_explicit_setting(self):
        from config import Settings
        s = Settings(
            razorpay_payment_callback_url="https://app.example.com/payment/done",
        )
        assert s.razorpay_callback_url == "https://app.example.com/payment/done"

    def test_webhook_url_is_server_endpoint(self):
        from config import Settings
        s = Settings(base_url="https://api.example.com")
        assert s.razorpay_webhook_url == "https://api.example.com/v1/webhooks/razorpay"

    def test_webhook_url_uses_dedicated_base(self):
        from config import Settings
        s = Settings(
            base_url="http://localhost:8000",
            razorpay_webhook_base_url="https://hooks.example.com",
        )
        assert s.razorpay_webhook_url == "https://hooks.example.com/v1/webhooks/razorpay"


class TestLiveKeyGuard:
    """M6: Razorpay live keys must not be used in non-production mode."""

    def test_live_key_detected(self):
        from config import Settings
        s = Settings(razorpay_key_id="rzp_live_abc123")
        assert s.razorpay_is_live is True

    def test_test_key_not_flagged(self):
        from config import Settings
        s = Settings(razorpay_key_id="rzp_test_abc123")
        assert s.razorpay_is_live is False


class TestProductionValidation:
    """L9: ENCRYPTION_KEY validation removed since nothing uses it yet."""

    def test_no_encryption_key_warning(self):
        from config import Settings
        s = Settings(
            secret_key="prod-secret",
            razorpay_key_id="rzp_test_real",
            openai_api_key="sk-real",
            cors_origins="https://app.example.com",
            encryption_key="",
        )
        issues = s.validate_production()
        # L9: encryption_key should NOT be in issues (removed dead validation)
        assert not any("ENCRYPTION_KEY" in i for i in issues)

    def test_missing_secret_key_flagged(self):
        from config import Settings
        s = Settings(secret_key="", app_mode="production")
        issues = s.validate_production()
        assert any("SECRET_KEY" in i for i in issues)


class TestDemoModeSettings:
    """N5/N6: Demo vs production behavior."""

    def test_is_demo(self):
        from config import Settings
        s = Settings(app_mode="demo")
        assert s.is_demo is True
        assert s.is_production is False

    def test_is_production(self):
        from config import Settings
        s = Settings(app_mode="production")
        assert s.is_production is True
        assert s.is_demo is False

    def test_effective_secret_key_dev(self):
        from config import Settings
        s = Settings(app_mode="demo", secret_key="")
        assert s.effective_secret_key == "dev-only-insecure-key-change-before-prod"

    def test_effective_secret_key_prod_raises(self):
        from config import Settings
        s = Settings(app_mode="production", secret_key="")
        with pytest.raises(ValueError, match="SECRET_KEY must be set"):
            _ = s.effective_secret_key
