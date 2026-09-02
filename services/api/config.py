from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Razorpay
    razorpay_key_id: str = "rzp_test_demo"
    razorpay_key_secret: str = "demo_secret"
    razorpay_webhook_secret: str = "demo_webhook"

    # OpenAI
    openai_api_key: str = "sk-demo"
    openai_model: str = "gpt-4o-mini"

    # App
    database_url: str = "sqlite:///./agentsetu.db"
    secret_key: str = "dev-secret-key-change-in-prod"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    base_url: str = "http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
