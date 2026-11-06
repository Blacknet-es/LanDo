from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from sqlmodel import Session

from src.application.events.dispatcher import DomainEventDispatcher
from src.domain.events.events import (
    DomainEvent,
    EventCreatedDomainEvent,
    EventRescheduledDomainEvent,
)
from src.infrastructure.db.models import EventOutboxModel

EventType = TypeVar("EventType", bound=DomainEvent)
EventHandler = Callable[[DomainEvent], None]


class InMemoryDomainEventDispatcher(DomainEventDispatcher):
    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)
        self.collected: list[DomainEvent] = []

    def subscribe(self, event_type: type[EventType], handler: Callable[[EventType], None]) -> None:
        self._handlers[event_type].append(handler)

    def dispatch(self, event: DomainEvent) -> None:
        self.collected.append(event)
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def dispatch_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.dispatch(event)

    def clear_collected(self) -> None:
        self.collected.clear()


event_dispatcher = InMemoryDomainEventDispatcher()


class SqlModelDomainEventDispatcher(DomainEventDispatcher):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self._session = session
        self._user_id = user_id

    def dispatch(self, event: DomainEvent) -> None:
        payload: dict[str, object] | None = None
        event_type: str | None = None
        if isinstance(event, EventCreatedDomainEvent):
            event_type = "event.created"
            payload = {
                "schema_version": "1",
                "event_id": str(event.event_id),
                "aggregate_id": event.aggregate_id,
                "user_id": str(self._user_id),
                "title": event.title,
                "source": event.source,
                "occurred_at": event.occurred_at.isoformat(),
            }
        elif isinstance(event, EventRescheduledDomainEvent):
            event_type = "event.rescheduled"
            payload = {
                "schema_version": "1",
                "event_id": str(event.event_id),
                "aggregate_id": event.aggregate_id,
                "user_id": str(self._user_id),
                "old_start": event.old_start.isoformat() if event.old_start else None,
                "new_start": event.new_start.isoformat(),
                "old_end": event.old_end.isoformat() if event.old_end else None,
                "new_end": event.new_end.isoformat() if event.new_end else None,
                "occurred_at": event.occurred_at.isoformat(),
            }
        if event_type is not None and payload is not None:
            self._session.add(
                EventOutboxModel(
                    event_id=event.event_id,
                    user_id=self._user_id,
                    event_type=event_type,
                    payload=payload,
                )
            )

    def dispatch_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.dispatch(event)
        self._session.commit()
