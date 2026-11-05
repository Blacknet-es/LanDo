from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from sqlmodel import Session

from src.agent.graph import create_agent_graph
from src.domain.settings.repository import SqlModelUserSettingsRepository
from src.infrastructure.db.session import get_session
from src.infrastructure.llm.factory import get_llm_provider as create_llm_provider

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(
        validation_alias=AliasChoices("message", "content"),
        min_length=1,
    )
    thread_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("thread_id", "conversationId"),
    )
    current_datetime: datetime | None = None
    user_timezone: str = "UTC"

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("message must not be blank")
        return message


def get_llm_provider(session: Session = Depends(get_session)) -> BaseChatModel:
    settings = SqlModelUserSettingsRepository(session).get_settings()
    provider = settings.selected_provider
    return create_llm_provider(
        provider_type=provider,
        model_name=settings.selected_model,
        api_key=(settings.api_keys or {}).get(provider),
        base_url=settings.ollama_base_url,
    )


@router.post("")
def chat(
    payload: ChatRequest,
    llm: BaseChatModel = Depends(get_llm_provider),
    session: Session = Depends(get_session),
) -> dict:
    thread_id = payload.thread_id or str(uuid4())
    graph = create_agent_graph(
        llm=llm,
        session=session,
        current_datetime=payload.current_datetime,
        user_timezone=payload.user_timezone,
    )
    result = graph.invoke(
        {"messages": [HumanMessage(content=payload.message)]},
        config={"configurable": {"thread_id": thread_id}},
    )

    reply = result["messages"][-1].content
    tool_outputs = [
        message.content for message in result["messages"] if isinstance(message, ToolMessage)
    ]
    return {
        "reply": reply,
        "thread_id": thread_id,
        "tool_outputs": tool_outputs,
    }
