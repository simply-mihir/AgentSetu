"""
Application configuration — loaded from environment variables.
Never hard-code secrets. Use .env for local dev, managed secrets in production.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────────
    app_mode: str = "demo"          # demo | sandbox | production
    environment: str = "development"
    base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    secret_key: str = ""            # MUST be set in production — see validation below
    access_token_expire_minutes: int = 60 * 24  # 24 h

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./agentsetu.db"

    # ── Redis (optional) ─────────────────────────────────────────────────────
    redis_url: str = ""

    # ── Razorpay ─────────────────────────────────────────────────────────────
    razorpay_key_id: str = "rzp_test_demo"
    razorpay_key_secret: str = "demo_secret"
    razorpay_webhook_secret: str = "demo_webhook"
    razorpay_webhook_base_url: str = ""     # Phase 8: separate URL for webhooks (public-facing)
    razorpay_oauth_client_id: str = ""
    razorpay_oauth_client_secret: str = ""

    # ── LLM (OpenAI-compatible: OpenAI, Groq, Together, etc.) ───────────────
    openai_api_key: str = "sk-demo"
    openai_base_url: str = ""         # Empty = OpenAI default. Groq: https://api.groq.com/openai/v1
    openai_model: str = "gpt-4o-mini"

    # ── Encryption (for stored tokens) ───────────────────────────────────────
    encryption_key: str = ""

    # ── Observability ────────────────────────────────────────────────────────
    sentry_dsn: str = ""
    log_format: str = "text"  # "text" | "json" — use "json" in production

    # ── Scoring weights ───────────────────────────────────────────────────────
    score_weight_price: float = 0.45
    score_weight_delivery: float = 0.25
    score_weight_rating: float = 0.20
    score_weight_policy: float = 0.10

    # ── Derived ──────────────────────────────────────────────────────────────
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_demo(self) -> bool:
        return self.app_mode == "demo"

    @property
    def is_production(self) -> bool:
        return self.app_mode == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def razorpay_is_live(self) -> bool:
        return self.razorpay_key_id.startswith("rzp_live_")

    @property
    def razorpay_callback_url(self) -> str:
        """Phase 8: Use dedicated webhook URL if set, else fall back to base_url."""
        base = self.razorpay_webhook_base_url or self.base_url
        return f"{base}/v1/webhooks/razorpay"

    @property
    def effective_secret_key(self) -> str:
        """Return configured key or auto-generate for dev (NOT safe for prod)."""
        if self.secret_key:
            return self.secret_key
        if self.is_production:
            raise ValueError("SECRET_KEY must be set in production")
        return "dev-only-insecure-key-change-before-prod"

    def validate_production(self) -> List[str]:
        """Return list of missing required production config."""
        issues = []
        if not self.secret_key:
            issues.append("SECRET_KEY not set")
        if not self.encryption_key:
            issues.append("ENCRYPTION_KEY not set")
        if self.razorpay_key_id == "rzp_test_demo":
            issues.append("RAZORPAY_KEY_ID is still demo value")
        if self.openai_api_key == "sk-demo":
            issues.append("OPENAI_API_KEY is still demo value")
        if self.cors_origins_list == ["http://localhost:3000", "http://localhost:3001"]:
            issues.append("CORS_ORIGINS still set to localhost")
        return issues

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
