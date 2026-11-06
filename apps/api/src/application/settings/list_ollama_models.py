from dataclasses import dataclass
from typing import Protocol

from src.domain.settings.repository import UserSettingsRepository


@dataclass(frozen=True)
class OllamaModel:
    name: str
    size: int | None = None
    modified_at: str | None = None


class OllamaCatalogUnavailable(Exception):
    pass


class OllamaCatalogInvalidResponse(Exception):
    pass


class OllamaModelCatalog(Protocol):
    async def list_models(self, base_url: str) -> list[OllamaModel]: ...


class ListOllamaModelsUseCase:
    def __init__(
        self,
        settings_repository: UserSettingsRepository,
        catalog: OllamaModelCatalog,
    ) -> None:
        self._settings_repository = settings_repository
        self._catalog = catalog

    async def execute(self) -> tuple[str, list[OllamaModel]]:
        settings = self._settings_repository.get_settings()
        base_url = (settings.ollama_base_url or "http://host.docker.internal:11434").rstrip("/")
        return base_url, await self._catalog.list_models(base_url)
