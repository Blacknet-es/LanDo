"""
Tests for LLM Provider Factory and Fallback logic.
"""

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from src.infrastructure.llm.factory import get_llm_provider, DEFAULT_OLLAMA_MODEL


class TestLLMProviderFactory:
    def test_ollama_provider_returns_chat_ollama(self):
        llm = get_llm_provider("ollama", model_name="qwen2.5:7b")
        assert isinstance(llm, ChatOllama)
        assert llm.model == "qwen2.5:7b"

    def test_google_provider_with_key_returns_chat_google(self):
        llm = get_llm_provider(
            "google",
            model_name="gemini-1.5-flash",
            api_key="mock-gemini-key",
        )
        assert isinstance(llm, ChatGoogleGenerativeAI)
        assert llm.model == "gemini-1.5-flash"

    def test_google_provider_without_key_falls_back_to_ollama(self):
        llm = get_llm_provider("google", api_key=None)
        assert isinstance(llm, ChatOllama)
        assert llm.model == DEFAULT_OLLAMA_MODEL

    def test_anthropic_provider_with_key_returns_chat_anthropic(self):
        llm = get_llm_provider(
            "anthropic",
            model_name="claude-3-5-sonnet-20241022",
            api_key="mock-anthropic-key",
        )
        assert isinstance(llm, ChatAnthropic)
        assert llm.model == "claude-3-5-sonnet-20241022"

    def test_anthropic_provider_without_key_falls_back_to_ollama(self):
        llm = get_llm_provider("anthropic", api_key="")
        assert isinstance(llm, ChatOllama)
        assert llm.model == DEFAULT_OLLAMA_MODEL

    def test_openai_provider_with_key_returns_chat_openai(self):
        llm = get_llm_provider(
            "openai",
            model_name="gpt-4o-mini",
            api_key="mock-openai-key",
        )
        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-4o-mini"

    def test_openai_provider_without_key_falls_back_to_ollama(self):
        llm = get_llm_provider("openai", api_key=None)
        assert isinstance(llm, ChatOllama)
        assert llm.model == DEFAULT_OLLAMA_MODEL

    def test_unknown_provider_defaults_to_ollama(self):
        llm = get_llm_provider("unknown_provider")
        assert isinstance(llm, ChatOllama)
        assert llm.model == DEFAULT_OLLAMA_MODEL

