"""
Integration tests for /api/chat endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.application.chat.send_message import ChatResponse, SendChatMessage, SendChatMessageUseCase
from src.infrastructure.db.session import get_session
from src.main import app
from src.presentation.http.dependencies import get_send_chat_message_use_case
from tests.auth_utils import authenticated_client, create_test_user, get_test_user_id


class MockChatAgent:
    def invoke(self, command: SendChatMessage, thread_id: str) -> ChatResponse:
        return ChatResponse(
            reply="¡Hola! Soy LanDo, ¿en qué te puedo ayudar hoy?",
            thread_id=thread_id,
            tool_outputs=[],
        )


def test_chat_uses_supported_accept_language(
    client: TestClient,
) -> None:
    captured: dict[str, str] = {}

    class LanguageAgent:
        def invoke(self, command: SendChatMessage, thread_id: str) -> ChatResponse:
            captured["language"] = command.language
            return ChatResponse(reply="Hello", thread_id=thread_id, tool_outputs=[])

    client.app.dependency_overrides[get_send_chat_message_use_case] = lambda: (
        SendChatMessageUseCase(LanguageAgent())
    )
    response = client.post(
        "/api/v1/chat",
        json={"message": "Hello"},
        headers={"Accept-Language": "en-GB,en;q=0.9,es;q=0.8"},
    )

    assert response.status_code == 200
    assert captured["language"] == "en"


def _mock_use_case() -> SendChatMessageUseCase:
    return SendChatMessageUseCase(MockChatAgent())


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        create_test_user(session)
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = authenticated_client(session)
    yield client
    app.dependency_overrides.clear()


class TestChatApi:
    def test_chat_endpoint_success(self, client: TestClient):
        client.app.dependency_overrides[get_send_chat_message_use_case] = _mock_use_case
        payload = {
            "message": "Hola LanDo",
            "thread_id": "test-session-123",
            "user_timezone": "Europe/Madrid",
        }
        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "¡Hola! Soy LanDo" in data["reply"]
        assert data["thread_id"] == "test-session-123"
        assert isinstance(data["tool_outputs"], list)

    def test_chat_endpoint_validation_empty_message(self, client: TestClient):
        response = client.post("/api/v1/chat", json={"message": "   "})
        assert response.status_code == 422

    def test_chat_accepts_shared_client_payload(self, client: TestClient):
        client.app.dependency_overrides[get_send_chat_message_use_case] = _mock_use_case
        response = client.post(
            "/api/v1/chat",
            json={"content": "Hola", "conversationId": "shared-client-thread"},
        )
        assert response.status_code == 200
        assert response.json()["thread_id"] == "shared-client-thread"

    def test_chat_checkpoint_id_is_namespaced_by_user(
        self,
        client: TestClient,
        session: Session,
        monkeypatch: pytest.MonkeyPatch,
    ):
        captured: dict = {}

        from langchain_core.messages import AIMessage

        class FakeGraph:
            def invoke(self, _state, config):
                captured.update(config["configurable"])
                return {"messages": [AIMessage(content="isolated reply")]}

        def fake_create_agent_graph(**kwargs):
            assert kwargs["user_id"] == get_test_user_id(session)
            return FakeGraph()

        monkeypatch.setattr(
            "src.infrastructure.agent.chat_runner.create_agent_graph", fake_create_agent_graph
        )
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "thread_id": "client-thread"},
        )

        assert response.status_code == 200
        assert response.json()["thread_id"] == "client-thread"
        assert captured["thread_id"] == f"{get_test_user_id(session)}:client-thread"
