"""Application configuration loaded from environment variables."""

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
    access_token_expire_minutes: int = Field(default=60, gt=0)
    webhook_secret: str = ""

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
        return self


settings = Settings()
