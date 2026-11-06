from langchain_core.messages import HumanMessage, ToolMessage
from sqlmodel import Session

from src.application.chat.send_message import ChatResponse, SendChatMessage
from src.domain.settings.repository import UserSettingsRepository
from src.infrastructure.agent.graph import create_agent_graph
from src.infrastructure.llm.factory import get_llm_provider


class LangGraphChatRunner:
    def __init__(
        self,
        session: Session,
        settings_repository: UserSettingsRepository,
    ) -> None:
        self.session = session
        self.settings_repository = settings_repository

    def invoke(self, command: SendChatMessage, thread_id: str) -> ChatResponse:
        settings = self.settings_repository.get_settings()
        provider = settings.selected_provider
        llm = get_llm_provider(
            provider_type=provider,
            model_name=settings.selected_model,
            api_key=(settings.api_keys or {}).get(provider),
            base_url=settings.ollama_base_url,
        )
        graph = create_agent_graph(
            llm=llm,
            session=self.session,
            user_id=command.user_id,
            current_datetime=command.current_datetime,
            user_timezone=command.user_timezone,
            language=command.language,
        )
        result = graph.invoke(
            {"messages": [HumanMessage(content=command.message)]},
            config={"configurable": {"thread_id": f"{command.user_id}:{thread_id}"}},
        )
        messages = result["messages"]
        return ChatResponse(
            reply=messages[-1].content,
            thread_id=thread_id,
            tool_outputs=[
                message.content for message in messages if isinstance(message, ToolMessage)
            ],
        )
