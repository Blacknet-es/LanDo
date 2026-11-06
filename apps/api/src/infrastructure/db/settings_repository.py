from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.config import settings as app_settings
from src.domain.settings.models import LLMProviderType, UserSettings
from src.domain.settings.repository import UserSettingsRepository
from src.infrastructure.db.models import UserSettingsModel
from src.infrastructure.security.secrets import SecretCipher


class SqlModelUserSettingsRepository(UserSettingsRepository):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id
        self._secret_cipher = SecretCipher(app_settings.resolved_llm_secrets_encryption_key)

    def _to_domain(self, model: UserSettingsModel) -> UserSettings:
        return UserSettings(
            id=model.id,
            user_id=model.user_id,
            selected_provider=model.selected_provider,
            selected_model=model.selected_model,
            api_keys={
                provider: self._secret_cipher.decrypt(secret)
                for provider, secret in (model.api_keys or {}).items()
            },
            ollama_base_url=model.ollama_base_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def get_settings(self) -> UserSettings:
        model = self.session.exec(
            select(UserSettingsModel).where(UserSettingsModel.user_id == self.user_id)
        ).first()
        if model is None:
            model = UserSettingsModel(
                id=str(uuid4()),
                user_id=self.user_id,
                selected_provider=LLMProviderType.OLLAMA.value,
                selected_model="qwen2.5:7b",
                api_keys={},
                ollama_base_url="http://host.docker.internal:11434",
            )
            self.session.add(model)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
                model = self.session.exec(
                    select(UserSettingsModel).where(UserSettingsModel.user_id == self.user_id)
                ).first()
                if model is None:
                    raise
                return self._to_domain(model)
            self.session.refresh(model)
        return self._to_domain(model)

    def update_settings(self, settings: UserSettings) -> UserSettings:
        if settings.user_id != self.user_id:
            raise ValueError("Cannot update settings owned by another user.")
        model = self.session.exec(
            select(UserSettingsModel).where(UserSettingsModel.user_id == self.user_id)
        ).first()
        if model is None:
            raise ValueError("Settings do not exist for this user.")
        model.selected_provider = settings.selected_provider
        model.selected_model = settings.selected_model
        model.api_keys = {
            provider: self._secret_cipher.encrypt(secret)
            for provider, secret in settings.api_keys.items()
        }
        model.ollama_base_url = settings.ollama_base_url
        model.updated_at = datetime.now(UTC)
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)
