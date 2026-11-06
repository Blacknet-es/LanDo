"""
AbsorbExternalRemindersUseCase — imports reminders from external calendar systems.

When LanDo syncs a Google Calendar or CalDAV event it may carry reminder
offsets that the user set in those systems. This use-case absorbs them into
the read-only Event aggregate via ``absorb_external_reminder()``, which
does NOT raise ImmutableEventException (absorbing is a read path, not a
local mutation).
"""

from __future__ import annotations

from src.application.events.dispatcher import DomainEventDispatcher
from src.application.events.dtos import AbsorbExternalRemindersCommand
from src.application.events.repository import EventRepository
from src.domain.events.entities import Event
from src.domain.events.exceptions import EventNotFoundException


class AbsorbExternalRemindersUseCase:
    def __init__(
        self,
        repository: EventRepository,
        dispatcher: DomainEventDispatcher,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher

    def execute(self, command: AbsorbExternalRemindersCommand) -> Event:
        event = self._repository.find_by_id(command.event_id)
        if event is None:
            raise EventNotFoundException(command.event_id)

        for minutes in command.reminder_minutes:
            event.absorb_external_reminder(minutes)

        self._repository.save(event)
        self._dispatcher.dispatch_all(event.pull_domain_events())

        return event
