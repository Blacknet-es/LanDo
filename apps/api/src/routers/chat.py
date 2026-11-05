from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from sqlmodel import Session
from typing_extensions import Optional, Literal
from datetime import datetime
from langchain_core.messages import SystemMessage
from src.agent.tools.locations import get_location_tools
from src.application.events.create_event import CreateEventUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.application.events.repository import EventRepository
from src.application.events.exceptions import ImmutableEventException

router = APIRouter()

@router.post("/api/chat")
async def chat(
    message: str,
    thread_id: Optional[str] = None,
    llm: BaseChatModel = Depends(get_llm_provider),
    session: Session = Depends(get_session),
    current_datetime: Optional[datetime] = None,
    user_timezone: str = "UTC",
    checkpointer: Optional[MemorySaver] = None,
):
    """
    Endpoint to handle chat requests.
    """
    tools = get_event_tools(session) + get_location_tools(session)
    llm_with_tools = llm.bind_tools(tools)
    tool_node = ToolNode(tools)

    system_prompt = build_system_prompt(
        current_datetime=current_datetime,
        user_timezone=user_timezone,
    )

    def agent_node(state: AgentState):
        messages = list(state["messages"])
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_prompt)] + messages
        elif isinstance(messages[0], SystemMessage):
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
    graph = workflow.compile(checkpointer=cp)

    state = {"messages": [BaseMessage(content=message)]}
    result = graph.run(state)

    reply = result["messages"][0].content
    tool_outputs = []

    return JSONResponse(
        content={
            "reply": reply,
            "thread_id": thread_id,
            "tool_outputs": tool_outputs,
        }
    )
