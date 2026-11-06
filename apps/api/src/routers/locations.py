"""
Locations REST API router.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.application.locations.use_cases import (
    CreateUserLocationDTO,
    CreateUserLocationUseCase,
    ListUserLocationsUseCase,
)
from src.domain.locations.exceptions import InvalidCoordinatesException
from src.presentation.http.dependencies import (
    get_create_location_use_case,
    get_list_locations_use_case,
)

router = APIRouter(prefix="/locations", tags=["locations"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class CreateLocationRequest(BaseModel):
    name: str = Field(
        min_length=1, max_length=120, description="Name or alias for location (e.g. Home, Office)"
    )
    latitude: float = Field(ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    radius_meters: int = Field(default=100, gt=0, description="Geofence trigger radius in meters")


class LocationResponse(BaseModel):
    id: str
    name: str
    latitude: float
    longitude: float
    radius_meters: int


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    payload: CreateLocationRequest,
    use_case: CreateUserLocationUseCase = Depends(get_create_location_use_case),
) -> LocationResponse:
    try:
        dto = CreateUserLocationDTO(
            name=payload.name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_meters=payload.radius_meters,
        )
        location = use_case.execute(dto)
        return LocationResponse(
            id=location.id,
            name=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
            radius_meters=location.radius_meters,
        )
    except (InvalidCoordinatesException, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.get("", response_model=list[LocationResponse])
def get_locations(
    limit: int = 100,
    offset: int = 0,
    use_case: ListUserLocationsUseCase = Depends(get_list_locations_use_case),
) -> list[LocationResponse]:
    locations = use_case.execute(limit=limit, offset=offset)

    return [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            latitude=loc.latitude,
            longitude=loc.longitude,
            radius_meters=loc.radius_meters,
        )
        for loc in locations
    ]
