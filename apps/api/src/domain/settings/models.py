from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class LLMProviderType(str, Enum):
    OLLAMA = "ollama"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class UserSettings:
    user_id: UUID
    id: str = field(default_factory=lambda: str(uuid4()))
    selected_provider: str = LLMProviderType.OLLAMA.value
    selected_model: str = "qwen2.5:7b"
    api_keys: dict[str, str] = field(default_factory=dict)
    ollama_base_url: str = "http://host.docker.internal:11434"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
