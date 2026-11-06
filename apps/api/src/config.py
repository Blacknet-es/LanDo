"""Application configuration loaded from environment variables."""

import base64
import hashlib

from cryptography.fernet import Fernet
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: str = "development"
    secret_key: str = "dev-only-secret-key-change-in-production"
    llm_secrets_encryption_key: str = ""
    access_token_expire_minutes: int = Field(default=60, gt=0)
    webhook_secret: str = ""
    n8n_webhook_url: str = ""

    # Database
    database_url: str = "postgresql://lando:lando_secret@localhost:5432/lando_db"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # CORS
    allowed_origins: str = "http://localhost:8081,http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @model_validator(mode="after")
    def production_requires_strong_secret(self) -> "Settings":
        if self.environment.lower() == "production" and (
            self.secret_key == "dev-only-secret-key-change-in-production"
            or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        if self.environment.lower() == "production" and not self.llm_secrets_encryption_key:
            raise ValueError("LLM_SECRETS_ENCRYPTION_KEY is required in production")
        if self.llm_secrets_encryption_key:
            try:
                Fernet(self.llm_secrets_encryption_key.encode("ascii"))
            except (ValueError, UnicodeEncodeError) as exc:
                raise ValueError("LLM_SECRETS_ENCRYPTION_KEY must be a valid Fernet key") from exc
        return self

    @property
    def resolved_llm_secrets_encryption_key(self) -> str:
        if self.llm_secrets_encryption_key:
            return self.llm_secrets_encryption_key
        derived = hashlib.sha256(self.secret_key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(derived).decode("ascii")


settings = Settings()
