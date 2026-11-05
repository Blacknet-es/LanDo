"""
Settings API Router for LLM Configuration.
"""

from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from src.domain.settings.models import LLMProviderType
from src.domain.settings.repository import SqlModelUserSettingsRepository
from src.domain.users.models import User
from src.infrastructure.db.session import get_session
from src.infrastructure.llm.factory import DEFAULT_OLLAMA_BASE_URL, PROVIDER_DEFAULTS
from src.security.auth import get_current_user

router = APIRouter(prefix="/settings/llm", tags=["settings"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class UpdateLLMSettingsRequest(BaseModel):
    selected_provider: LLMProviderType
    selected_model: str
    api_keys: Optional[Dict[str, str]] = None
    ollama_base_url: Optional[str] = None


class LLMConfigResponse(BaseModel):
    selected_provider: str
    selected_model: str
    ollama_base_url: str
    available_providers: List[str]
    provider_presets: Dict[str, str]
    # Masks API keys so full secrets are never returned in plaintext
    configured_api_keys: Dict[str, bool]


class OllamaModelInfo(BaseModel):
    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None


class OllamaModelsListResponse(BaseModel):
    models: List[OllamaModelInfo]
    base_url: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mask_api_keys(api_keys: Optional[Dict[str, str]]) -> Dict[str, bool]:
    if not api_keys:
        return {}
    return {k: bool(v and v.strip()) for k, v in api_keys.items()}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=LLMConfigResponse)
def get_llm_settings(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LLMConfigResponse:
    """Fetch current LLM settings, available providers, and presets."""
    repo = SqlModelUserSettingsRepository(session, current_user.id)
    settings = repo.get_settings()

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
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LLMConfigResponse:
    """Update active LLM provider, model, API keys, and Ollama base URL."""
    repo = SqlModelUserSettingsRepository(session, current_user.id)
    settings = repo.get_settings()

    settings.selected_provider = payload.selected_provider.value
    settings.selected_model = payload.selected_model.strip()

    if payload.ollama_base_url:
        settings.ollama_base_url = payload.ollama_base_url.strip()

    if payload.api_keys is not None:
        # Merge or update keys
        current_keys = dict(settings.api_keys or {})
        for provider_name, key_val in payload.api_keys.items():
            if key_val is not None:
                current_keys[provider_name] = key_val
        settings.api_keys = current_keys

    updated = repo.update_settings(settings)

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
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OllamaModelsListResponse:
    """
    Query local Ollama instance /api/tags endpoint to dynamically list
    all models downloaded on the host machine.
    """
    repo = SqlModelUserSettingsRepository(session, current_user.id)
    settings = repo.get_settings()
    base_url = (settings.ollama_base_url or DEFAULT_OLLAMA_BASE_URL).rstrip("/")

    tags_endpoint = f"{base_url}/api/tags"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(tags_endpoint)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Ollama returned HTTP {response.status_code}: {response.text}",
                )
            data = response.json()
            models_raw = data.get("models", [])
            models = [
                OllamaModelInfo(
                    name=m.get("name", ""),
                    size=m.get("size"),
                    modified_at=m.get("modified_at"),
                )
                for m in models_raw
            ]
            return OllamaModelsListResponse(models=models, base_url=base_url)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to reach local Ollama at {base_url}: {str(exc)}",
        )
