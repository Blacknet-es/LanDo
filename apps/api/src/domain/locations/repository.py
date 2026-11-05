"""
Repository protocol and SQLModel implementation for User Locations.
"""

from datetime import datetime, timezone
from typing import List, Optional, Protocol, runtime_checkable
from uuid import UUID

from sqlmodel import Session, select

from src.domain.locations.models import UserLocation


@runtime_checkable
class LocationRepository(Protocol):
    def find_by_id(self, location_id: str) -> Optional[UserLocation]: ...

    def find_by_name(self, name: str) -> Optional[UserLocation]: ...

    def list_all(self, limit: int = 100, offset: int = 0) -> List[UserLocation]: ...

    def save(self, location: UserLocation) -> UserLocation: ...

    def delete(self, location_id: str) -> None: ...


class SqlModelLocationRepository(LocationRepository):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    def find_by_id(self, location_id: str) -> Optional[UserLocation]:
        return self.session.exec(
            select(UserLocation).where(
                UserLocation.id == location_id,
                UserLocation.user_id == self.user_id,
            )
        ).first()

    def find_by_name(self, name: str) -> Optional[UserLocation]:
        # Case-insensitive name match
        query = select(UserLocation).where(
            UserLocation.name.ilike(name.strip()),
            UserLocation.user_id == self.user_id,
        )
        return self.session.exec(query).first()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[UserLocation]:
        query = (
            select(UserLocation)
            .where(UserLocation.user_id == self.user_id)
            .offset(offset)
            .limit(limit)
            .order_by(UserLocation.name)
        )
        return list(self.session.exec(query).all())

    def save(self, location: UserLocation) -> UserLocation:
        location.validate_coordinates()
        location.user_id = self.user_id
        location.updated_at = datetime.now(timezone.utc)
        self.session.add(location)
        self.session.commit()
        self.session.refresh(location)
        return location

    def delete(self, location_id: str) -> None:
        loc = self.find_by_id(location_id)
        if loc:
            self.session.delete(loc)
            self.session.commit()
