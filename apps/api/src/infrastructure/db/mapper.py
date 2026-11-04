"""
Mapper: SQLModel schemas ↔ Domain Entities.

Keeps infrastructure concerns (ORM columns, nullable FKs) completely out of
the domain layer. The mapper is the only place that knows about both worlds.

Convention:
  ``to_domain(model)``      → domain entity / value object
  ``to_model(entity)``      → SQLModel ORM row (ready for session.add)
  ``update_model(entity, model)`` → mutate an existing row in-place
"""

from __future__ import annotations

from src.domain.events.entities import Event, Typology
from src.domain.events.value_objects import (
    DopamineReward,
    EnergyLevel,
    EventReminder,
    EventSource,
    RecurrenceFrequency,
    RecurrenceRule,
    ReminderStatus,
    TimeRange,
)
from src.infrastructure.db.models import (
    EventModel,
    EventReminderModel,
    RecurrenceRuleModel,
    TypologyModel,
)


# ── Typology ──────────────────────────────────────────────────────────────────


def typology_to_domain(model: TypologyModel) -> Typology:
    return Typology(
        id=model.id,
        name=model.name,
        color_hex=model.color_hex,
        icon=model.icon,
        is_system_preset=model.is_system_preset,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def typology_to_model(entity: Typology) -> TypologyModel:
    return TypologyModel(
        id=entity.id,
        name=entity.name,
        color_hex=entity.color_hex,
        icon=entity.icon,
        is_system_preset=entity.is_system_preset,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


# ── EventReminder ─────────────────────────────────────────────────────────────


def reminder_to_domain(model: EventReminderModel) -> EventReminder:
    return EventReminder(
        minutes_before=model.minutes_before,
        is_absorbed_from_external=model.is_absorbed_from_external,
        status=ReminderStatus(model.status),
    )


def reminder_to_model(reminder: EventReminder, event_id: str) -> EventReminderModel:
    return EventReminderModel(
        event_id=event_id,
        minutes_before=reminder.minutes_before,
        is_absorbed_from_external=reminder.is_absorbed_from_external,
        status=reminder.status.value,
    )


# ── RecurrenceRule ────────────────────────────────────────────────────────────


def recurrence_to_domain(model: RecurrenceRuleModel) -> RecurrenceRule:
    return RecurrenceRule(
        frequency=RecurrenceFrequency(model.frequency),
        interval=model.interval,
        until_date=model.until_date,
        count=model.count,
    )


def recurrence_to_model(rule: RecurrenceRule, event_id: str) -> RecurrenceRuleModel:
    return RecurrenceRuleModel(
        event_id=event_id,
        frequency=rule.frequency.value,
        interval=rule.interval,
        until_date=rule.until_date,
        count=rule.count,
    )


# ── Event ─────────────────────────────────────────────────────────────────────


def event_to_domain(model: EventModel) -> Event:
    time_range = TimeRange(start_time=model.start_time, end_time=model.end_time)

    recurrence_rule: RecurrenceRule | None = None
    if model.recurrence_rule is not None:
        recurrence_rule = recurrence_to_domain(model.recurrence_rule)

    reminders = [reminder_to_domain(r) for r in (model.reminders or [])]

    # Reconstruct the aggregate without triggering __post_init__ side-effects
    # by using a direct constructor call with all fields populated.
    event = Event(
        id=model.id,
        title=model.title,
        description=model.description,
        time_range=time_range,
        is_all_day=model.is_all_day,
        source=EventSource(model.source),
        external_id=model.external_id,
        is_read_only=model.is_read_only,
        typology_id=model.typology_id,
        energy_level=EnergyLevel(model.energy_level),
        cognitive_load=model.cognitive_load,
        dopamine_reward=DopamineReward(model.dopamine_reward),
        recurrence_rule=recurrence_rule,
        reminders=reminders,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
    return event


def event_to_model(entity: Event) -> EventModel:
    return EventModel(
        id=entity.id,
        title=entity.title,
        description=entity.description,
        start_time=entity.time_range.start_time,
        end_time=entity.time_range.end_time,
        is_all_day=entity.is_all_day,
        source=entity.source.value,
        external_id=entity.external_id,
        is_read_only=entity.is_read_only,
        typology_id=entity.typology_id,
        energy_level=entity.energy_level.value,
        cognitive_load=entity.cognitive_load,
        dopamine_reward=entity.dopamine_reward.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def update_model_from_entity(entity: Event, model: EventModel) -> None:
    """Mutate an existing ORM row in-place from the current entity state."""
    model.title = entity.title
    model.description = entity.description
    model.start_time = entity.time_range.start_time
    model.end_time = entity.time_range.end_time
    model.is_all_day = entity.is_all_day
    model.energy_level = entity.energy_level.value
    model.cognitive_load = entity.cognitive_load
    model.dopamine_reward = entity.dopamine_reward.value
    model.typology_id = entity.typology_id
    model.updated_at = entity.updated_at

