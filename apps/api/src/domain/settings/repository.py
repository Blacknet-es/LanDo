"""
User Settings Repository protocol and SQLModel implementation.
"""

from typing import Optional, Protocol, runtime_checkable
from datetime import datetime, timezone
from sqlmodel import Session, select
from src.domain.settings.models import UserSettingsModel, LLMProviderType


@runtime_checkable
class UserSettingsRepository(Protocol):
    def get_settings(self, user_id: str = "default_user") -> UserSettingsModel:
        ...

    def update_settings(self, settings: UserSettingsModel) -> UserSettingsModel:
        ...


class SqlModelUserSettingsRepository(UserSettingsRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_settings(self, user_id: str = "default_user") -> UserSettingsModel:
        settings = self.session.get(UserSettingsModel, user_id)
        if not settings:
            # Create default settings
            settings = UserSettingsModel(
                id=user_id,
                selected_provider=LLMProviderType.OLLAMA.value,
                selected_model="qwen2.5:7b",
                api_keys={},
                ollama_base_url="http://host.docker.internal:11434",
            )
            self.session.add(settings)
            self.session.commit()
            self.session.refresh(settings)
        return settings

    def update_settings(self, settings: UserSettingsModel) -> UserSettingsModel:
        settings.updated_at = datetime.now(timezone.utc)
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return settings

