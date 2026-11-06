from typing import Protocol

from src.domain.events.events import DomainEvent


class DomainEventDispatcher(Protocol):
    def dispatch(self, event: DomainEvent) -> None: ...

    def dispatch_all(self, events: list[DomainEvent]) -> None: ...
