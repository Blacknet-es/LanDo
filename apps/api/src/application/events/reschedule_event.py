"""
RescheduleEventUseCase — moves an event to a new time range.

Key invariant enforced: ``Event.reschedule()`` raises
``ImmutableEventException`` if the event is read-only (external source).
The use-case lets that exception propagate so the API layer can map it to
a 403 response.
"""

from __future__ import annotations

from src.application.events.dtos import RescheduleEventCommand
from src.application.events.repository import EventRepository
from src.domain.events.dispatcher import DomainEventDispatcher
from src.domain.events.exceptions import EventNotFoundException
from src.domain.events.value_objects import TimeRange


class RescheduleEventUseCase:
    def __init__(
        self,
        repository: EventRepository,
        dispatcher: DomainEventDispatcher,
    ) -> None:
        self._repository = repository
        self._dispatcher = dispatcher

    def execute(self, command: RescheduleEventCommand) -> None:
        event = self._repository.find_by_id(command.event_id)
        if event is None:
            raise EventNotFoundException(command.event_id)

        new_time_range = TimeRange(
            start_time=command.new_start_time,
            end_time=command.new_end_time,
        )

        # Raises ImmutableEventException for read-only events — let it propagate.
        event.reschedule(new_time_range)

        self._repository.save(event)
        self._dispatcher.dispatch_all(event.pull_domain_events())

