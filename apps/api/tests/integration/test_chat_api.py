"""
Integration tests for /api/chat endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.infrastructure.db.session import get_session
from src.main import app
from src.routers.chat import get_llm_provider
from tests.auth_utils import authenticated_client, create_test_user, get_test_user_id


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
        client.app.dependency_overrides[get_llm_provider] = lambda: MockChatModel()
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
        client.app.dependency_overrides[get_llm_provider] = lambda: MockChatModel()
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

        class FakeGraph:
            def invoke(self, _state, config):
                captured.update(config["configurable"])
                return {"messages": [AIMessage(content="isolated reply")]}

        def fake_create_agent_graph(**kwargs):
            assert kwargs["user_id"] == get_test_user_id(session)
            return FakeGraph()

        monkeypatch.setattr("src.routers.chat.create_agent_graph", fake_create_agent_graph)
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello", "thread_id": "client-thread"},
        )

        assert response.status_code == 200
        assert response.json()["thread_id"] == "client-thread"
        assert captured["thread_id"] == f"{get_test_user_id(session)}:client-thread"
