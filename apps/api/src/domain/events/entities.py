"""
Domain Entities for the LanDo event bounded context.

``Event`` is the aggregate root. All invariants are enforced inside the
entity; no business logic leaks into application or infrastructure layers.

Design decisions:
- ``dataclass`` (not Pydantic) keeps domain code framework-agnostic.
- Mutable fields are intentional for a rich-domain model; SQLModel schemas
  in infrastructure handle persistence separately.
- Domain events accumulate in ``_domain_events`` and are drained by use-cases.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from src.domain.events.events import (
    DomainEvent,
    EventCreatedDomainEvent,
    EventRescheduledDomainEvent,
    ExternalReminderAbsorbedDomainEvent,
    ReminderScheduledDomainEvent,
)
from src.domain.events.exceptions import (
    ImmutableEventException,
    InvalidCognitiveLoadException,
)
from src.domain.events.value_objects import (
    DopamineReward,
    EnergyLevel,
    EventReminder,
    EventSource,
    RecurrenceRule,
    TimeRange,
    TriggerType,
    TriggerCondition,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ── Typology ──────────────────────────────────────────────────────────────────


@dataclass
class Typology:
    """
    Categories that describe the nature of an event (e.g. Work, Health, Social).

    System presets ship with LanDo and cannot be renamed or deleted.
    Users may create custom typologies freely.
    """

    id: str = field(default_factory=_new_id)
    name: str = ""
    color_hex: str = "#6366f1"
    icon: str = "📌"
    is_system_preset: bool = False
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    def rename(self, new_name: str) -> None:
        """Rename this typology. System presets are immutable."""
        if self.is_system_preset:
            raise ValueError(
                f"Cannot rename system preset typology '{self.name}'. "
                "Create a custom typology instead."
            )
        if not new_name.strip():
            raise ValueError("Typology name cannot be blank.")
        self.name = new_name.strip()
        self.updated_at = _now()

    def update_appearance(self, color_hex: Optional[str] = None, icon: Optional[str] = None) -> None:
        if self.is_system_preset:
            raise ValueError("Cannot modify the appearance of a system preset typology.")
        if color_hex is not None:
            self.color_hex = color_hex
        if icon is not None:
            self.icon = icon
        self.updated_at = _now()


# ── Event Aggregate Root ───────────────────────────────────────────────────────


@dataclass
class Event:
    """
    Core aggregate root for LanDo.

    Encapsulates:
    - Scheduling (time range, all-day flag, recurrence)
    - Cognitive attributes (energy level, cognitive load, dopamine reward)
    - Reminders (local + absorbed from external systems)
    - Provenance (source, external_id, read-only flag)

    Invariants enforced at construction:
    1. ``cognitive_load`` must be in [1, 5].
    2. If ``source != LOCAL``, ``is_read_only`` must be True.

    Domain events are buffered in ``_domain_events`` and must be drained
    by the use-case via ``pull_domain_events()`` before persisting.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    id: str = field(default_factory=_new_id)

    # ── Core fields ───────────────────────────────────────────────────────────
    title: str = ""
    description: Optional[str] = None
    time_range: TimeRange = field(default_factory=lambda: TimeRange(start_time=_now()))
    is_all_day: bool = False

    # ── Provenance ────────────────────────────────────────────────────────────
    source: EventSource = EventSource.LOCAL
    external_id: Optional[str] = None
    is_read_only: bool = False

    # ── Typology ──────────────────────────────────────────────────────────────
    typology_id: Optional[str] = None

    # ── Location & Geofencing ────────────────────────────────────────────────
    trigger_type: TriggerType = TriggerType.TIME_BASED
    location_id: Optional[str] = None
    trigger_condition: Optional[TriggerCondition] = None

    # ── ADHD / Cognitive load attributes ─────────────────────────────────────
    energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY
    cognitive_load: int = 3  # 1–5 scale
    dopamine_reward: DopamineReward = DopamineReward.MEDIUM

    # ── Recurrence ────────────────────────────────────────────────────────────
    recurrence_rule: Optional[RecurrenceRule] = None

    # ── Reminders ─────────────────────────────────────────────────────────────
    reminders: list[EventReminder] = field(default_factory=list)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    # ── Pending domain events (not persisted, drained by use-cases) ───────────
    _domain_events: list[DomainEvent] = field(
        default_factory=list, repr=False, compare=False, hash=False
    )

    # ── Invariant enforcement ─────────────────────────────────────────────────

    def __post_init__(self) -> None:
        self._enforce_source_invariant()
        self._enforce_cognitive_load_invariant()

    def _enforce_source_invariant(self) -> None:
        """Events from external sources MUST be read-only on creation."""
        if self.source != EventSource.LOCAL and not self.is_read_only:
            raise ValueError(
                f"Events originating from '{self.source.value}' must have "
                "is_read_only=True. The external system is the source of truth."
            )

    def _enforce_cognitive_load_invariant(self) -> None:
        if not (1 <= self.cognitive_load <= 5):
            raise InvalidCognitiveLoadException(self.cognitive_load)

    def _guard_immutable(self) -> None:
        """Raise ImmutableEventException if this event cannot be mutated locally."""
        if self.is_read_only:
            raise ImmutableEventException(self.id, self.source.value)

    # ── Mutation API ──────────────────────────────────────────────────────────

    def reschedule(self, new_time_range: TimeRange) -> None:
        """
        Move the event to a new time range.

        Raises:
            ImmutableEventException: if ``is_read_only`` is True.
        """
        self._guard_immutable()
        old_range = self.time_range
        self.time_range = new_time_range
        self.updated_at = _now()
        self._domain_events.append(
            EventRescheduledDomainEvent(
                aggregate_id=self.id,
                old_start=old_range.start_time,
                new_start=new_time_range.start_time,
                old_end=old_range.end_time,
                new_end=new_time_range.end_time,
            )
        )

    def update_details(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        energy_level: Optional[EnergyLevel] = None,
        cognitive_load: Optional[int] = None,
        dopamine_reward: Optional[DopamineReward] = None,
        typology_id: Optional[str] = None,
    ) -> None:
        """
        Update mutable descriptive fields.

        Raises:
            ImmutableEventException: if ``is_read_only`` is True.
            InvalidCognitiveLoadException: if ``cognitive_load`` is outside [1, 5].
        """
        self._guard_immutable()
        if title is not None:
            if not title.strip():
                raise ValueError("Event title cannot be blank.")
            self.title = title.strip()
        if description is not None:
            self.description = description
        if energy_level is not None:
            self.energy_level = energy_level
        if cognitive_load is not None:
            if not (1 <= cognitive_load <= 5):
                raise InvalidCognitiveLoadException(cognitive_load)
            self.cognitive_load = cognitive_load
        if dopamine_reward is not None:
            self.dopamine_reward = dopamine_reward
        if typology_id is not None:
            self.typology_id = typology_id
        self.updated_at = _now()

    def set_recurrence(self, rule: RecurrenceRule) -> None:
        """
        Attach or replace a recurrence rule.

        Raises:
            ImmutableEventException: if ``is_read_only`` is True.
        """
        self._guard_immutable()
        self.recurrence_rule = rule
        self.updated_at = _now()

    def clear_recurrence(self) -> None:
        """Remove recurrence, turning this into a one-time event."""
        self._guard_immutable()
        self.recurrence_rule = None
        self.updated_at = _now()

    def add_reminder(self, minutes_before: int) -> EventReminder:
        """
        Attach a local reminder to this event.

        Raises:
            ImmutableEventException: if ``is_read_only`` is True.
        """
        self._guard_immutable()
        reminder = EventReminder(minutes_before=minutes_before)
        self.reminders.append(reminder)
        self._domain_events.append(
            ReminderScheduledDomainEvent(
                aggregate_id=self.id,
                minutes_before=minutes_before,
            )
        )
        return reminder

    def absorb_external_reminder(self, minutes_before: int) -> EventReminder:
        """
        Absorb a reminder sourced from an external calendar system.

        Unlike ``add_reminder``, this is permitted on read-only events —
        we are *recording* what the external system already declared,
        not creating a new local notification.
        """
        reminder = EventReminder(
            minutes_before=minutes_before,
            is_absorbed_from_external=True,
        )
        self.reminders.append(reminder)
        self._domain_events.append(
            ExternalReminderAbsorbedDomainEvent(
                aggregate_id=self.id,
                minutes_before=minutes_before,
                external_source=self.source.value,
            )
        )
        return reminder

    # ── Domain event draining ─────────────────────────────────────────────────

    def pull_domain_events(self) -> list[DomainEvent]:
        """
        Return all buffered domain events and clear the internal queue.

        Call this inside the use-case *after* all mutations, and *before*
        persisting, so events represent the final committed state.
        """
        events = list(self._domain_events)
        self._domain_events.clear()
        return events

    # ── Factory method ────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        title: str,
        time_range: TimeRange,
        *,
        description: Optional[str] = None,
        is_all_day: bool = False,
        source: EventSource = EventSource.LOCAL,
        external_id: Optional[str] = None,
        typology_id: Optional[str] = None,
        trigger_type: TriggerType = TriggerType.TIME_BASED,
        location_id: Optional[str] = None,
        trigger_condition: Optional[TriggerCondition] = None,
        energy_level: EnergyLevel = EnergyLevel.MEDIUM_ENERGY,
        cognitive_load: int = 3,
        dopamine_reward: DopamineReward = DopamineReward.MEDIUM,
        recurrence_rule: Optional[RecurrenceRule] = None,
    ) -> Event:
        """
        Named constructor — preferred way to create a new Event.

        Automatically sets ``is_read_only=True`` for external sources and
        emits ``EventCreatedDomainEvent``.
        """
        if not title.strip():
            raise ValueError("Event title cannot be blank.")

        is_read_only = source != EventSource.LOCAL
        event = cls(
            title=title.strip(),
            description=description,
            time_range=time_range,
            is_all_day=is_all_day,
            source=source,
            external_id=external_id,
            is_read_only=is_read_only,
            typology_id=typology_id,
            trigger_type=trigger_type,
            location_id=location_id,
            trigger_condition=trigger_condition,
            energy_level=energy_level,
            cognitive_load=cognitive_load,
            dopamine_reward=dopamine_reward,
            recurrence_rule=recurrence_rule,
        )
        event._domain_events.append(
            EventCreatedDomainEvent(
                aggregate_id=event.id,
                title=event.title,
                source=source.value,
            )
        )
        return event

