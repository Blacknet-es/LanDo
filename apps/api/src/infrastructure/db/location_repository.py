from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, select

from src.domain.locations.models import UserLocation
from src.domain.locations.repository import LocationRepository
from src.infrastructure.db.models import UserLocationModel


class SqlModelLocationRepository(LocationRepository):
    def __init__(self, session: Session, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    @staticmethod
    def _to_domain(model: UserLocationModel) -> UserLocation:
        return UserLocation(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            latitude=model.latitude,
            longitude=model.longitude,
            radius_meters=model.radius_meters,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def find_by_id(self, location_id: str) -> UserLocation | None:
        model = self.session.exec(
            select(UserLocationModel).where(
                UserLocationModel.id == location_id,
                UserLocationModel.user_id == self.user_id,
            )
        ).first()
        return self._to_domain(model) if model else None

    def find_by_name(self, name: str) -> UserLocation | None:
        model = self.session.exec(
            select(UserLocationModel).where(
                UserLocationModel.name.ilike(name.strip()),
                UserLocationModel.user_id == self.user_id,
            )
        ).first()
        return self._to_domain(model) if model else None

    def list_all(self, limit: int = 100, offset: int = 0) -> list[UserLocation]:
        models = self.session.exec(
            select(UserLocationModel)
            .where(UserLocationModel.user_id == self.user_id)
            .offset(offset)
            .limit(limit)
            .order_by(UserLocationModel.name)
        ).all()
        return [self._to_domain(model) for model in models]

    def save(self, location: UserLocation) -> UserLocation:
        location.validate_coordinates()
        location.user_id = self.user_id
        location.updated_at = datetime.now(timezone.utc)
        model = self.session.get(UserLocationModel, location.id)
        if model is not None and model.user_id != self.user_id:
            raise ValueError("Cannot update a location owned by another user.")
        if model is None:
            model = UserLocationModel(id=location.id, user_id=self.user_id)
        model.name = location.name
        model.latitude = location.latitude
        model.longitude = location.longitude
        model.radius_meters = location.radius_meters
        model.updated_at = location.updated_at
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)

    def delete(self, location_id: str) -> None:
        model = self.session.exec(
            select(UserLocationModel).where(
                UserLocationModel.id == location_id,
                UserLocationModel.user_id == self.user_id,
            )
        ).first()
        if model:
            self.session.delete(model)
            self.session.commit()
