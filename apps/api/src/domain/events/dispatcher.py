"""
Domain Event Dispatcher — interface and in-memory implementation.

The dispatcher decouples aggregates from side-effects:
  1. Aggregates record domain events internally (``_domain_events`` list).
  2. Use-cases drain events via ``pull_domain_events()`` and pass them here.
  3. Registered handlers react (send emails, update read models, log, etc.).

For production, swap ``InMemoryDomainEventDispatcher`` for an async
message-broker-backed implementation without changing any domain code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Callable, Generic, Type, TypeVar

from src.domain.events.events import DomainEvent

T = TypeVar("T", bound=DomainEvent)

# A handler is any callable that accepts a single DomainEvent subclass instance.
EventHandler = Callable[[DomainEvent], None]


# ── Interface ─────────────────────────────────────────────────────────────────


class DomainEventDispatcher(ABC):
    """
    Abstract dispatcher contract.

    Implementations must be safe to call from synchronous use-case code.
    Async dispatching (Celery, Redis Streams, etc.) should be handled
    inside the handler rather than the dispatcher itself.
    """

    @abstractmethod
    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        """Register ``handler`` to be called whenever ``event_type`` is dispatched."""
        ...

    @abstractmethod
    def dispatch(self, event: DomainEvent) -> None:
        """Dispatch a single domain event to all registered handlers."""
        ...

    @abstractmethod
    def dispatch_all(self, events: list[DomainEvent]) -> None:
        """Convenience: dispatch a sequence of domain events in order."""
        ...


# ── In-Memory Implementation ──────────────────────────────────────────────────


class InMemoryDomainEventDispatcher(DomainEventDispatcher):
    """
    Synchronous, in-process dispatcher backed by a simple dict.

    Suitable for:
    - Unit and integration tests (inspect ``collected`` for assertions).
    - Local development without an external broker.

    Replace with a broker-backed implementation in production.
    """

    def __init__(self) -> None:
        self._handlers: dict[Type[DomainEvent], list[EventHandler]] = defaultdict(list)
        # Optional: accumulate all dispatched events for test assertions.
        self.collected: list[DomainEvent] = []

    def subscribe(self, event_type: Type[T], handler: Callable[[T], None]) -> None:
        self._handlers[event_type].append(handler)  # type: ignore[arg-type]

    def dispatch(self, event: DomainEvent) -> None:
        self.collected.append(event)
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def dispatch_all(self, events: list[DomainEvent]) -> None:
        for event in events:
            self.dispatch(event)

    def clear_collected(self) -> None:
        """Reset the collected event log — useful between test cases."""
        self.collected.clear()

