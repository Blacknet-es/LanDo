from dataclasses import dataclass
from typing import List
from uuid import UUID

from src.domain.locations.models import UserLocation
from src.domain.locations.repository import LocationRepository


@dataclass(frozen=True)
class CreateUserLocationDTO:
    name: str
    latitude: float
    longitude: float
    radius_meters: int = 100


class CreateUserLocationUseCase:
    def __init__(self, repository: LocationRepository, user_id: UUID) -> None:
        self.repository = repository
        self.user_id = user_id

    def execute(self, dto: CreateUserLocationDTO) -> UserLocation:
        normalized_name = dto.name.strip()
        if not normalized_name:
            raise ValueError("name must not be blank")
        location = UserLocation(
            user_id=self.user_id,
            name=normalized_name,
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
