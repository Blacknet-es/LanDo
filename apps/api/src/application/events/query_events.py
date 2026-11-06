from datetime import datetime

from src.application.events.repository import EventRepository
from src.domain.events.entities import Event


class GetEventUseCase:
    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    def execute(self, event_id: str) -> Event | None:
        return self._repository.find_by_id(event_id)


class ListEventsUseCase:
    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    def execute(
        self,
        limit: int = 100,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Event]:
        if start_date is not None or end_date is not None:
            return self._repository.find_by_date_range(start_date, end_date)
        return self._repository.find_all(limit=limit, offset=offset)
