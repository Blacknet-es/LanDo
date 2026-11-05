import logging
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session

from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.application.events.dtos import AbsorbExternalRemindersCommand
from src.config import settings
from src.domain.events.dispatcher import InMemoryDomainEventDispatcher
from src.domain.events.exceptions import EventNotFoundException
from src.domain.events.value_objects import TriggerType
from src.infrastructure.db.repositories import SqlModelEventRepository
from src.infrastructure.db.session import get_session

router = APIRouter()
event_dispatcher = InMemoryDomainEventDispatcher()
logger = logging.getLogger(__name__)


def verify_webhook_secret(
    lando_secret: str | None = Header(default=None, alias="X-LanDo-Webhook-Secret"),
    legacy_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> None:
    configured_secret = settings.webhook_secret
    if not configured_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret is not configured",
        )
    provided_secret = lando_secret if lando_secret is not None else legacy_secret
    if provided_secret is None or not secrets.compare_digest(
        provided_secret.encode("utf-8"), configured_secret.encode("utf-8")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret",
        )


class LocationTriggerRequest(BaseModel):
    user_id: str = Field(min_length=1)
    location_id: str = Field(min_length=1)
    trigger_type: TriggerType

    @field_validator("user_id", "location_id")
    @classmethod
    def identifiers_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identifier must not be blank")
        return normalized


class ExternalEventRequest(BaseModel):
    event_id: str = Field(min_length=1)
    reminder_minutes: list[int] = Field(default_factory=list)


def _process_location_trigger(payload: LocationTriggerRequest) -> dict[str, str]:
    return {"message": "Location trigger received"}


@router.post("/location-trigger")
async def location_trigger(
    payload: LocationTriggerRequest,
    _: None = Depends(verify_webhook_secret),
) -> dict:
    try:
        return _process_location_trigger(payload)
    except Exception as exc:
        logger.exception(
            "Failed to process location trigger for user %s and location %s",
            payload.user_id,
            payload.location_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Failed to process location trigger",
                "error": str(exc),
            },
        ) from exc


@router.post("/external-event")
async def external_event(
    event_data: ExternalEventRequest,
    session: Session = Depends(get_session),
    _: None = Depends(verify_webhook_secret),
) -> dict:
    use_case = AbsorbExternalRemindersUseCase(
        repository=SqlModelEventRepository(session),
        dispatcher=event_dispatcher,
    )
    command = AbsorbExternalRemindersCommand(
        event_id=event_data.event_id,
        reminder_minutes=event_data.reminder_minutes,
    )
    try:
        use_case.execute(command)
    except EventNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return {"message": "External event absorbed"}
