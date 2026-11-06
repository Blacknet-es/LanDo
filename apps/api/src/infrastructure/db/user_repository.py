from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from src.application.users.use_cases import AccountAlreadyExists
from src.domain.users.models import User
from src.domain.users.repository import UserRepository
from src.infrastructure.db.models import UserModel


class SqlModelUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_domain(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            created_at=model.created_at,
            preferred_language=model.preferred_language,
        )

    def find_by_email(self, email: str) -> User | None:
        model = self.session.exec(select(UserModel).where(UserModel.email == email)).first()
        return self._to_domain(model) if model else None

    def save(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            preferred_language=user.preferred_language,
            created_at=user.created_at,
        )
        self.session.add(model)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise AccountAlreadyExists from exc
        self.session.refresh(model)
        return self._to_domain(model)

    def update_preferred_language(self, user_id: UUID, language: str) -> User | None:
        model = self.session.get(UserModel, user_id)
        if model is None:
            return None
        model.preferred_language = language
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        return self._to_domain(model)
