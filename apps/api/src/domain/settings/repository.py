"""
User Settings Repository protocol and SQLModel implementation.
"""

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.domain.settings.models import LLMProviderType, UserSettingsModel


@runtime_checkable
class UserSettingsRepository(Protocol):
    def get_settings(self) -> UserSettingsModel: ...

    def update_settings(self, settings: UserSettingsModel) -> UserSettingsModel: ...


class SqlModelUserSettingsRepository(UserSettingsRepository):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    def get_settings(self) -> UserSettingsModel:
        settings = self.session.exec(
            select(UserSettingsModel).where(UserSettingsModel.user_id == self.user_id)
        ).first()
        if not settings:
            settings = UserSettingsModel(
                id=str(uuid4()),
                user_id=self.user_id,
                selected_provider=LLMProviderType.OLLAMA.value,
                selected_model="qwen2.5:7b",
                api_keys={},
                ollama_base_url="http://host.docker.internal:11434",
            )
            self.session.add(settings)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
                settings = self.session.exec(
                    select(UserSettingsModel).where(UserSettingsModel.user_id == self.user_id)
                ).first()
                if settings is None:
                    raise
                return settings
            self.session.refresh(settings)
        return settings

    def update_settings(self, settings: UserSettingsModel) -> UserSettingsModel:
        if settings.user_id != self.user_id:
            raise ValueError("Cannot update settings owned by another user.")
        settings.updated_at = datetime.now(timezone.utc)
        self.session.add(settings)
        self.session.commit()
        self.session.refresh(settings)
        return settings
