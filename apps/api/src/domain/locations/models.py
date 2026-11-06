from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.locations.exceptions import InvalidCoordinatesException


@dataclass
class UserLocation:
    user_id: UUID
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    radius_meters: int = 100
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate_coordinates(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0) or not (-180.0 <= self.longitude <= 180.0):
            raise InvalidCoordinatesException(self.latitude, self.longitude)
        if self.radius_meters <= 0:
            raise ValueError(f"radius_meters must be > 0, got {self.radius_meters}")
