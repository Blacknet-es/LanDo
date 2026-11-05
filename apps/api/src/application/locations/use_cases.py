"""
Application use cases for managing user POIs and locations.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

from src.domain.locations.models import UserLocation
from src.domain.locations.repository import LocationRepository
from src.domain.locations.exceptions import InvalidCoordinatesException


class CreateUserLocationDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    latitude: float
    longitude: float
    radius_meters: int = Field(default=100, gt=0)


class CreateUserLocationUseCase:
    def __init__(self, repository: LocationRepository) -> None:
        self.repository = repository

    def execute(self, dto: CreateUserLocationDTO) -> UserLocation:
        location = UserLocation(
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

