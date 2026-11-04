"""
Value Objects for the LanDo event bounded context.

All Value Objects are immutable (frozen dataclasses). They encapsulate
primitive obsession and enforce their own invariants in __post_init__.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Enumerations ──────────────────────────────────────────────────────────────


class EventSource(str, Enum):
    """Where this event was created / authoritative system of record."""

    LOCAL = "LOCAL"
    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    CALDAV = "CALDAV"


class EnergyLevel(str, Enum):
    """Estimated physical / mental energy required to complete the event."""

    HIGH_ENERGY = "HIGH_ENERGY"
    MEDIUM_ENERGY = "MEDIUM_ENERGY"
    LOW_ENERGY = "LOW_ENERGY"


class DopamineReward(str, Enum):
    """Anticipated sense of accomplishment after completing the event."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecurrenceFrequency(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    CUSTOM = "CUSTOM"


class ReminderStatus(str, Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"


# ── Value Objects ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TimeRange:
    """
    Represents the temporal span of an event.

    - For all-day events, only ``start_time`` is meaningful (end_time is None).
    - ``end_time`` must be strictly after ``start_time`` when provided.
    """

    start_time: datetime
    end_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.end_time is not None and self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be strictly after start_time ({self.start_time})."
            )

    def duration_minutes(self) -> Optional[float]:
        """Return event duration in minutes, or None for open-ended events."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds() / 60.0

    def overlaps(self, other: TimeRange) -> bool:
        """Return True if this range overlaps with another."""
        self_end = self.end_time or self.start_time
        other_end = other.end_time or other.start_time
        return self.start_time < other_end and other.start_time < self_end


@dataclass(frozen=True)
class RecurrenceRule:
    """
    Describes how an event repeats over time.

    Constraints:
    - ``interval`` must be ≥ 1.
    - ``until_date`` and ``count`` are mutually exclusive.
    """

    frequency: RecurrenceFrequency
    interval: int = 1
    until_date: Optional[datetime] = None
    count: Optional[int] = None

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError(f"interval must be ≥ 1, got {self.interval}.")
        if self.until_date is not None and self.count is not None:
            raise ValueError(
                "Cannot specify both until_date and count in a RecurrenceRule. "
                "Choose one termination strategy."
            )
        if self.count is not None and self.count < 1:
            raise ValueError(f"count must be ≥ 1, got {self.count}.")

    @property
    def is_infinite(self) -> bool:
        """Return True when neither until_date nor count terminates the series."""
        return self.until_date is None and self.count is None

    def generate_occurrences(
        self, start_time: datetime, max_occurrences: int = 50
    ) -> list[datetime]:
        """
        Calculate and generate upcoming event dates based on the recurrence rule.
        Includes start_time as the 1st occurrence if count >= 1 or until_date >= start_time.
        """
        from datetime import timedelta
        import calendar

        occurrences: list[datetime] = []
        limit = self.count if self.count is not None else max_occurrences
        target_day = start_time.day

        for i in range(limit):
            if self.frequency == RecurrenceFrequency.DAILY:
                current = start_time + timedelta(days=i * self.interval)
            elif self.frequency == RecurrenceFrequency.WEEKLY:
                current = start_time + timedelta(weeks=i * self.interval)
            elif self.frequency == RecurrenceFrequency.MONTHLY:
                total_months = (start_time.month - 1) + (i * self.interval)
                year = start_time.year + (total_months // 12)
                month = (total_months % 12) + 1
                max_day = calendar.monthrange(year, month)[1]
                day = min(target_day, max_day)
                current = start_time.replace(year=year, month=month, day=day)
            elif self.frequency == RecurrenceFrequency.CUSTOM:
                current = start_time + timedelta(days=i * self.interval)
            else:
                break

            if self.until_date is not None and current > self.until_date:
                break

            occurrences.append(current)

        return occurrences


@dataclass(frozen=True)
class EventReminder:
    """
    A notification scheduled before an event starts.

    - ``minutes_before`` must be non-negative (0 = at event start).
    - ``is_absorbed_from_external`` marks reminders imported from external calendars.
    - Immutable; use ``dispatch()`` to transition status.
    """

    minutes_before: int
    is_absorbed_from_external: bool = False
    status: ReminderStatus = ReminderStatus.PENDING

    def __post_init__(self) -> None:
        if self.minutes_before < 0:
            raise ValueError(
                f"minutes_before must be non-negative, got {self.minutes_before}."
            )

    def dispatch(self) -> EventReminder:
        """Return a new EventReminder with status DISPATCHED (preserves immutability)."""
        return EventReminder(
            minutes_before=self.minutes_before,
            is_absorbed_from_external=self.is_absorbed_from_external,
            status=ReminderStatus.DISPATCHED,
        )

    @property
    def is_pending(self) -> bool:
        return self.status == ReminderStatus.PENDING

