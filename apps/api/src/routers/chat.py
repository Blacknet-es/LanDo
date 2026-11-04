"""
Chat REST API router for interacting with the LangGraph AI Assistant.
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage

from src.infrastructure.db.session import get_session
from src.domain.settings.repository import SqlModelUserSettingsRepository
from src.infrastructure.llm.factory import get_llm_provider
from src.agent.graph import create_agent_graph

router = APIRouter(prefix="/chat", tags=["chat"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(description="User prompt or instruction for LanDo.")
    thread_id: Optional[str] = Field(
        default=None,
        description="Conversation session ID for memory persistence. If omitted, a new UUID is generated.",
    )
    user_timezone: Optional[str] = Field(
        default="UTC",
        description="User timezone name (e.g. 'Europe/Madrid', 'America/New_York').",
    )


class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    tool_outputs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Structured outputs from any tools executed during this turn.",
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat_with_agent(
    payload: ChatRequest,
    session: Session = Depends(get_session),
) -> ChatResponse:
    """
    Main conversation endpoint with LanDo Agent.
    - Dynamically configures the model from user settings.
    - Runs the LangGraph agent state graph.
    - Returns final assistant reply and executed tool outputs.
    """
    user_message = payload.message.strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be blank.",
        )

    thread_id = payload.thread_id or str(uuid.uuid4())

    # 1. Fetch user LLM settings
    settings_repo = SqlModelUserSettingsRepository(session)
    user_settings = settings_repo.get_settings()

    provider = user_settings.selected_provider
    model_name = user_settings.selected_model
    api_key = (user_settings.api_keys or {}).get(provider)
    base_url = user_settings.ollama_base_url

    # 2. Instantiate BaseChatModel with fallback to local Ollama if keys missing
    llm = get_llm_provider(
        provider_type=provider,
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    # 3. Build agent graph with session tools & current datetime
    graph = create_agent_graph(
        llm=llm,
        session=session,
        current_datetime=datetime.now(timezone.utc),
        user_timezone=payload.user_timezone or "UTC",
    )

    # 4. Invoke graph
    config = {"configurable": {"thread_id": thread_id}}
    input_state = {
        "messages": [HumanMessage(content=user_message)]
    }

    try:
        final_state = graph.invoke(input_state, config=config)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )

    # 5. Extract reply and any tool execution outputs
    messages = final_state.get("messages", [])
    reply = ""
    tool_outputs: List[Dict[str, Any]] = []

    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not reply:
            reply = str(msg.content)
            break

    # If no AIMessage content found (e.g. only tool response), fallback
    if not reply and messages:
        last_msg = messages[-1]
        reply = str(last_msg.content)

    for msg in messages:
        if isinstance(msg, ToolMessage):
            tool_outputs.append({
                "tool_name": getattr(msg, "name", "tool"),
                "output": msg.content,
            })

    return ChatResponse(
        reply=reply,
        thread_id=thread_id,
        tool_outputs=tool_outputs,
    )

