"""
Repository Protocol for the Event aggregate.

Defines the persistence contract as a structural Protocol so the application
layer stays decoupled from any concrete ORM or database technology.

Implementations live in ``src/infrastructure/db/``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from src.domain.events.entities import Event


@runtime_checkable
class EventRepository(Protocol):
    def find_by_id(self, event_id: str) -> Event | None:
        """Return the Event with the given id, or None if not found."""
        ...

    def save(self, event: Event) -> None:
        """Persist (insert or update) the event."""
        ...

    def find_all(self, limit: int = 100, offset: int = 0) -> list[Event]:
        """Return events for this repository's tenant."""
        ...

    def find_by_date_range(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[Event]:
        """Return tenant-owned events in the optional inclusive date range."""
        ...

    def delete(self, event_id: str) -> None:
        """Remove the event from persistence."""
        ...
