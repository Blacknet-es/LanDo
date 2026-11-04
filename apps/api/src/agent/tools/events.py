"""
LangChain structured tools for managing calendar events and tasks in LanDo.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from sqlmodel import Session

from src.infrastructure.db.repositories import SqlModelEventRepository
from src.domain.locations.repository import SqlModelLocationRepository
from src.domain.events.dispatcher import InMemoryDomainEventDispatcher
from src.domain.events.value_objects import (
    EnergyLevel,
    DopamineReward,
    EventSource,
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
from src.application.events.dtos import (
    CreateEventCommand,
    RescheduleEventCommand,
)

# Global or module dispatcher
tool_event_dispatcher = InMemoryDomainEventDispatcher()


# ── Tool Schemas ──────────────────────────────────────────────────────────────


class CreateEventToolInput(BaseModel):
    title: str = Field(description="Title or summary of the event/task.")
    start_time: str = Field(
        description="Start datetime in ISO 8601 format (e.g. '2026-11-05T10:00:00Z')."
    )
    end_time: Optional[str] = Field(
        default=None,
        description="End datetime in ISO 8601 format. If omitted, defaults to 1 hour after start_time.",
    )
    description: Optional[str] = Field(
        default=None, description="Detailed notes, description, or checklist items."
    )
    typology: Optional[str] = Field(
        default=None,
        description="Category/Typology ID or name (e.g., 'Work', 'Health', 'Focus').",
    )
    energy_level: Optional[str] = Field(
        default="MEDIUM_ENERGY",
        description="Expected energy demand: 'HIGH_ENERGY', 'MEDIUM_ENERGY', or 'LOW_ENERGY'.",
    )
    cognitive_load: Optional[int] = Field(
        default=3,
        description="Mental effort scale from 1 (trivial/relaxing) to 5 (deep focus/draining).",
    )
    trigger_type: Optional[str] = Field(
        default="TIME",
        description="Trigger mechanism: 'TIME' for standard time-based events or 'LOCATION' for geofence/place triggers.",
    )
    location_name: Optional[str] = Field(
        default=None,
        description="Name of saved place/POI (e.g. 'Home', 'Parents\\' House', 'Office') when trigger_type is 'LOCATION'.",
    )
    trigger_condition: Optional[str] = Field(
        default="ENTER",
        description="Geofence event condition: 'ENTER' (when arriving) or 'EXIT' (when leaving).",
    )


class GetEventsToolInput(BaseModel):
    start_date: Optional[str] = Field(
        default=None,
        description="Start ISO date or datetime to filter events (e.g. '2026-11-05').",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="End ISO date or datetime to filter events (e.g. '2026-11-06').",
    )


class RescheduleEventToolInput(BaseModel):
    event_id: str = Field(description="Unique ID of the event to reschedule.")
    new_start_time: str = Field(
        description="New start datetime in ISO 8601 format."
    )
    new_end_time: Optional[str] = Field(
        default=None,
        description="New end datetime in ISO 8601 format.",
    )


# ── Tool Factory ──────────────────────────────────────────────────────────────


def _parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    cleaned = dt_str.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        # Fallback date-only format
        try:
            dt = datetime.strptime(cleaned, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None


def get_event_tools(session: Session) -> List[StructuredTool]:
    """Factory creating tools bound to the active database session."""
    repo = SqlModelEventRepository(session)
    location_repo = SqlModelLocationRepository(session)
    create_uc = CreateEventUseCase(repo, tool_event_dispatcher)
    reschedule_uc = RescheduleEventUseCase(repo, tool_event_dispatcher)

    def create_event(
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        typology: Optional[str] = None,
        energy_level: Optional[str] = "MEDIUM_ENERGY",
        cognitive_load: Optional[int] = 3,
        trigger_type: Optional[str] = "TIME",
        location_name: Optional[str] = None,
        trigger_condition: Optional[str] = "ENTER",
    ) -> Dict[str, Any]:
        """Create a new calendar event, task, or location-based reminder."""
        st = _parse_dt(start_time)
        if not st:
            return {
                "error": f"Invalid start_time format '{start_time}'. Please use ISO format like YYYY-MM-DDTHH:MM:SS."
            }

        et = _parse_dt(end_time) if end_time else None
        if not et and st:
            from datetime import timedelta
            et = st + timedelta(hours=1)

        energy = EnergyLevel.MEDIUM_ENERGY
        if energy_level:
            try:
                energy = EnergyLevel(energy_level.upper())
            except Exception:
                energy = EnergyLevel.MEDIUM_ENERGY

        load = 3
        if cognitive_load is not None:
            load = max(1, min(5, cognitive_load))

        # Resolve location trigger
        resolved_trigger_type = TriggerType.TIME_BASED
        resolved_location_id = None
        resolved_condition = None

        if trigger_type and trigger_type.upper() in ["LOCATION", "LOCATION_ENTER", "LOCATION_EXIT"]:
            cond_str = (trigger_condition or "ENTER").upper()
            resolved_condition = TriggerCondition.ON_EXIT if cond_str in ["EXIT", "ON_EXIT"] else TriggerCondition.ON_ENTER
            resolved_trigger_type = TriggerType.LOCATION_EXIT if resolved_condition == TriggerCondition.ON_EXIT else TriggerType.LOCATION_ENTER

            if location_name:
                matched_loc = location_repo.find_by_name(location_name)
                if matched_loc:
                    resolved_location_id = matched_loc.id
                else:
                    return {
                        "error": f"Location '{location_name}' was not found in saved places. Please ask the user to save this location first using manage_locations (with latitude/longitude)."
                    }
            else:
                return {"error": "A location_name is required when trigger_type is 'LOCATION'."}

        cmd = CreateEventCommand(
            title=title,
            start_time=st,
            end_time=et,
            description=description,
            typology_id=typology,
            trigger_type=resolved_trigger_type,
            location_id=resolved_location_id,
            trigger_condition=resolved_condition,
            energy_level=energy,
            cognitive_load=load,
            source=EventSource.LOCAL,
        )

        try:
            event = create_uc.execute(cmd)
            result = {
                "status": "success",
                "event_id": event.id,
                "title": event.title,
                "start_time": event.time_range.start_time.isoformat(),
                "end_time": event.time_range.end_time.isoformat() if event.time_range.end_time else None,
                "cognitive_load": event.cognitive_load,
                "energy_level": event.energy_level.value,
                "trigger_type": event.trigger_type.value,
            }
            if event.location_id:
                result["location_id"] = event.location_id
                result["trigger_condition"] = event.trigger_condition.value if event.trigger_condition else None
            return result
        except Exception as e:
            return {"error": f"Failed to create event: {str(e)}"}

    def get_events(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve user calendar events within an optional date range."""
        st = _parse_dt(start_date)
        et = _parse_dt(end_date)
        events = repo.find_by_date_range(st, et)
        return {
            "count": len(events),
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "description": e.description,
                    "start_time": e.time_range.start_time.isoformat(),
                    "end_time": e.time_range.end_time.isoformat() if e.time_range.end_time else None,
                    "cognitive_load": e.cognitive_load,
                    "energy_level": e.energy_level.value,
                    "is_read_only": e.is_read_only,
                    "source": e.source.value,
                }
                for e in events
            ],
        }

    def reschedule_event(
        event_id: str,
        new_start_time: str,
        new_end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reschedule an existing event to a new start/end time."""
        st = _parse_dt(new_start_time)
        if not st:
            return {"error": f"Invalid new_start_time format '{new_start_time}'."}
        et = _parse_dt(new_end_time) if new_end_time else None

        cmd = RescheduleEventCommand(
            event_id=event_id,
            new_start_time=st,
            new_end_time=et,
        )

        try:
            reschedule_uc.execute(cmd)
            return {
                "status": "success",
                "message": f"Event '{event_id}' rescheduled successfully to {st.isoformat()}.",
            }
        except ImmutableEventException as e:
            return {
                "error": f"Event '{event_id}' cannot be modified because it is read-only (external source: {e.source}). Please update it in the external calendar."
            }
        except EventNotFoundException:
            return {"error": f"Event '{event_id}' not found."}
        except Exception as e:
            return {"error": f"Failed to reschedule event: {str(e)}"}

    return [
        StructuredTool.from_function(
            func=create_event,
            name="create_event",
            description="Create a new calendar event, task, or reminder for the user.",
            args_schema=CreateEventToolInput,
        ),
        StructuredTool.from_function(
            func=get_events,
            name="get_events",
            description="Query and list calendar events within an optional date range (start_date, end_date).",
            args_schema=GetEventsToolInput,
        ),
        StructuredTool.from_function(
            func=reschedule_event,
            name="reschedule_event",
            description="Reschedule an existing event to a new date and time. Validates read-only permissions.",
            args_schema=RescheduleEventToolInput,
        ),
    ]

