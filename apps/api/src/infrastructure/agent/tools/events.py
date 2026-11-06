from datetime import datetime
from typing import Any
from uuid import UUID

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.application.events.create_event import CreateEventUseCase
from src.application.events.dtos import (
    CreateEventCommand,
    RescheduleEventCommand,
)
from src.application.events.repository import EventRepository
from src.application.events.reschedule_event import RescheduleEventUseCase
from src.domain.events.entities import Event
from src.domain.events.exceptions import (
    EventNotFoundException,
    ImmutableEventException,
    InvalidCognitiveLoadException,
)
from src.domain.events.value_objects import (
    DopamineReward,
    EnergyLevel,
    EventSource,
    TriggerCondition,
    TriggerType,
)
from src.infrastructure.db.location_repository import SqlModelLocationRepository
from src.infrastructure.db.repositories import SqlModelEventRepository
from src.infrastructure.events.dispatcher import SqlModelDomainEventDispatcher


class CreateEventInput(BaseModel):
    title: str = Field(description="Short title for the event")
    start_time: datetime = Field(description="Event start time in ISO 8601 format")
    end_time: datetime | None = None
    description: str | None = None
    is_all_day: bool = False
    energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY
    cognitive_load: int = Field(default=3, ge=1, le=5)
    dopamine_reward: DopamineReward = DopamineReward.MEDIUM
    reminder_minutes: list[int] = Field(default_factory=list)
    trigger_type: str = "TIME_BASED"
    location_id: str | None = None
    location_name: str | None = None
    trigger_condition: str | None = None


class GetEventsInput(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None


class RescheduleEventInput(BaseModel):
    event_id: str
    new_start_time: datetime
    new_end_time: datetime | None = None


def _event_data(event: Event) -> dict[str, Any]:
    return {
        "event_id": event.id,
        "title": event.title,
        "description": event.description,
        "start_time": event.time_range.start_time.isoformat(),
        "end_time": (event.time_range.end_time.isoformat() if event.time_range.end_time else None),
        "energy_level": event.energy_level.value,
        "cognitive_load": event.cognitive_load,
        "trigger_type": event.trigger_type.value,
        "location_id": event.location_id,
    }


def _trigger_values(
    trigger_type: str,
    trigger_condition: str | None,
) -> tuple[TriggerType, TriggerCondition | None]:
    value = trigger_type.strip().upper()
    condition = trigger_condition.strip().upper() if trigger_condition else None

    if value == "LOCATION":
        value = "LOCATION_EXIT" if condition in {"EXIT", "ON_EXIT"} else "LOCATION_ENTER"
    if value not in TriggerType.__members__:
        raise ValueError(f"Unknown trigger type '{trigger_type}'.")
    parsed_type = TriggerType[value]

    if parsed_type == TriggerType.TIME_BASED:
        return parsed_type, None
    if condition is None:
        condition = "ON_EXIT" if parsed_type == TriggerType.LOCATION_EXIT else "ON_ENTER"
    elif condition == "ENTER":
        condition = "ON_ENTER"
    elif condition == "EXIT":
        condition = "ON_EXIT"
    if condition not in TriggerCondition.__members__:
        raise ValueError(f"Unknown trigger condition '{trigger_condition}'.")
    return parsed_type, TriggerCondition[condition]


def get_event_tools(session: Session, user_id: UUID) -> list[StructuredTool]:
    repository: EventRepository = SqlModelEventRepository(session, user_id)
    dispatcher = SqlModelDomainEventDispatcher(session, user_id)
    location_repository = SqlModelLocationRepository(session, user_id)

    def create_event(
        title: str,
        start_time: datetime,
        end_time: datetime | None = None,
        description: str | None = None,
        is_all_day: bool = False,
        energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY,
        cognitive_load: int = 3,
        dopamine_reward: DopamineReward = DopamineReward.MEDIUM,
        reminder_minutes: list[int] | None = None,
        trigger_type: str = "TIME_BASED",
        location_id: str | None = None,
        location_name: str | None = None,
        trigger_condition: str | None = None,
    ) -> dict[str, Any]:
        """Create an event or a location-based reminder."""
        try:
            parsed_trigger, parsed_condition = _trigger_values(trigger_type, trigger_condition)
            if parsed_trigger != TriggerType.TIME_BASED:
                location = (
                    location_repository.find_by_id(location_id)
                    if location_id
                    else location_repository.find_by_name(location_name)
                    if location_name
                    else None
                )
                if location is None:
                    return {
                        "error": (
                            f"Location '{location_name or location_id or ''}' not found "
                            "in saved places. Save the location first."
                        )
                    }
                location_id = location.id

            command = CreateEventCommand(
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                is_all_day=is_all_day,
                source=EventSource.LOCAL,
                trigger_type=parsed_trigger,
                location_id=location_id,
                trigger_condition=parsed_condition,
                energy_level=energy_level,
                cognitive_load=cognitive_load,
                dopamine_reward=dopamine_reward,
                reminder_minutes=reminder_minutes or [],
            )
            event = CreateEventUseCase(repository, dispatcher).execute(command)
            return {"status": "success", **_event_data(event)}
        except (InvalidCognitiveLoadException, ValueError) as exc:
            return {"error": str(exc)}

    def get_events(
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """List events, optionally filtered by an inclusive date range."""
        events = repository.find_by_date_range(start_date, end_date)
        return {
            "count": len(events),
            "events": [_event_data(event) for event in events],
        }

    def reschedule_event(
        event_id: str,
        new_start_time: datetime,
        new_end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Move an existing event to a new time."""
        try:
            RescheduleEventUseCase(repository, dispatcher).execute(
                RescheduleEventCommand(
                    event_id=event_id,
                    new_start_time=new_start_time,
                    new_end_time=new_end_time,
                )
            )
            return {"status": "success", "event_id": event_id}
        except ImmutableEventException as exc:
            return {"error": f"Event cannot be modified because it is read-only. {exc}"}
        except (EventNotFoundException, ValueError) as exc:
            return {"error": str(exc)}

    return [
        StructuredTool.from_function(
            func=create_event,
            name="create_event",
            description="Create an event or a location-triggered reminder.",
            args_schema=CreateEventInput,
        ),
        StructuredTool.from_function(
            func=get_events,
            name="get_events",
            description="List events, optionally filtered by start and end date.",
            args_schema=GetEventsInput,
        ),
        StructuredTool.from_function(
            func=reschedule_event,
            name="reschedule_event",
            description="Reschedule an existing event.",
            args_schema=RescheduleEventInput,
        ),
    ]
