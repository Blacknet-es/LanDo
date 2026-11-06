from typing import Protocol
from uuid import UUID

from src.domain.users.models import User, UserLanguage
from src.domain.users.repository import UserRepository


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, hashed_password: str) -> bool: ...


class AccessTokenIssuer(Protocol):
    def issue(self, user_id: UUID) -> str: ...


class AccountAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class InvalidUserLanguage(Exception):
    pass


class RegisterUserUseCase:
    def __init__(self, repository: UserRepository, password_hasher: PasswordHasher) -> None:
        self.repository = repository
        self.password_hasher = password_hasher

    def execute(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        if self.repository.find_by_email(normalized_email) is not None:
            raise AccountAlreadyExists
        user = User(email=normalized_email, hashed_password=self.password_hasher.hash(password))
        try:
            return self.repository.save(user)
        except AccountAlreadyExists:
            raise


class LoginUserUseCase:
    def __init__(
        self,
        repository: UserRepository,
        password_hasher: PasswordHasher,
        token_issuer: AccessTokenIssuer,
    ) -> None:
        self.repository = repository
        self.password_hasher = password_hasher
        self.token_issuer = token_issuer

    def execute(self, email: str, password: str) -> str:
        user = self.repository.find_by_email(email.strip().lower())
        if user is None or not self.password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentials
        return self.token_issuer.issue(user.id)


class UpdateUserLanguageUseCase:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def execute(self, user_id: UUID, language: str) -> User:
        try:
            selected_language = UserLanguage(language)
        except ValueError as exc:
            raise InvalidUserLanguage(language) from exc

        user = self.repository.update_preferred_language(user_id, selected_language.value)
        if user is None:
            raise LookupError("User not found")
        return user
