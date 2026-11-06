from dataclasses import dataclass

from src.domain.settings.models import LLMProviderType, UserSettings
from src.domain.settings.repository import UserSettingsRepository


@dataclass(frozen=True)
class UpdateUserSettings:
    selected_provider: LLMProviderType
    selected_model: str
    api_keys: dict[str, str] | None = None
    ollama_base_url: str | None = None


class GetUserSettingsUseCase:
    def __init__(self, repository: UserSettingsRepository) -> None:
        self._repository = repository

    def execute(self) -> UserSettings:
        return self._repository.get_settings()


class UpdateUserSettingsUseCase:
    def __init__(self, repository: UserSettingsRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdateUserSettings) -> UserSettings:
        model = self._repository.get_settings()
        selected_model = command.selected_model.strip()
        if not selected_model:
            raise ValueError("selected_model must not be blank")

        model.selected_provider = command.selected_provider.value
        model.selected_model = selected_model
        if command.ollama_base_url is not None:
            base_url = command.ollama_base_url.strip()
            if not base_url:
                raise ValueError("ollama_base_url must not be blank")
            model.ollama_base_url = base_url
        if command.api_keys is not None:
            merged_keys = dict(model.api_keys or {})
            merged_keys.update(
                {provider: key.strip() for provider, key in command.api_keys.items() if key.strip()}
            )
            model.api_keys = merged_keys
        return self._repository.update_settings(model)
