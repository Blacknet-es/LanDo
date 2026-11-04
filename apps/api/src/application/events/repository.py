"""
Repository Protocol for the Event aggregate.

Defines the persistence contract as a structural Protocol so the application
layer stays decoupled from any concrete ORM or database technology.

Implementations live in ``src/infrastructure/db/``.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from src.domain.events.entities import Event


@runtime_checkable
class EventRepository(Protocol):
    def find_by_id(self, event_id: str) -> Optional[Event]:
        """Return the Event with the given id, or None if not found."""
        ...

    def save(self, event: Event) -> None:
        """Persist (insert or update) the event."""
        ...

    def delete(self, event_id: str) -> None:
        """Remove the event from persistence."""
        ...

