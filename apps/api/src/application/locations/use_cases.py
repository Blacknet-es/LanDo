"""
Application use cases for managing user POIs and locations.
"""

from typing import List
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.locations.models import UserLocation
from src.domain.locations.repository import LocationRepository


class CreateUserLocationDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    latitude: float
    longitude: float
    radius_meters: int = Field(default=100, gt=0)


class CreateUserLocationUseCase:
    def __init__(self, repository: LocationRepository, user_id: UUID) -> None:
        self.repository = repository
        self.user_id = user_id

    def execute(self, dto: CreateUserLocationDTO) -> UserLocation:
        location = UserLocation(
            user_id=self.user_id,
            name=dto.name.strip(),
            latitude=dto.latitude,
            longitude=dto.longitude,
            radius_meters=dto.radius_meters,
        )
        return self.repository.save(location)


class ListUserLocationsUseCase:
    def __init__(self, repository: LocationRepository) -> None:
        self.repository = repository

    def execute(self, limit: int = 100, offset: int = 0) -> List[UserLocation]:
        return self.repository.list_all(limit=limit, offset=offset)
