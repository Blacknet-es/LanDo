"""
LangChain structured tools for managing saved user locations / POIs.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlmodel import Session

from src.application.locations.use_cases import (
    CreateUserLocationDTO,
    CreateUserLocationUseCase,
    ListUserLocationsUseCase,
)
from src.domain.locations.repository import SqlModelLocationRepository


class ManageLocationsInput(BaseModel):
    action: str = Field(
        description="Action to perform: 'create' to add a new place or 'list' to query saved places."
    )
    name: Optional[str] = Field(
        default=None,
        description="Name / alias of the location (e.g., 'Home', 'Office', 'Parents\\' House'). Required if action is 'create'.",
    )
    latitude: Optional[float] = Field(
        default=None,
        description="Latitude in decimal degrees. Required if action is 'create'.",
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Longitude in decimal degrees. Required if action is 'create'.",
    )
    radius_meters: Optional[int] = Field(
        default=100,
        description="Geofence radius in meters. Defaults to 100.",
    )


def get_location_tools(session: Session, user_id: UUID) -> List[StructuredTool]:
    repo = SqlModelLocationRepository(session, user_id)
    create_uc = CreateUserLocationUseCase(repo, user_id)
    list_uc = ListUserLocationsUseCase(repo)

    def manage_locations(
        action: str,
        name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: Optional[int] = 100,
    ) -> Dict[str, Any]:
        """Create or query user saved locations and POIs for geofencing."""
        act = action.lower().strip()

        if act == "create":
            if not name or latitude is None or longitude is None:
                return {
                    "error": "To create a location, 'name', 'latitude', and 'longitude' are all required."
                }
            try:
                dto = CreateUserLocationDTO(
                    name=name,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius_meters or 100,
                )
                loc = create_uc.execute(dto)
                return {
                    "status": "success",
                    "location_id": loc.id,
                    "name": loc.name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "radius_meters": loc.radius_meters,
                    "message": f"Location '{loc.name}' saved successfully.",
                }
            except Exception as e:
                return {"error": f"Failed to create location: {str(e)}"}

        elif act == "list":
            locations = list_uc.execute()
            return {
                "count": len(locations),
                "locations": [
                    {
                        "id": l.id,
                        "name": l.name,
                        "latitude": l.latitude,
                        "longitude": l.longitude,
                        "radius_meters": l.radius_meters,
                    }
                    for l in locations
                ],
            }

        return {"error": f"Unknown action '{action}'. Supported actions are 'create' and 'list'."}

    return [
        StructuredTool.from_function(
            func=manage_locations,
            name="manage_locations",
            description="Manage user saved places/POIs for geofencing (create new locations or list existing saved ones).",
            args_schema=ManageLocationsInput,
        )
    ]
