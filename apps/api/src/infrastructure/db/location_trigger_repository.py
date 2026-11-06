from uuid import UUID

from sqlmodel import Session, select

from src.infrastructure.db.models import UserLocationModel, UserModel


class SqlModelLocationTriggerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def user_exists(self, user_id: UUID) -> bool:
        return self._session.get(UserModel, user_id) is not None

    def location_exists_for_user(self, location_id: str, user_id: UUID) -> bool:
        statement = select(UserLocationModel.id).where(
            UserLocationModel.id == location_id,
            UserLocationModel.user_id == user_id,
        )
        return self._session.exec(statement).first() is not None
