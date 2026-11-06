from typing import Protocol
from uuid import UUID

from src.domain.users.models import User


class UserRepository(Protocol):
    def find_by_email(self, email: str) -> User | None: ...

    def save(self, user: User) -> User: ...

    def update_preferred_language(self, user_id: UUID, language: str) -> User | None: ...
