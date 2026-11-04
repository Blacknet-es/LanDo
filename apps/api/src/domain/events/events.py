"""
Domain Events for the LanDo event bounded context.

Domain Events are immutable records of *something that happened* inside the
aggregate. They are the EDD backbone: use-cases collect them from the
aggregate via ``pull_domain_events()`` and hand them off to the dispatcher.

Naming convention: <AggregateChange>DomainEvent
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


# ── Base ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DomainEvent:
    """
    Abstract base for all domain events.

    Every event carries:
    - a unique ``event_id`` (UUID v4) for idempotency and tracing.
    - an ``occurred_at`` UTC timestamp set at construction time.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ── Event Aggregate Domain Events ─────────────────────────────────────────────


@dataclass(frozen=True)
class EventCreatedDomainEvent(DomainEvent):
    """
    Published when a new Event aggregate is successfully created.
    Triggers reminder scheduling, recurrence expansion, and audit logging.
    """

    aggregate_id: str = ""
    title: str = ""
    source: str = ""  # EventSource.value


@dataclass(frozen=True)
class EventRescheduledDomainEvent(DomainEvent):
    """
    Published when an Event's TimeRange is changed via ``Event.reschedule()``.
    Downstream handlers should re-schedule notifications and sync to external
    calendars where applicable.
    """

    aggregate_id: str = ""
    old_start: Optional[datetime] = None
    new_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    old_end: Optional[datetime] = None
    new_end: Optional[datetime] = None


@dataclass(frozen=True)
class EventRecurrenceGeneratedDomainEvent(DomainEvent):
    """
    Published after recurrence occurrences have been expanded from a master event.
    ``occurrences_count`` reflects how many child events were generated in this batch.
    """

    aggregate_id: str = ""
    occurrences_count: int = 0
    frequency: str = ""  # RecurrenceFrequency.value


@dataclass(frozen=True)
class ReminderScheduledDomainEvent(DomainEvent):
    """
    Published when a new local reminder is attached to an event.
    Downstream notification services should subscribe to this event.
    """

    aggregate_id: str = ""
    minutes_before: int = 0


@dataclass(frozen=True)
class ExternalReminderAbsorbedDomainEvent(DomainEvent):
    """
    Published when a reminder originating from an external calendar system
    (Google Calendar, CalDAV, …) is absorbed into a read-only event.

    Unlike ``ReminderScheduledDomainEvent`` this event does NOT trigger
    local notification scheduling — the source system owns the delivery.
    """

    aggregate_id: str = ""
    minutes_before: int = 0
    external_source: str = ""  # EventSource.value

