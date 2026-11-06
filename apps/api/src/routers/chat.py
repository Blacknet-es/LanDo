from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from src.application.chat.send_message import SendChatMessage, SendChatMessageUseCase
from src.domain.users.models import User
from src.presentation.http.dependencies import get_send_chat_message_use_case
from src.presentation.http.language import get_request_language
from src.security.auth import get_current_user

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


@router.post("")
def chat(
    payload: ChatRequest,
    use_case: SendChatMessageUseCase = Depends(get_send_chat_message_use_case),
    current_user: User = Depends(get_current_user),
    language: str = Depends(get_request_language),
) -> dict:
    response = use_case.execute(
        SendChatMessage(
            user_id=current_user.id,
            message=payload.message,
            thread_id=payload.thread_id,
            current_datetime=payload.current_datetime,
            user_timezone=payload.user_timezone,
            language=language,
        )
    )
    return {
        "reply": response.reply,
        "thread_id": response.thread_id,
        "tool_outputs": response.tool_outputs,
    }
