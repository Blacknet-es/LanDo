import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.application.events.dtos import AbsorbExternalRemindersCommand
from src.config import settings
from src.domain.events.dispatcher import InMemoryDomainEventDispatcher
from src.domain.events.exceptions import EventNotFoundException
from src.domain.events.value_objects import TriggerType
from src.domain.locations.models import UserLocation
from src.domain.users.models import User
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
    user_id: UUID
    location_id: str = Field(min_length=1)
    trigger_type: TriggerType

    @field_validator("location_id")
    @classmethod
    def identifiers_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Identifier must not be blank")
        return normalized


class ExternalEventRequest(BaseModel):
    user_id: UUID
    event_id: str = Field(min_length=1)
    reminder_minutes: list[int] = Field(default_factory=list)


def _process_location_trigger(
    payload: LocationTriggerRequest,
    session: Session,
) -> dict[str, str]:
    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    location = session.exec(
        select(UserLocation).where(
            UserLocation.id == payload.location_id,
            UserLocation.user_id == payload.user_id,
        )
    ).first()
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")

    return {"message": "Location trigger received"}


@router.post("/location-trigger")
async def location_trigger(
    payload: LocationTriggerRequest,
    _: None = Depends(verify_webhook_secret),
    session: Session = Depends(get_session),
) -> dict:
    try:
        return _process_location_trigger(payload, session)
    except HTTPException:
        raise
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
        repository=SqlModelEventRepository(session, event_data.user_id),
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
