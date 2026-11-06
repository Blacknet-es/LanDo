from typing import Protocol
from uuid import UUID


class LocationTriggerRepository(Protocol):
    def user_exists(self, user_id: UUID) -> bool: ...

    def location_exists_for_user(self, location_id: str, user_id: UUID) -> bool: ...


class WebhookUserNotFound(Exception):
    pass


class WebhookLocationNotFound(Exception):
    pass


class ProcessLocationTriggerUseCase:
    def __init__(self, repository: LocationTriggerRepository) -> None:
        self._repository = repository

    def execute(self, user_id: UUID, location_id: str) -> None:
        if not self._repository.user_exists(user_id):
            raise WebhookUserNotFound("User not found")
        if not self._repository.location_exists_for_user(location_id, user_id):
            raise WebhookLocationNotFound("Location not found")
