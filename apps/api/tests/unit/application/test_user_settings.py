from uuid import uuid4

import pytest

from src.application.settings.manage_user_settings import (
    UpdateUserSettings,
    UpdateUserSettingsUseCase,
)
from src.domain.settings.models import LLMProviderType, UserSettings


class InMemorySettingsRepository:
    def __init__(self) -> None:
        self.settings = UserSettings(user_id=uuid4())

    def get_settings(self) -> UserSettings:
        return self.settings

    def update_settings(self, settings: UserSettings) -> UserSettings:
        self.settings = settings
        return settings


def test_update_settings_merges_nonblank_keys_and_normalizes_model() -> None:
    repository = InMemorySettingsRepository()
    repository.settings.api_keys = {"google": "existing"}
    use_case = UpdateUserSettingsUseCase(repository)

    updated = use_case.execute(
        UpdateUserSettings(
            selected_provider=LLMProviderType.OPENAI,
            selected_model="  gpt-test  ",
            api_keys={"google": "", "openai": " new-key "},
        )
    )

    assert updated.selected_provider == "openai"
    assert updated.selected_model == "gpt-test"
    assert updated.api_keys == {"google": "existing", "openai": "new-key"}


def test_update_settings_rejects_blank_model() -> None:
    repository = InMemorySettingsRepository()

    with pytest.raises(ValueError, match="selected_model"):
        UpdateUserSettingsUseCase(repository).execute(
            UpdateUserSettings(
                selected_provider=LLMProviderType.OLLAMA,
                selected_model="   ",
            )
        )
