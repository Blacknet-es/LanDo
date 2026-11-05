from typing import Annotated, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from sqlmodel import Session

from src.agent.tools.events import get_event_tools
from src.agent.tools.locations import get_location_tools
from src.agent.prompts import build_system_prompt
from src.application.events.create_event import CreateEventUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.application.events.repository import EventRepository
from src.application.events.exceptions import ImmutableEventException

# ── State Definition ──────────────────────────────────────────────────────────


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# Global in-memory checkpointer for thread session state persistence
global_memory_checkpointer = MemorySaver()


# ── Graph Builder ─────────────────────────────────────────────────────────────


def create_agent_graph(
    llm: BaseChatModel,
    session: Session,
    current_datetime: Optional[datetime] = None,
    user_timezone: str = "UTC",
    checkpointer: Optional[MemorySaver] = None,
):
    """
    Builds and compiles a LangGraph stateful agent workflow.

    Workflow:
    [agent node] -> (has tool calls?)
       ├── Yes -> [tools node] -> [agent node]
       └── No  -> END
    """
    tools = get_event_tools(session) + get_location_tools(session)
    # Bind tools to the model
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    system_prompt = build_system_prompt(
        current_datetime=current_datetime,
        user_timezone=user_timezone,
    )

    def agent_node(state: AgentState):
        messages = list(state["messages"])
        # Ensure system prompt is present as the first message
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + messages
        elif isinstance(messages[0], SystemMessage):
            # Update with current dynamic timestamp
            messages[0] = SystemMessage(content=system_prompt)

        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "__end__"

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "__end__": END,
        },
    )
    workflow.add_edge("tools", "agent")

    cp = checkpointer if checkpointer is not None else global_memory_checkpointer
    return workflow.compile(checkpointer=cp)
