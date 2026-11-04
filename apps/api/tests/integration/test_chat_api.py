"""
Integration tests for /api/chat endpoint.
"""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.language_models.chat_models import BaseChatModel

from src.main import app
from src.infrastructure.db.session import get_session


class MockChatModel(BaseChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content="¡Hola! Soy LanDo, ¿en qué te puedo ayudar hoy?")
                )
            ]
        )

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "mock-chat-model"


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


class TestChatApi:
    def test_chat_endpoint_success(self, client: TestClient):
        with patch("src.routers.chat.get_llm_provider", return_value=MockChatModel()):
            payload = {
                "message": "Hola LanDo",
                "thread_id": "test-session-123",
                "user_timezone": "Europe/Madrid",
            }
            response = client.post("/api/chat", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "¡Hola! Soy LanDo" in data["reply"]
            assert data["thread_id"] == "test-session-123"
            assert isinstance(data["tool_outputs"], list)

    def test_chat_endpoint_validation_empty_message(self, client: TestClient):
        response = client.post("/api/chat", json={"message": "   "})
        assert response.status_code == 422

