"""MeetScribe settings — all configuration via environment variables."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MeetScribe"
    environment: str = "development"
    secret_key: str = "dev-only-change-me-in-production-use-a-long-random-secret"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./meetscribe.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./storage"
    max_upload_mb: int = 100
    transcription_provider: str = "local"  # local | none
    summary_provider: str = "local"  # local | ollama
    cloud_ai_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    cors_origins: str = "http://localhost:3000"
    rate_limit_login: str = "30/minute"
    rate_limit_upload: str = "60/minute"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
