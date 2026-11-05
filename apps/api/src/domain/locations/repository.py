"""
Repository protocol and SQLModel implementation for User Locations.
"""

from typing import Optional, List, Protocol, runtime_checkable
from datetime import datetime, timezone
from sqlmodel import Session, select
from src.domain.locations.models import UserLocation


@runtime_checkable
class LocationRepository(Protocol):
    def find_by_id(self, location_id: str) -> Optional[UserLocation]:
        ...

    def find_by_name(self, name: str) -> Optional[UserLocation]:
        ...

    def list_all(self, limit: int = 100, offset: int = 0) -> List[UserLocation]:
        ...

    def save(self, location: UserLocation) -> UserLocation:
        ...

    def delete(self, location_id: str) -> None:
        ...


class SqlModelLocationRepository(LocationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_by_id(self, location_id: str) -> Optional[UserLocation]:
        return self.session.get(UserLocation, location_id)

    def find_by_name(self, name: str) -> Optional[UserLocation]:
        # Case-insensitive name match
        query = select(UserLocation).where(
            UserLocation.name.ilike(name.strip())
        )
        return self.session.exec(query).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[UserLocation]:
        query = select(UserLocation).offset(offset).limit(limit).order_by(UserLocation.name)
        return list(self.session.exec(query).all())

    def save(self, location: UserLocation) -> UserLocation:
        location.validate_coordinates()
        location.updated_at = datetime.now(timezone.utc)
        self.session.add(location)
        self.session.commit()
        self.session.refresh(location)
        return location

    def delete(self, location_id: str) -> None:
        loc = self.session.get(UserLocation, location_id)
        if loc:
            self.session.delete(loc)
            self.session.commit()

