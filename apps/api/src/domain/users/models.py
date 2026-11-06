from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class UserLanguage(StrEnum):
    SPANISH = "es"
    ENGLISH = "en"


@dataclass(frozen=True)
class User:
    email: str
    hashed_password: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    preferred_language: str = UserLanguage.SPANISH.value
