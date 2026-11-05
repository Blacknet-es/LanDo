"""
Unit tests for LangGraph Agent Graph and workflow execution.
"""

from datetime import datetime, timezone

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import MemorySaver
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.agent.graph import create_agent_graph
from tests.auth_utils import create_test_user, get_test_user_id


class FakeToolCallingChatModel(BaseChatModel):
    """Mock LLM returning deterministic messages for testing graph workflow."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        last_msg = messages[-1]
        text = last_msg.content if isinstance(last_msg, HumanMessage) else ""

        # If user requests to add event, simulate tool call
        if "reunión" in text.lower():
            msg = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_event",
                        "args": {
                            "title": "Reunión de equipo",
                            "start_time": "2026-11-05T10:00:00Z",
                        },
                        "id": "call_123",
                    }
                ],
            )
        else:
            msg = AIMessage(content=f"Echo: {text}")

        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "fake-tool-caller"


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        create_test_user(session, "agent-graph@example.com")
        yield session
    SQLModel.metadata.drop_all(engine)


class TestAgentGraph:
    def test_graph_simple_reply(self, session: Session):
        fake_llm = FakeToolCallingChatModel()
        cp = MemorySaver()
        graph = create_agent_graph(
            llm=fake_llm,
            session=session,
            user_id=get_test_user_id(session),
            current_datetime=datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc),
            checkpointer=cp,
        )

        res = graph.invoke(
            {"messages": [HumanMessage(content="Hello LanDo!")]},
            config={"configurable": {"thread_id": "thread-1"}},
        )

        assert "messages" in res
        last_message = res["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert "Echo: Hello LanDo!" in last_message.content

    def test_graph_tool_execution(self, session: Session):
        fake_llm = FakeToolCallingChatModel()
        cp = MemorySaver()
        graph = create_agent_graph(
            llm=fake_llm,
            session=session,
            user_id=get_test_user_id(session),
            current_datetime=datetime(2026, 11, 4, 18, 0, tzinfo=timezone.utc),
            checkpointer=cp,
        )

        res = graph.invoke(
            {"messages": [HumanMessage(content="Agendar reunión")]},
            config={"configurable": {"thread_id": "thread-2"}},
        )

        assert len(res["messages"]) >= 3
        # Tools node should have run create_event
        tool_messages = [m for m in res["messages"] if hasattr(m, "tool_call_id")]
        assert len(tool_messages) >= 1
        assert "Reunión de equipo" in str(tool_messages[0].content)
