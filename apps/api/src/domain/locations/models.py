"""
Domain models and SQLModel persistence for User Locations / Points of Interest (POIs).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

from src.domain.locations.exceptions import InvalidCoordinatesException


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserLocation(SQLModel, table=True):
    __tablename__ = "user_locations"

    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str = Field(index=True, max_length=120, description="Alias (e.g. Home, Office, Parents' House)")
    latitude: float = Field(description="Latitude in decimal degrees (-90 to 90)")
    longitude: float = Field(description="Longitude in decimal degrees (-180 to 180)")
    radius_meters: int = Field(default=100, description="Geofence detection radius in meters")
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    def validate_coordinates(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0) or not (-180.0 <= self.longitude <= 180.0):
            raise InvalidCoordinatesException(self.latitude, self.longitude)
        if self.radius_meters <= 0:
            raise ValueError(f"radius_meters must be > 0, got {self.radius_meters}")
