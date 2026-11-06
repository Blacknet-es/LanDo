from typing import Protocol

from src.domain.settings.models import UserSettings


class UserSettingsRepository(Protocol):
    def get_settings(self) -> UserSettings: ...

    def update_settings(self, settings: UserSettings) -> UserSettings: ...
