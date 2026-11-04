"""Events REST API router."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.infrastructure.db.session import get_session
from src.infrastructure.db.repositories import SqlModelEventRepository
from src.domain.events.dispatcher import InMemoryDomainEventDispatcher
from src.domain.events.value_objects import (
    EventSource,
    EnergyLevel,
    DopamineReward,
    RecurrenceFrequency,
    TriggerType,
    TriggerCondition,
)
from src.domain.events.exceptions import (
    ImmutableEventException,
    InvalidCognitiveLoadException,
    EventNotFoundException,
)
from src.application.events.create_event import CreateEventUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.application.events.absorb_reminders import AbsorbExternalRemindersUseCase
from src.application.events.dtos import (
    CreateEventCommand,
    RescheduleEventCommand,
    RecurrenceRuleDTO,
    AbsorbExternalRemindersCommand,
)

router = APIRouter(prefix="/events", tags=["events"])

# Singleton in-memory dispatcher for the process
event_dispatcher = InMemoryDomainEventDispatcher()


# ── Schemas ───────────────────────────────────────────────────────────────────


class RecurrenceRuleSchema(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = 1
    until_date: Optional[datetime] = None
    count: Optional[int] = None


class CreateEventRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    is_all_day: bool = False
    source: EventSource = EventSource.LOCAL
    external_id: Optional[str] = None
    typology_id: Optional[str] = None
    trigger_type: TriggerType = TriggerType.TIME_BASED
    location_id: Optional[str] = None
    trigger_condition: Optional[TriggerCondition] = None
    energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY
    cognitive_load: int = Field(default=3, ge=1, le=5)
    dopamine_reward: DopamineReward = DopamineReward.MEDIUM
    recurrence_rule: Optional[RecurrenceRuleSchema] = None
    reminder_minutes: List[int] = Field(default_factory=list)


class RescheduleEventRequest(BaseModel):
    new_start_time: datetime
    new_end_time: Optional[datetime] = None


class EventResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    is_all_day: bool
    source: str
    external_id: Optional[str]
    is_read_only: bool
    typology_id: Optional[str]
    trigger_type: str
    location_id: Optional[str]
    trigger_condition: Optional[str]
    energy_level: str
    cognitive_load: int
    dopamine_reward: str
    created_at: datetime
    updated_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: CreateEventRequest,
    session: Session = Depends(get_session),
) -> EventResponse:
    repo = SqlModelEventRepository(session)
    use_case = CreateEventUseCase(repo, event_dispatcher)

    rec_dto = None
    if payload.recurrence_rule:
        rec_dto = RecurrenceRuleDTO(
            frequency=payload.recurrence_rule.frequency,
            interval=payload.recurrence_rule.interval,
            until_date=payload.recurrence_rule.until_date,
            count=payload.recurrence_rule.count,
        )

    cmd = CreateEventCommand(
        title=payload.title,
        start_time=payload.start_time,
        end_time=payload.end_time,
        description=payload.description,
        is_all_day=payload.is_all_day,
        source=payload.source,
        external_id=payload.external_id,
        typology_id=payload.typology_id,
        trigger_type=payload.trigger_type,
        location_id=payload.location_id,
        trigger_condition=payload.trigger_condition,
        energy_level=payload.energy_level,
        cognitive_load=payload.cognitive_load,
        dopamine_reward=payload.dopamine_reward,
        recurrence_rule=rec_dto,
        reminder_minutes=payload.reminder_minutes,
    )

    try:
        event = use_case.execute(cmd)
    except (InvalidCognitiveLoadException, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_time=event.time_range.start_time,
        end_time=event.time_range.end_time,
        is_all_day=event.is_all_day,
        source=event.source.value,
        external_id=event.external_id,
        is_read_only=event.is_read_only,
        typology_id=event.typology_id,
        trigger_type=event.trigger_type.value,
        location_id=event.location_id,
        trigger_condition=event.trigger_condition.value if event.trigger_condition else None,
        energy_level=event.energy_level.value,
        cognitive_load=event.cognitive_load,
        dopamine_reward=event.dopamine_reward.value,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=List[EventResponse])
def list_events(
    limit: int = 100,
    offset: int = 0,
    session: Session = Depends(get_session),
) -> List[EventResponse]:
    repo = SqlModelEventRepository(session)
    events = repo.find_all(limit=limit, offset=offset)

    return [
        EventResponse(
            id=e.id,
            title=e.title,
            description=e.description,
            start_time=e.time_range.start_time,
            end_time=e.time_range.end_time,
            is_all_day=e.is_all_day,
            source=e.source.value,
            external_id=e.external_id,
            is_read_only=e.is_read_only,
            typology_id=e.typology_id,
            trigger_type=e.trigger_type.value,
            location_id=e.location_id,
            trigger_condition=e.trigger_condition.value if e.trigger_condition else None,
            energy_level=e.energy_level.value,
            cognitive_load=e.cognitive_load,
            dopamine_reward=e.dopamine_reward.value,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in events
    ]


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: str,
    session: Session = Depends(get_session),
) -> EventResponse:
    repo = SqlModelEventRepository(session)
    event = repo.find_by_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event '{event_id}' not found.",
        )
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_time=event.time_range.start_time,
        end_time=event.time_range.end_time,
        is_all_day=event.is_all_day,
        source=event.source.value,
        external_id=event.external_id,
        is_read_only=event.is_read_only,
        typology_id=event.typology_id,
        trigger_type=event.trigger_type.value,
        location_id=event.location_id,
        trigger_condition=event.trigger_condition.value if event.trigger_condition else None,
        energy_level=event.energy_level.value,
        cognitive_load=event.cognitive_load,
        dopamine_reward=event.dopamine_reward.value,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.post("/{event_id}/reschedule", status_code=status.HTTP_200_OK)
def reschedule_event(
    event_id: str,
    payload: RescheduleEventRequest,
    session: Session = Depends(get_session),
) -> dict:
    repo = SqlModelEventRepository(session)
    use_case = RescheduleEventUseCase(repo, event_dispatcher)

    cmd = RescheduleEventCommand(
        event_id=event_id,
        new_start_time=payload.new_start_time,
        new_end_time=payload.new_end_time,
    )
    try:
        use_case.execute(cmd)
    except ImmutableEventException as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )
    except EventNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return {"status": "success", "message": "Event rescheduled successfully"}

