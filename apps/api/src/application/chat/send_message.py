from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SendChatMessage:
    user_id: UUID
    message: str
    thread_id: str | None = None
    current_datetime: datetime | None = None
    user_timezone: str = "UTC"
    language: str = "es"


@dataclass(frozen=True)
class ChatResponse:
    reply: Any
    thread_id: str
    tool_outputs: list[Any]


class ChatAgent(Protocol):
    def invoke(self, command: SendChatMessage, thread_id: str) -> ChatResponse: ...


class SendChatMessageUseCase:
    def __init__(self, agent: ChatAgent) -> None:
        self.agent = agent

    def execute(self, command: SendChatMessage) -> ChatResponse:
        thread_id = command.thread_id or str(uuid4())
        response = self.agent.invoke(command, thread_id)
        return ChatResponse(
            reply=response.reply,
            thread_id=thread_id,
            tool_outputs=response.tool_outputs,
        )
