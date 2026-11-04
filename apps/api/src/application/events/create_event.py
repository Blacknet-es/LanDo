"""
CreateEventUseCase — orchestrates event creation end-to-end.

Responsibilities:
1. Translate the command DTO into domain Value Objects.
2. Call ``Event.create()`` (factory), which enforces invariants and buffers
   ``EventCreatedDomainEvent``.
3. Attach reminders (each call buffers ``ReminderScheduledDomainEvent``).
4. Persist via the repository.
5. Drain and dispatch all buffered domain events.

The use-case never imports from infrastructure — it depends only on the
EventRepository Protocol defined in this same application layer.
"""

from __future__ import annotations

from src.application.events.dtos import CreateEventCommand
from src.application.events.repository import EventRepository
from src.domain.events.dispatcher import DomainEventDispatcher
from src.domain.events.entities import Event
from src.domain.events.value_objects import RecurrenceRule, TimeRange


class CreateEventUseCase:
    def __init__(
        self,
        repository: EventRepository,
        dispatcher: DomainEventDispatcher,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher

    def execute(self, command: CreateEventCommand) -> Event:
        # 1. Build value objects from the command DTO
        time_range = TimeRange(
            start_time=command.start_time,
            end_time=command.end_time,
        )

        recurrence_rule: RecurrenceRule | None = None
        if command.recurrence_rule is not None:
            recurrence_rule = RecurrenceRule(
                frequency=command.recurrence_rule.frequency,
                interval=command.recurrence_rule.interval,
                until_date=command.recurrence_rule.until_date,
                count=command.recurrence_rule.count,
            )

        # 2. Create aggregate (invariants enforced inside, EventCreated buffered)
        event = Event.create(
            title=command.title,
            time_range=time_range,
            description=command.description,
            is_all_day=command.is_all_day,
            source=command.source,
            external_id=command.external_id,
            typology_id=command.typology_id,
            trigger_type=command.trigger_type,
            location_id=command.location_id,
            trigger_condition=command.trigger_condition,
            energy_level=command.energy_level,
            cognitive_load=command.cognitive_load,
            dopamine_reward=command.dopamine_reward,
            recurrence_rule=recurrence_rule,
        )

        # 3. Attach reminders (ReminderScheduled buffered for each)
        for minutes in command.reminder_minutes:
            if command.source.value == "LOCAL":
                event.add_reminder(minutes)
            else:
                # External events get absorbed reminders, not local ones
                event.absorb_external_reminder(minutes)

        # 4. Persist
        self._repository.save(event)

        # 5. Drain and dispatch all buffered domain events
        self._dispatcher.dispatch_all(event.pull_domain_events())

        return event

