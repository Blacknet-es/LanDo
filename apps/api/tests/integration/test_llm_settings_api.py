"""
Integration tests for /api/settings/llm endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from src.main import app
from src.infrastructure.db.session import get_session


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestLLMSettingsApi:
    def test_get_default_llm_settings(self, client: TestClient):
        response = client.get("/api/v1/settings/llm")
        assert response.status_code == 200
        data = response.json()
        assert data["selected_provider"] == "ollama"
        assert data["selected_model"] == "qwen2.5:7b"
        assert "ollama" in data["available_providers"]
        assert "google" in data["available_providers"]
        assert "anthropic" in data["available_providers"]
        assert "openai" in data["available_providers"]
        assert "qwen2.5:7b" in data["provider_presets"]["ollama"]

    def test_update_llm_settings(self, client: TestClient):
        payload = {
            "selected_provider": "google",
            "selected_model": "gemini-1.5-pro",
            "api_keys": {
                "google": "test-gemini-key-12345",
            },
            "ollama_base_url": "http://localhost:11434",
        }
        put_res = client.put("/api/v1/settings/llm", json=payload)
        assert put_res.status_code == 200
        put_data = put_res.json()
        assert put_data["selected_provider"] == "google"
        assert put_data["selected_model"] == "gemini-1.5-pro"
        assert put_data["ollama_base_url"] == "http://localhost:11434"
        # Key masked as boolean flag (True)
        assert put_data["configured_api_keys"]["google"] is True

        # Verify persistence with GET
        get_res = client.get("/api/v1/settings/llm")
        assert get_res.status_code == 200
        assert get_res.json()["selected_provider"] == "google"
        assert get_res.json()["configured_api_keys"]["google"] is True

    def test_list_ollama_models_success(self, client: TestClient):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5:7b", "size": 4700000000, "modified_at": "2026-11-01"},
                {"name": "llama3.2:latest", "size": 2000000000, "modified_at": "2026-11-02"},
            ]
        }

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            response = client.get("/api/v1/settings/llm/ollama-models")
            assert response.status_code == 200
            data = response.json()
            assert len(data["models"]) == 2
            assert data["models"][0]["name"] == "qwen2.5:7b"
            assert data["models"][1]["name"] == "llama3.2:latest"

    def test_list_ollama_models_service_unavailable(self, client: TestClient):
        import httpx

        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            response = client.get("/api/v1/settings/llm/ollama-models")
            assert response.status_code == 503
            assert "Unable to reach local Ollama" in response.json()["detail"]
