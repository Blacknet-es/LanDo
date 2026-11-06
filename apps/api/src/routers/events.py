"""Events REST API router."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.events.create_event import CreateEventUseCase
from src.application.events.dtos import (
    CreateEventCommand,
    RecurrenceRuleDTO,
    RescheduleEventCommand,
)
from src.application.events.query_events import GetEventUseCase, ListEventsUseCase
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.domain.events.exceptions import (
    EventNotFoundException,
    ImmutableEventException,
    InvalidCognitiveLoadException,
)
from src.domain.events.value_objects import (
    DopamineReward,
    EnergyLevel,
    EventSource,
    RecurrenceFrequency,
    TriggerCondition,
    TriggerType,
)
from src.presentation.http.dependencies import (
    get_create_event_use_case,
    get_get_event_use_case,
    get_list_events_use_case,
    get_reschedule_event_use_case,
)

router = APIRouter(prefix="/events", tags=["events"])

# ── Schemas ───────────────────────────────────────────────────────────────────


class RecurrenceRuleSchema(BaseModel):
    frequency: RecurrenceFrequency
    interval: int = 1
    until_date: datetime | None = None
    count: int | None = None


class CreateEventRequest(BaseModel):
    title: str
    start_time: datetime
    end_time: datetime | None = None
    description: str | None = None
    is_all_day: bool = False
    source: EventSource = EventSource.LOCAL
    external_id: str | None = None
    typology_id: str | None = None
    trigger_type: TriggerType = TriggerType.TIME_BASED
    location_id: str | None = None
    trigger_condition: TriggerCondition | None = None
    energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY
    cognitive_load: int = Field(default=3, ge=1, le=5)
    dopamine_reward: DopamineReward = DopamineReward.MEDIUM
    recurrence_rule: RecurrenceRuleSchema | None = None
    reminder_minutes: list[int] = Field(default_factory=list)


class RescheduleEventRequest(BaseModel):
    new_start_time: datetime
    new_end_time: datetime | None = None


class EventResponse(BaseModel):
    id: str
    title: str
    description: str | None
    start_time: datetime
    end_time: datetime | None
    is_all_day: bool
    source: str
    external_id: str | None
    is_read_only: bool
    typology_id: str | None
    trigger_type: str
    location_id: str | None
    trigger_condition: str | None
    energy_level: str
    cognitive_load: int
    dopamine_reward: str
    created_at: datetime
    updated_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: CreateEventRequest,
    use_case: CreateEventUseCase = Depends(get_create_event_use_case),
) -> EventResponse:
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


@router.get("", response_model=list[EventResponse])
def list_events(
    limit: int = 100,
    offset: int = 0,
    use_case: ListEventsUseCase = Depends(get_list_events_use_case),
) -> list[EventResponse]:
    events = use_case.execute(limit=limit, offset=offset)

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
    use_case: GetEventUseCase = Depends(get_get_event_use_case),
) -> EventResponse:
    event = use_case.execute(event_id)
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
    use_case: RescheduleEventUseCase = Depends(get_reschedule_event_use_case),
) -> dict:
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
