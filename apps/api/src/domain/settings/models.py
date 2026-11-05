"""
Settings domain models and enumerations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict
from uuid import UUID, uuid4

from sqlmodel import JSON, Field, Relationship, SQLModel

from src.domain.users.models import User


class LLMProviderType(str, Enum):
    OLLAMA = "ollama"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class UserSettingsModel(SQLModel, table=True):
    __tablename__ = "user_settings"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    selected_provider: str = Field(default=LLMProviderType.OLLAMA.value)
    selected_model: str = Field(default="qwen2.5:7b")
    # Store API keys as a JSON object: {"google": "...", "anthropic": "...", "openai": "..."}
    api_keys: Dict[str, str] = Field(default_factory=dict, sa_type=JSON)
    ollama_base_url: str = Field(default="http://host.docker.internal:11434")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: User = Relationship()
