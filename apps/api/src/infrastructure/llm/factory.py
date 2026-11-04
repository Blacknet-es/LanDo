"""
Multi-provider LLM Factory.

Provides unified construction of LangChain BaseChatModel instances across:
- local Ollama
- Google Generative AI (Gemini)
- Anthropic (Claude)
- OpenAI (GPT)

Includes safe fallback handling to local Ollama if an API key is missing or invalid.
"""

from typing import Optional
import logging
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_BASE_URL = "http://host.docker.internal:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b"

# Provider default models
PROVIDER_DEFAULTS = {
    "ollama": "qwen2.5:7b",
    "google": "gemini-1.5-flash",
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4o-mini",
}


def get_llm_provider(
    provider_type: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.2,
) -> BaseChatModel:
    """
    Factory function returning a configured BaseChatModel instance.

    Fallback behavior:
    If a cloud provider (google, anthropic, openai) is requested without an API key,
    it logs a warning and falls back to local Ollama to ensure offline/local-first resilience.
    """
    provider = (provider_type or "ollama").lower().strip()
    target_model = model_name or PROVIDER_DEFAULTS.get(provider, DEFAULT_OLLAMA_MODEL)

    # ── 1. Ollama (Local) ────────────────────────────────────────────────────────
    if provider == "ollama":
        url = base_url or DEFAULT_OLLAMA_BASE_URL
        return ChatOllama(
            model=target_model,
            base_url=url,
            temperature=temperature,
        )

    # ── 2. Google Gemini ────────────────────────────────────────────────────────
    if provider == "google":
        if not api_key:
            logger.warning(
                "Google Gemini selected but no API key provided. Falling back to Ollama (%s).",
                DEFAULT_OLLAMA_MODEL,
            )
            return get_llm_provider("ollama", base_url=base_url)
        return ChatGoogleGenerativeAI(
            model=target_model,
            google_api_key=api_key,
            temperature=temperature,
        )

    # ── 3. Anthropic Claude ──────────────────────────────────────────────────────
    if provider == "anthropic":
        if not api_key:
            logger.warning(
                "Anthropic selected but no API key provided. Falling back to Ollama (%s).",
                DEFAULT_OLLAMA_MODEL,
            )
            return get_llm_provider("ollama", base_url=base_url)
        return ChatAnthropic(
            model_name=target_model,
            anthropic_api_key=api_key,
            temperature=temperature,
        )

    # ── 4. OpenAI ────────────────────────────────────────────────────────────────
    if provider == "openai":
        if not api_key:
            logger.warning(
                "OpenAI selected but no API key provided. Falling back to Ollama (%s).",
                DEFAULT_OLLAMA_MODEL,
            )
            return get_llm_provider("ollama", base_url=base_url)
        return ChatOpenAI(
            model=target_model,
            api_key=api_key,
            temperature=temperature,
        )

    # Unknown provider fallback
    logger.warning("Unrecognized LLM provider '%s'. Defaulting to Ollama.", provider_type)
    return get_llm_provider("ollama", base_url=base_url)

