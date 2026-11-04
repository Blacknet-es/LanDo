"""
DTOs and Commands for the event application layer.

Commands are plain dataclasses that cross the application boundary —
they carry user intent without any domain logic. The use-cases translate
them into domain calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.domain.events.value_objects import (
    DopamineReward,
    EnergyLevel,
    EventSource,
    RecurrenceFrequency,
)


# ── Sub-DTOs ──────────────────────────────────────────────────────────────────


@dataclass
class RecurrenceRuleDTO:
    frequency: RecurrenceFrequency
    interval: int = 1
    until_date: Optional[datetime] = None
    count: Optional[int] = None


# ── Commands ──────────────────────────────────────────────────────────────────


@dataclass
class CreateEventCommand:
    """Input for CreateEventUseCase."""

    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    is_all_day: bool = False
    source: EventSource = EventSource.LOCAL
    external_id: Optional[str] = None
    typology_id: Optional[str] = None
    energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY
    cognitive_load: int = 3
    dopamine_reward: DopamineReward = DopamineReward.MEDIUM
    recurrence_rule: Optional[RecurrenceRuleDTO] = None
    # Reminder offsets in minutes (e.g. [15, 60] = 15 min and 1 hr before)
    reminder_minutes: list[int] = field(default_factory=list)


@dataclass
class RescheduleEventCommand:
    """Input for RescheduleEventUseCase."""

    event_id: str
    new_start_time: datetime
    new_end_time: Optional[datetime] = None


@dataclass
class AbsorbExternalRemindersCommand:
    """Input for AbsorbExternalRemindersUseCase."""

    event_id: str
    # Minutes-before values to absorb (from an external calendar sync)
    reminder_minutes: list[int]

