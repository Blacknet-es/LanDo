from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from sqlmodel import Session

from src.application.chat.send_message import SendChatMessageUseCase
from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.application.events.create_event import CreateEventUseCase
from src.application.events.query_events import GetEventUseCase, ListEventsUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.application.locations.use_cases import (
    CreateUserLocationUseCase,
    ListUserLocationsUseCase,
)
from src.application.settings.list_ollama_models import ListOllamaModelsUseCase
from src.application.settings.manage_user_settings import (
    GetUserSettingsUseCase,
    UpdateUserSettingsUseCase,
)
from src.application.users.use_cases import (
    LoginUserUseCase,
    RegisterUserUseCase,
    UpdateUserLanguageUseCase,
)
from src.application.webhooks.process_location_trigger import ProcessLocationTriggerUseCase
from src.domain.users.models import User
from src.infrastructure.agent.chat_runner import LangGraphChatRunner
from src.infrastructure.db.location_repository import SqlModelLocationRepository
from src.infrastructure.db.location_trigger_repository import (
    SqlModelLocationTriggerRepository,
)
from src.infrastructure.db.repositories import SqlModelEventRepository
from src.infrastructure.db.session import get_session
from src.infrastructure.db.settings_repository import SqlModelUserSettingsRepository
from src.infrastructure.db.user_repository import SqlModelUserRepository
from src.infrastructure.events.dispatcher import SqlModelDomainEventDispatcher
from src.infrastructure.llm.ollama_catalog import HttpxOllamaModelCatalog
from src.security.auth import JwtAccessTokenIssuer, PwdlibPasswordHasher, get_current_user


def get_register_user_use_case(
    session: Session = Depends(get_session),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(SqlModelUserRepository(session), PwdlibPasswordHasher())


def get_login_user_use_case(session: Session = Depends(get_session)) -> LoginUserUseCase:
    return LoginUserUseCase(
        SqlModelUserRepository(session),
        PwdlibPasswordHasher(),
        JwtAccessTokenIssuer(),
    )


def get_event_repository(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SqlModelEventRepository:
    return SqlModelEventRepository(session, current_user.id)


def create_webhook_event_repository(session: Session, user_id: UUID) -> SqlModelEventRepository:
    return SqlModelEventRepository(session, user_id)


def get_create_event_use_case(
    repository: SqlModelEventRepository = Depends(get_event_repository),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CreateEventUseCase:
    return CreateEventUseCase(
        repository,
        SqlModelDomainEventDispatcher(session, current_user.id),
    )


def get_reschedule_event_use_case(
    repository: SqlModelEventRepository = Depends(get_event_repository),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> RescheduleEventUseCase:
    return RescheduleEventUseCase(
        repository,
        SqlModelDomainEventDispatcher(session, current_user.id),
    )


def get_list_events_use_case(
    repository: SqlModelEventRepository = Depends(get_event_repository),
) -> ListEventsUseCase:
    return ListEventsUseCase(repository)


def get_get_event_use_case(
    repository: SqlModelEventRepository = Depends(get_event_repository),
) -> GetEventUseCase:
    return GetEventUseCase(repository)


def get_location_repository(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SqlModelLocationRepository:
    return SqlModelLocationRepository(session, current_user.id)


def get_create_location_use_case(
    repository: SqlModelLocationRepository = Depends(get_location_repository),
    current_user: User = Depends(get_current_user),
) -> CreateUserLocationUseCase:
    return CreateUserLocationUseCase(repository, current_user.id)


def get_list_locations_use_case(
    repository: SqlModelLocationRepository = Depends(get_location_repository),
) -> ListUserLocationsUseCase:
    return ListUserLocationsUseCase(repository)


def get_user_settings_repository(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SqlModelUserSettingsRepository:
    return SqlModelUserSettingsRepository(session, current_user.id)


def get_user_settings_use_case(
    repository: SqlModelUserSettingsRepository = Depends(get_user_settings_repository),
) -> GetUserSettingsUseCase:
    return GetUserSettingsUseCase(repository)


def get_update_user_settings_use_case(
    repository: SqlModelUserSettingsRepository = Depends(get_user_settings_repository),
) -> UpdateUserSettingsUseCase:
    return UpdateUserSettingsUseCase(repository)


def get_update_user_language_use_case(
    session: Session = Depends(get_session),
) -> UpdateUserLanguageUseCase:
    return UpdateUserLanguageUseCase(SqlModelUserRepository(session))


def get_absorb_external_reminders_use_case_factory(
    session: Session = Depends(get_session),
) -> Callable[[UUID], AbsorbExternalRemindersUseCase]:
    return lambda user_id: AbsorbExternalRemindersUseCase(
        SqlModelEventRepository(session, user_id),
        SqlModelDomainEventDispatcher(session, user_id),
    )


def get_list_ollama_models_use_case(
    repository: SqlModelUserSettingsRepository = Depends(get_user_settings_repository),
) -> ListOllamaModelsUseCase:
    return ListOllamaModelsUseCase(repository, HttpxOllamaModelCatalog())


def get_location_trigger_use_case(
    session: Session = Depends(get_session),
) -> ProcessLocationTriggerUseCase:
    return ProcessLocationTriggerUseCase(SqlModelLocationTriggerRepository(session))


def get_send_chat_message_use_case(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> SendChatMessageUseCase:
    settings_repository = SqlModelUserSettingsRepository(session, current_user.id)
    return SendChatMessageUseCase(LangGraphChatRunner(session, settings_repository))
