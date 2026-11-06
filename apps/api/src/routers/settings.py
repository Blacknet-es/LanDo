"""
Settings API Router for LLM Configuration.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.application.settings.catalog import PROVIDER_DEFAULTS
from src.application.settings.list_ollama_models import (
    ListOllamaModelsUseCase,
    OllamaCatalogInvalidResponse,
    OllamaCatalogUnavailable,
)
from src.application.settings.manage_user_settings import (
    GetUserSettingsUseCase,
    UpdateUserSettings,
    UpdateUserSettingsUseCase,
)
from src.domain.settings.models import LLMProviderType
from src.presentation.http.dependencies import (
    get_list_ollama_models_use_case,
    get_update_user_settings_use_case,
    get_user_settings_use_case,
)

router = APIRouter(prefix="/settings/llm", tags=["settings"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class UpdateLLMSettingsRequest(BaseModel):
    selected_provider: LLMProviderType
    selected_model: str
    api_keys: dict[str, str] | None = None
    ollama_base_url: str | None = None


class LLMConfigResponse(BaseModel):
    selected_provider: str
    selected_model: str
    ollama_base_url: str
    available_providers: list[str]
    provider_presets: dict[str, str]
    # Masks API keys so full secrets are never returned in plaintext
    configured_api_keys: dict[str, bool]


class OllamaModelInfo(BaseModel):
    name: str
    size: int | None = None
    modified_at: str | None = None


class OllamaModelsListResponse(BaseModel):
    models: list[OllamaModelInfo]
    base_url: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mask_api_keys(api_keys: dict[str, str] | None) -> dict[str, bool]:
    if not api_keys:
        return {}
    return {k: bool(v and v.strip()) for k, v in api_keys.items()}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=LLMConfigResponse)
def get_llm_settings(
    use_case: GetUserSettingsUseCase = Depends(get_user_settings_use_case),
) -> LLMConfigResponse:
    """Fetch current LLM settings, available providers, and presets."""
    settings = use_case.execute()

    return LLMConfigResponse(
        selected_provider=settings.selected_provider,
        selected_model=settings.selected_model,
        ollama_base_url=settings.ollama_base_url,
        available_providers=[p.value for p in LLMProviderType],
        provider_presets=PROVIDER_DEFAULTS,
        configured_api_keys=_mask_api_keys(settings.api_keys),
    )


@router.put("", response_model=LLMConfigResponse)
def update_llm_settings(
    payload: UpdateLLMSettingsRequest,
    use_case: UpdateUserSettingsUseCase = Depends(get_update_user_settings_use_case),
) -> LLMConfigResponse:
    """Update active LLM provider, model, API keys, and Ollama base URL."""
    try:
        updated = use_case.execute(
            UpdateUserSettings(
                selected_provider=payload.selected_provider,
                selected_model=payload.selected_model,
                api_keys=payload.api_keys,
                ollama_base_url=payload.ollama_base_url,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return LLMConfigResponse(
        selected_provider=updated.selected_provider,
        selected_model=updated.selected_model,
        ollama_base_url=updated.ollama_base_url,
        available_providers=[p.value for p in LLMProviderType],
        provider_presets=PROVIDER_DEFAULTS,
        configured_api_keys=_mask_api_keys(updated.api_keys),
    )


@router.get("/ollama-models", response_model=OllamaModelsListResponse)
async def list_ollama_models(
    use_case: ListOllamaModelsUseCase = Depends(get_list_ollama_models_use_case),
) -> OllamaModelsListResponse:
    """
    Query local Ollama instance /api/tags endpoint to dynamically list
    all models downloaded on the host machine.
    """
    try:
        base_url, models = await use_case.execute()
    except OllamaCatalogUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except OllamaCatalogInvalidResponse as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return OllamaModelsListResponse(
        models=[
            OllamaModelInfo(
                name=model.name,
                size=model.size,
                modified_at=model.modified_at,
            )
            for model in models
        ],
        base_url=base_url,
    )
